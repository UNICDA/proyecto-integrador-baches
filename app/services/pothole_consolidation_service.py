import logging
from datetime import datetime, timezone
from typing import Optional

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement, WKTElement
from sqlalchemy import Float, cast, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.catalogs import PotholeStatus, SeverityLevel
from app.models.potholes import AIDetection, CitizenReport, ImageEvidence, Pothole
from app.models.users import RoadRoute
from app.services.ai_service import AIInferenceResult, AIService

logger = logging.getLogger(__name__)

ELIGIBLE_DEDUP_STATUS_CODES = ("AI_CANDIDATE", "PUBLIC_CONFIRMED")
DEFAULT_ROUTE_WEIGHT = 1.0
MAX_PRIORITY_SCORE = 999.99


class PotholeConsolidationService:
    """
    Servicio de dominio responsable del cruce espacial con corredores viales,
    deduplicación geográfica de baches (RF-16) y cálculo de prioridad explicable (RF-18).
    """

    @staticmethod
    def _to_geography(location_geom):
        """
        Convierte una geometría ORM (WKBElement, WKTElement o expresión SQL) a Geography
        evitando que GeoAlchemy2 envíe un EWKB hexadecimal a ST_GeogFromText.
        """
        if isinstance(location_geom, WKBElement):
            raw_wkb = (
                bytes.fromhex(location_geom.data)
                if isinstance(location_geom.data, str)
                else bytes(location_geom.data)
            )
            return cast(func.ST_GeomFromEWKB(raw_wkb), Geography)

        if isinstance(location_geom, WKTElement):
            return cast(
                func.ST_GeomFromEWKT(f"SRID={location_geom.srid};{location_geom.data}"),
                Geography,
            )

        return cast(location_geom, Geography)

    @staticmethod
    def find_matching_route(db: Session, location_geom) -> Optional[RoadRoute]:
        """
        Identifica la ruta vial de estudio cuyo buffer en metros contiene el punto dado.
        Si intersecta varias rutas, retorna la más cercana según distancia geodésica real.
        """
        point_geog = PotholeConsolidationService._to_geography(location_geom)
        route_geog = cast(RoadRoute.road_geometry, Geography)

        return (
            db.query(RoadRoute)
            .filter(
                func.ST_DWithin(
                    route_geog,
                    point_geog,
                    cast(RoadRoute.buffer_meters, Float),
                )
            )
            .order_by(func.ST_Distance(route_geog, point_geog).asc())
            .first()
        )

    @staticmethod
    def find_nearby_pothole(
        db: Session,
        location_geom,
        radius_meters: float,
    ) -> Optional[Pothole]:
        """
        Busca el bache activo más cercano dentro del radio especificado en metros.
        Solo considera baches en estado AI_CANDIDATE o PUBLIC_CONFIRMED.
        """
        point_geog = PotholeConsolidationService._to_geography(location_geom)
        pothole_geog = cast(Pothole.centroid_location, Geography)

        return (
            db.query(Pothole)
            .join(PotholeStatus, Pothole.pothole_status_id == PotholeStatus.id)
            .filter(
                PotholeStatus.code.in_(ELIGIBLE_DEDUP_STATUS_CODES),
                func.ST_DWithin(pothole_geog, point_geog, float(radius_meters)),
            )
            .order_by(func.ST_Distance(pothole_geog, point_geog).asc())
            .first()
        )

    @staticmethod
    def generate_readable_code(db: Session) -> str:
        """
        Genera un código único legible con formato SDE-{YYYY}-{NNNNN}
        consultando el último correlativo del año en curso.
        """
        current_year = datetime.now(timezone.utc).year
        prefix = f"SDE-{current_year}-"

        last_code_row = (
            db.query(Pothole.readable_code)
            .filter(Pothole.readable_code.like(f"{prefix}%"))
            .order_by(Pothole.readable_code.desc())
            .first()
        )

        next_sequence = 1
        if last_code_row is not None and last_code_row[0]:
            try:
                next_sequence = int(last_code_row[0].split("-")[-1]) + 1
            except ValueError:
                next_sequence = (
                    db.query(Pothole)
                    .filter(Pothole.readable_code.like(f"{prefix}%"))
                    .count()
                    + 1
                )

        return f"{prefix}{next_sequence:05d}"

    @staticmethod
    def calculate_priority_score(
        severity_weight: float,
        route_weight: float,
        evidence_count: int,
    ) -> float:
        """
        Calcula el puntaje de prioridad explicable (RF-18) combinando severidad,
        importancia del corredor vial y recurrencia de evidencias.
        """
        raw_score = (
            float(severity_weight)
            * float(route_weight)
            * (1.0 + 0.15 * max(0, evidence_count - 1))
        )
        return min(round(raw_score, 2), MAX_PRIORITY_SCORE)

    @staticmethod
    def consolidate_detection(
        db: Session,
        report: CitizenReport,
        evidence: ImageEvidence,
        inference: AIInferenceResult,
    ) -> Optional[Pothole]:
        """
        Consolida una inferencia de IA contra los baches existentes en PostGIS,
        registra la trazabilidad en ai_detections y actualiza la prioridad explicable.
        No ejecuta db.commit(); la atomicidad queda controlada por el llamador.
        """
        if (
            not inference.detected
            or inference.confidence_score < settings.AI_CONFIDENCE_THRESHOLD
        ):
            logger.info(
                "No se detectó un bache válido para el reporte '%s' "
                "(detected=%s, confidence=%.3f, threshold=%.2f).",
                report.id,
                inference.detected,
                inference.confidence_score,
                settings.AI_CONFIDENCE_THRESHOLD,
            )
            return None

        proposed_severity = AIService.resolve_severity_level(
            db=db,
            estimated_area_pct=inference.estimated_area_pct,
        )
        matched_route = PotholeConsolidationService.find_matching_route(
            db=db,
            location_geom=report.capture_location,
        )
        nearby_pothole = PotholeConsolidationService.find_nearby_pothole(
            db=db,
            location_geom=report.capture_location,
            radius_meters=settings.POTHOLE_DEDUP_RADIUS_METERS,
        )

        if nearby_pothole is not None:
            # Caso A: Deduplicación espacial sobre un bache activo existente
            pothole = nearby_pothole
            pothole.total_citizen_reports = (pothole.total_citizen_reports or 0) + 1

            if (
                pothole.last_detected_at is None
                or report.captured_at > pothole.last_detected_at
            ):
                pothole.last_detected_at = report.captured_at

            if pothole.route_id is None and matched_route is not None:
                pothole.route_id = matched_route.id

            pothole_status = (
                db.query(PotholeStatus)
                .filter(PotholeStatus.id == pothole.pothole_status_id)
                .first()
            )
            current_ai_severity = (
                db.query(SeverityLevel)
                .filter(SeverityLevel.id == pothole.ai_max_severity_id)
                .first()
            )

            # Si el bache sigue en revisión (AI_CANDIDATE) y la nueva severidad es mayor, se promueve
            if (
                pothole_status is not None
                and pothole_status.code == "AI_CANDIDATE"
                and (
                    current_ai_severity is None
                    or float(proposed_severity.priority_weight)
                    > float(current_ai_severity.priority_weight)
                )
            ):
                pothole.ai_max_severity_id = proposed_severity.id
                effective_severity = proposed_severity
            elif pothole.validated_severity_id is not None:
                validated_severity = (
                    db.query(SeverityLevel)
                    .filter(SeverityLevel.id == pothole.validated_severity_id)
                    .first()
                )
                effective_severity = validated_severity or current_ai_severity or proposed_severity
            else:
                effective_severity = current_ai_severity or proposed_severity

            route_weight = DEFAULT_ROUTE_WEIGHT
            if pothole.route_id is not None:
                assigned_route = (
                    db.query(RoadRoute)
                    .filter(RoadRoute.id == pothole.route_id)
                    .first()
                )
                if assigned_route is not None:
                    route_weight = float(assigned_route.priority_weight)

            total_evidences = (pothole.total_citizen_reports or 0) + (
                pothole.total_technical_detections or 0
            )
            pothole.priority_score = PotholeConsolidationService.calculate_priority_score(
                severity_weight=float(effective_severity.priority_weight),
                route_weight=route_weight,
                evidence_count=total_evidences,
            )

            logger.info(
                "Reporte '%s' deduplicado sobre bache existente '%s' "
                "(total_citizen_reports=%d, priority_score=%.2f).",
                report.id,
                pothole.readable_code,
                pothole.total_citizen_reports,
                float(pothole.priority_score),
            )
        else:
            # Caso B: Nuevo candidato de bache (siempre nace en AI_CANDIDATE para Human-in-the-Loop)
            ai_candidate_status = (
                db.query(PotholeStatus)
                .filter(PotholeStatus.code == "AI_CANDIDATE")
                .first()
            )
            if ai_candidate_status is None:
                raise RuntimeError(
                    "Estado de bache 'AI_CANDIDATE' no configurado en la tabla 'pothole_statuses'."
                )

            readable_code = PotholeConsolidationService.generate_readable_code(db)
            route_id = matched_route.id if matched_route is not None else None
            route_weight = (
                float(matched_route.priority_weight)
                if matched_route is not None
                else DEFAULT_ROUTE_WEIGHT
            )
            priority_score = PotholeConsolidationService.calculate_priority_score(
                severity_weight=float(proposed_severity.priority_weight),
                route_weight=route_weight,
                evidence_count=1,
            )

            pothole = Pothole(
                readable_code=readable_code,
                route_id=route_id,
                centroid_location=report.capture_location,
                ai_max_severity_id=proposed_severity.id,
                validated_severity_id=None,
                pothole_status_id=ai_candidate_status.id,
                priority_score=priority_score,
                parent_pothole_id=None,
                total_citizen_reports=1,
                total_technical_detections=0,
                first_detected_at=report.captured_at,
                last_detected_at=report.captured_at,
            )
            db.add(pothole)
            db.flush()

            logger.info(
                "Nuevo candidato de bache creado '%s' para reporte '%s' "
                "(route_id=%s, severity=%s, priority_score=%.2f).",
                pothole.readable_code,
                report.id,
                route_id,
                proposed_severity.code,
                float(pothole.priority_score),
            )

        # Registro de trazabilidad de la inferencia en ai_detections
        detection = AIDetection(
            evidence_id=evidence.id,
            assigned_pothole_id=pothole.id,
            proposed_severity_id=proposed_severity.id,
            yolo_model_version=inference.model_version,
            confidence=round(inference.confidence_score, 3),
            bounding_box=inference.bounding_box,
            relative_area_pct=round(inference.estimated_area_pct, 2),
            inference_time_ms=inference.inference_time_ms,
        )
        db.add(detection)

        return pothole
