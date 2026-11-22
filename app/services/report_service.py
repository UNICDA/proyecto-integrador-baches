import logging
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.catalogs import ProcessingStatus
from app.models.potholes import CitizenReport, ImageEvidence
from app.models.users import User
from app.schemas.report_schema import (
    CitizenReportResponse,
    CitizenReportSummary,
    ImageEvidenceResponse,
    PaginatedCitizenReportResponse,
)
from app.services.storage_service import StorageService
from app.worker.tasks import process_citizen_report

logger = logging.getLogger(__name__)


class ReportService:
    """
    Servicio de dominio encargado de la ingesta, validación de idempotencia,
    encolado asíncrono y consulta de reportes ciudadanos.
    """

    @staticmethod
    def _build_report_response(
        report: CitizenReport,
        latitude: float,
        longitude: float,
        processing_status_code: str,
        evidence: Optional[ImageEvidence],
    ) -> CitizenReportResponse:
        """Construye la respuesta serializada del reporte ciudadano y su evidencia."""
        evidence_schema = (
            ImageEvidenceResponse.model_validate(evidence) if evidence is not None else None
        )
        return CitizenReportResponse(
            id=report.id,
            user_id=report.user_id,
            idempotency_key=report.idempotency_key,
            latitude=latitude,
            longitude=longitude,
            gps_accuracy_meters=(
                float(report.gps_accuracy_meters)
                if report.gps_accuracy_meters is not None
                else None
            ),
            citizen_comment=report.citizen_comment,
            processing_status_id=report.processing_status_id,
            processing_status_code=processing_status_code,
            captured_at=report.captured_at,
            synced_at=report.synced_at,
            evidence=evidence_schema,
        )

    @staticmethod
    def create_citizen_report(
        db: Session,
        user: User,
        idempotency_key: UUID,
        latitude: float,
        longitude: float,
        captured_at: datetime,
        image_file: UploadFile,
        gps_accuracy_meters: Optional[float] = None,
        citizen_comment: Optional[str] = None,
    ) -> Tuple[CitizenReportResponse, bool]:
        """
        Registra un reporte ciudadano garantizando idempotencia, integridad de imagen,
        persistencia atómica entre MinIO y PostgreSQL/PostGIS, y encolado en Celery.

        Retorna una tupla (CitizenReportResponse, is_duplicate).
        """
        # 1. Validar rangos geográficos WGS84
        if not (-90.0 <= latitude <= 90.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La latitud debe estar comprendida entre -90 y 90 grados.",
            )

        if not (-180.0 <= longitude <= 180.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La longitud debe estar comprendida entre -180 y 180 grados.",
            )

        if gps_accuracy_meters is not None and gps_accuracy_meters < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La precisión GPS en metros no puede ser un valor negativo.",
            )

        # 2. Control de idempotencia (RF-08) antes de leer o subir la imagen
        existing_row = (
            db.query(
                CitizenReport,
                func.ST_Y(CitizenReport.capture_location).label("latitude"),
                func.ST_X(CitizenReport.capture_location).label("longitude"),
                ProcessingStatus.code.label("status_code"),
            )
            .join(ProcessingStatus, CitizenReport.processing_status_id == ProcessingStatus.id)
            .filter(CitizenReport.idempotency_key == idempotency_key)
            .first()
        )

        if existing_row is not None:
            existing_report, existing_lat, existing_lon, existing_status_code = existing_row
            if existing_report.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="La clave de idempotencia proporcionada ya está registrada por otro usuario.",
                )

            existing_evidence = (
                db.query(ImageEvidence)
                .filter(ImageEvidence.report_id == existing_report.id)
                .first()
            )
            response_data = ReportService._build_report_response(
                report=existing_report,
                latitude=float(existing_lat),
                longitude=float(existing_lon),
                processing_status_code=existing_status_code,
                evidence=existing_evidence,
            )
            return response_data, True

        # 3. Validar integridad de la imagen y detectar duplicados por SHA-256 (RF-05)
        image_file.file.seek(0)
        file_bytes = image_file.file.read()
        metadata = StorageService.validate_and_inspect_image(
            file_bytes=file_bytes,
            content_type=image_file.content_type,
        )

        duplicate_evidence = (
            db.query(ImageEvidence)
            .filter(ImageEvidence.sha256_hash == metadata["sha256_hash"])
            .first()
        )
        if duplicate_evidence is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta fotografía ya fue registrada previamente en el sistema.",
            )

        # 4. Consultar estado inicial de procesamiento
        received_status = (
            db.query(ProcessingStatus)
            .filter(ProcessingStatus.code == "RECEIVED")
            .first()
        )
        if received_status is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno: El estado de procesamiento 'RECEIVED' no está configurado en la base de datos.",
            )

        # 5. Subir evidencia a MinIO y persistir en PostgreSQL de forma transaccional
        image_s3_key = StorageService.upload_file(
            file_bytes=file_bytes,
            content_type=metadata["mime_type"],
            folder="citizen_reports",
        )

        point_wkt = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

        try:
            new_report = CitizenReport(
                user_id=user.id,
                idempotency_key=idempotency_key,
                capture_location=point_wkt,
                gps_accuracy_meters=gps_accuracy_meters,
                citizen_comment=citizen_comment,
                processing_status_id=received_status.id,
                captured_at=captured_at,
            )
            db.add(new_report)
            db.flush()

            new_evidence = ImageEvidence(
                source_type="CITIZEN_PHOTO",
                report_id=new_report.id,
                survey_id=None,
                image_s3_key=image_s3_key,
                sha256_hash=metadata["sha256_hash"],
                width_px=metadata["width_px"],
                height_px=metadata["height_px"],
                size_bytes=metadata["size_bytes"],
                mime_type=metadata["mime_type"],
                frame_location=point_wkt,
                video_second=None,
            )
            db.add(new_evidence)
            db.commit()
            db.refresh(new_report)
            db.refresh(new_evidence)
        except Exception:
            db.rollback()
            StorageService.delete_file(image_s3_key)
            raise

        # 6. Encolar tarea asíncrona en Celery con resiliencia ante caída de Redis
        final_status = received_status
        queued_status = (
            db.query(ProcessingStatus)
            .filter(ProcessingStatus.code == "QUEUED_CELERY")
            .first()
        )

        if queued_status is not None:
            try:
                # Se actualiza a QUEUED_CELERY antes del despacho para evitar condiciones de carrera con el worker
                new_report.processing_status_id = queued_status.id
                db.commit()

                process_citizen_report.delay(str(new_report.id))
                final_status = queued_status
            except Exception as exc:
                logger.error(
                    "No se pudo encolar el reporte '%s' en Celery/Redis; se mantiene en RECEIVED: %s",
                    new_report.id,
                    str(exc),
                )
                db.rollback()
                new_report.processing_status_id = received_status.id
                db.commit()
                db.refresh(new_report)
                final_status = received_status
        else:
            logger.error(
                "Estado 'QUEUED_CELERY' no encontrado en base de datos; el reporte '%s' permanece en RECEIVED.",
                new_report.id,
            )

        response_data = ReportService._build_report_response(
            report=new_report,
            latitude=latitude,
            longitude=longitude,
            processing_status_code=final_status.code,
            evidence=new_evidence,
        )
        return response_data, False

    @staticmethod
    def get_user_reports(
        db: Session,
        user: User,
        limit: int = 20,
        offset: int = 0,
        status_code: Optional[str] = None,
    ) -> PaginatedCitizenReportResponse:
        """
        Obtiene el historial paginado de reportes pertenecientes al usuario autenticado,
        ordenados del más reciente al más antiguo y con filtro opcional por estado.
        """
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El parámetro 'limit' debe estar comprendido entre 1 y 100.",
            )

        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El parámetro 'offset' no puede ser negativo.",
            )

        base_filter = [CitizenReport.user_id == user.id]

        if status_code is not None:
            status_obj = (
                db.query(ProcessingStatus)
                .filter(ProcessingStatus.code == status_code)
                .first()
            )
            if status_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El estado de procesamiento '{status_code}' no es válido.",
                )
            base_filter.append(CitizenReport.processing_status_id == status_obj.id)

        total = db.query(CitizenReport).filter(*base_filter).count()

        rows = (
            db.query(
                CitizenReport.id,
                CitizenReport.citizen_comment,
                CitizenReport.captured_at,
                func.ST_Y(CitizenReport.capture_location).label("latitude"),
                func.ST_X(CitizenReport.capture_location).label("longitude"),
                ProcessingStatus.code.label("status_code"),
                ImageEvidence.image_s3_key,
            )
            .join(ProcessingStatus, CitizenReport.processing_status_id == ProcessingStatus.id)
            .outerjoin(ImageEvidence, ImageEvidence.report_id == CitizenReport.id)
            .filter(*base_filter)
            .order_by(CitizenReport.captured_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = [
            CitizenReportSummary(
                id=report_id,
                processing_status_code=proc_status_code,
                citizen_comment=comment,
                latitude=float(lat),
                longitude=float(lon),
                captured_at=captured_at,
                image_s3_key=image_s3_key,
            )
            for report_id, comment, captured_at, lat, lon, proc_status_code, image_s3_key in rows
        ]

        return PaginatedCitizenReportResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    @staticmethod
    def get_report_by_id(
        db: Session,
        report_id: UUID,
        current_user: User,
    ) -> CitizenReportResponse:
        """
        Obtiene el detalle de un reporte ciudadano por su ID validando reglas de propiedad:
        un usuario CITIZEN solo puede consultar sus propios reportes.
        """
        row = (
            db.query(
                CitizenReport,
                func.ST_Y(CitizenReport.capture_location).label("latitude"),
                func.ST_X(CitizenReport.capture_location).label("longitude"),
                ProcessingStatus.code.label("status_code"),
                ImageEvidence,
            )
            .join(ProcessingStatus, CitizenReport.processing_status_id == ProcessingStatus.id)
            .outerjoin(ImageEvidence, ImageEvidence.report_id == CitizenReport.id)
            .filter(CitizenReport.id == report_id)
            .first()
        )

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reporte ciudadano no encontrado.",
            )

        report, lat, lon, proc_status_code, evidence = row

        user_role = getattr(current_user, "token_role", None) or (
            current_user.role.code if current_user.role else None
        )
        if user_role == "CITIZEN" and report.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para consultar reportes de otros usuarios.",
            )

        return ReportService._build_report_response(
            report=report,
            latitude=float(lat),
            longitude=float(lon),
            processing_status_code=proc_status_code,
            evidence=evidence,
        )
