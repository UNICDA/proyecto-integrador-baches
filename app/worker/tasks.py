import logging
from uuid import UUID

from app.core.database import SessionLocal
from app.models import users as _users_models
from app.models.catalogs import ProcessingStatus
from app.models.potholes import CitizenReport, ImageEvidence
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_processing_status(db, code: str) -> ProcessingStatus:
    """Obtiene un estado de procesamiento por código o lanza error si no existe."""
    status_obj = (
        db.query(ProcessingStatus)
        .filter(ProcessingStatus.code == code)
        .first()
    )
    if status_obj is None:
        raise RuntimeError(
            f"Estado de procesamiento '{code}' no configurado en la base de datos."
        )
    return status_obj


@celery_app.task(name="process_citizen_report", bind=True, max_retries=3)
def process_citizen_report(self, report_id: str) -> dict:
    """
    Tarea asíncrona que ejecuta el pipeline de procesamiento de un reporte ciudadano.
    Transiciona el estado del reporte: QUEUED_CELERY -> PROCESSING_AI -> COMPLETED (o FAILED).
    """
    db = SessionLocal()
    report = None

    try:
        try:
            report_uuid = UUID(report_id)
        except ValueError:
            logger.warning(
                "ID de reporte inválido recibido en worker: '%s'. Se omite sin reintentar.",
                report_id,
            )
            return {"status": "skipped", "reason": "invalid_uuid", "report_id": report_id}

        report = (
            db.query(CitizenReport)
            .filter(CitizenReport.id == report_uuid)
            .first()
        )
        if report is None:
            logger.warning(
                "Reporte ciudadano '%s' no encontrado en la base de datos. Se omite sin reintentar.",
                report_id,
            )
            return {"status": "skipped", "reason": "not_found", "report_id": report_id}

        evidence = (
            db.query(ImageEvidence)
            .filter(ImageEvidence.report_id == report.id)
            .first()
        )
        if evidence is None:
            logger.warning(
                "No se encontró evidencia fotográfica asociada al reporte '%s'. Se omite sin reintentar.",
                report_id,
            )
            return {"status": "skipped", "reason": "evidence_not_found", "report_id": report_id}

        # 1. Marcar el reporte en estado PROCESSING_AI
        processing_status = _get_processing_status(db, "PROCESSING_AI")
        report.processing_status_id = processing_status.id
        db.commit()

        # 2. Gancho de inferencia (Placeholder limpio para RF-06)
        if not evidence.image_s3_key:
            raise ValueError(
                f"La evidencia '{evidence.id}' del reporte '{report_id}' no posee image_s3_key."
            )

        logger.info(
            "Procesando reporte ciudadano | report_id=%s | image_s3_key=%s | sha256_hash=%s",
            report_id,
            evidence.image_s3_key,
            evidence.sha256_hash,
        )

        # TODO (RF-06): Ejecutar inferencia PyTorch/YOLO y deduplicación espacial PostGIS

        # 3. Marcar el reporte como COMPLETED al finalizar sin errores
        completed_status = _get_processing_status(db, "COMPLETED")
        report.processing_status_id = completed_status.id
        db.commit()

        logger.info("Procesamiento completado exitosamente para el reporte '%s'.", report_id)
        return {"status": "completed", "report_id": report_id}

    except Exception as exc:
        db.rollback()
        logger.exception(
            "Error inesperado al procesar el reporte ciudadano '%s': %s",
            report_id,
            str(exc),
        )
        if report is not None:
            try:
                failed_status = _get_processing_status(db, "FAILED")
                report.processing_status_id = failed_status.id
                db.commit()
            except Exception as status_exc:
                db.rollback()
                logger.exception(
                    "No se pudo actualizar a FAILED el reporte '%s': %s",
                    report_id,
                    str(status_exc),
                )
        return {"status": "failed", "report_id": report_id, "error": str(exc)}

    finally:
        db.close()
