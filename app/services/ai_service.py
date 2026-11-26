from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.catalogs import SeverityLevel


@dataclass
class AIInferenceResult:
    """Estructura desacoplada con el resultado de inferencia sobre una evidencia."""

    detected: bool
    confidence_score: float
    estimated_area_pct: float
    bounding_box: dict
    inference_time_ms: int
    model_version: str


class AIService:
    """
    Adaptador de inferencia de Inteligencia Artificial para la detección de baches.
    Mantiene desacoplado el motor de visión artificial del worker de Celery y de
    la lógica de consolidación espacial.
    """

    @staticmethod
    def analyze_evidence(
        image_s3_key: str,
        width_px: int,
        height_px: int,
    ) -> AIInferenceResult:
        """
        Ejecuta el análisis de la evidencia fotográfica y retorna una propuesta
        de detección con caja delimitadora proporcional a las dimensiones reales.
        """
        # TODO (RF-06): Descargar imagen desde MinIO y ejecutar inferencia real con PyTorch/Ultralytics YOLO
        safe_width = max(int(width_px or 0), 1)
        safe_height = max(int(height_px or 0), 1)

        bounding_box = {
            "x_min": round(safe_width * 0.25),
            "y_min": round(safe_height * 0.40),
            "x_max": round(safe_width * 0.75),
            "y_max": round(safe_height * 0.80),
        }

        return AIInferenceResult(
            detected=True,
            confidence_score=0.87,
            estimated_area_pct=18.5,
            bounding_box=bounding_box,
            inference_time_ms=42,
            model_version=settings.AI_MODEL_VERSION,
        )

    @staticmethod
    def resolve_severity_level(
        db: Session,
        estimated_area_pct: float,
    ) -> SeverityLevel:
        """
        Mapea el porcentaje de área estimada del bache al nivel de severidad
        correspondiente según los umbrales configurados en severity_levels.
        """
        severity = (
            db.query(SeverityLevel)
            .filter(SeverityLevel.min_area_threshold_pct <= estimated_area_pct)
            .order_by(SeverityLevel.min_area_threshold_pct.desc())
            .first()
        )

        if severity is not None:
            return severity

        # Respaldo: nivel con menor umbral configurado (LOW)
        fallback_severity = (
            db.query(SeverityLevel)
            .order_by(SeverityLevel.min_area_threshold_pct.asc())
            .first()
        )
        if fallback_severity is None:
            raise RuntimeError(
                "No existen niveles de severidad configurados en la tabla 'severity_levels'."
            )

        return fallback_severity
