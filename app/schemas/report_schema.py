from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImageEvidenceResponse(BaseModel):
    """Esquema de salida para la evidencia fotográfica asociada a un reporte."""

    id: UUID
    source_type: str
    image_s3_key: str
    sha256_hash: str
    width_px: int
    height_px: int
    size_bytes: int
    mime_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitizenReportResponse(BaseModel):
    """Esquema de salida para un reporte ciudadano con coordenadas y evidencia."""

    id: UUID
    user_id: UUID
    idempotency_key: UUID
    latitude: float
    longitude: float
    gps_accuracy_meters: Optional[float] = None
    citizen_comment: Optional[str] = None
    processing_status_id: int
    processing_status_code: str
    captured_at: datetime
    synced_at: datetime
    evidence: Optional[ImageEvidenceResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CitizenReportSummary(BaseModel):
    """Esquema resumido para tarjetas del historial personal de reportes ciudadanos."""

    id: UUID
    processing_status_code: str
    citizen_comment: Optional[str] = None
    latitude: float
    longitude: float
    captured_at: datetime
    image_s3_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedCitizenReportResponse(BaseModel):
    """Esquema paginado para el historial de reportes ciudadanos."""

    total: int
    limit: int
    offset: int
    items: List[CitizenReportSummary]
