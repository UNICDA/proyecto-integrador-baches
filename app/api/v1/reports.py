from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_role
from app.models.users import User
from app.schemas.report_schema import (
    CitizenReportResponse,
    PaginatedCitizenReportResponse,
)
from app.services.report_service import ReportService

router = APIRouter()


@router.post(
    "",
    response_model=CitizenReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo reporte ciudadano de bache",
)
def create_citizen_report(
    response: Response,
    idempotency_key: UUID = Form(..., description="Clave única UUID para control de idempotencia offline."),
    latitude: float = Form(..., description="Latitud GPS en grados decimales (WGS84)."),
    longitude: float = Form(..., description="Longitud GPS en grados decimales (WGS84)."),
    captured_at: datetime = Form(..., description="Fecha y hora de captura en formato ISO 8601."),
    gps_accuracy_meters: Optional[float] = Form(None, description="Precisión estimada del GPS en metros."),
    citizen_comment: Optional[str] = Form(None, description="Comentario opcional del ciudadano."),
    image: UploadFile = File(..., description="Fotografía del bache (JPEG, PNG o WEBP, máx. 10 MB)."),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["CITIZEN", "ADMIN"])),
):
    """
    Recibe un reporte ciudadano vía multipart/form-data, delega las validaciones
    de idempotencia, integridad multimedia, almacenamiento S3 y encolado asíncrono al servicio,
    y retorna 201 Created para reportes nuevos o 200 OK para reintentos idempotentes.
    """
    report_response, is_duplicate = ReportService.create_citizen_report(
        db=db,
        user=current_user,
        idempotency_key=idempotency_key,
        latitude=latitude,
        longitude=longitude,
        captured_at=captured_at,
        image_file=image,
        gps_accuracy_meters=gps_accuracy_meters,
        citizen_comment=citizen_comment,
    )

    if is_duplicate:
        response.status_code = status.HTTP_200_OK

    return report_response


@router.get(
    "/me",
    response_model=PaginatedCitizenReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener historial personal de reportes ciudadanos",
)
def get_my_reports(
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de reportes a retornar."),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial para paginación."),
    status_code: Optional[str] = Query(
        None,
        description="Filtro opcional por código de estado de procesamiento (ej. QUEUED_CELERY, COMPLETED).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["CITIZEN", "ADMIN"])),
):
    """
    Retorna el historial paginado de reportes creados por el usuario autenticado,
    ordenados por fecha de captura descendente.
    """
    return ReportService.get_user_reports(
        db=db,
        user=current_user,
        limit=limit,
        offset=offset,
        status_code=status_code,
    )


@router.get(
    "/{report_id}",
    response_model=CitizenReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un reporte ciudadano por ID",
)
def get_report_detail(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["CITIZEN", "ADMIN", "REVIEWER"])),
):
    """
    Retorna el detalle completo de un reporte ciudadano.
    Los ciudadanos solo pueden consultar sus propios reportes.
    """
    return ReportService.get_report_by_id(
        db=db,
        report_id=report_id,
        current_user=current_user,
    )
