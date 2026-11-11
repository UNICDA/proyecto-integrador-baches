from sqlalchemy import Column, String, Boolean, text, ForeignKey, Integer, Numeric, BigInteger, SmallInteger
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base

class CitizenReport(Base):
    __tablename__ = "citizen_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    idempotency_key = Column(UUID(as_uuid=True), unique=True, nullable=False)
    capture_location = Column(Geometry("POINT", srid=4326), nullable=False)
    gps_accuracy_meters = Column(Numeric(6, 2), nullable=True)
    citizen_comment = Column(String, nullable=True)
    processing_status_id = Column(SmallInteger, ForeignKey("processing_statuses.id"), nullable=False)
    captured_at = Column(TIMESTAMP(timezone=True), nullable=False)
    synced_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

class TechnicalSurvey(Base):
    __tablename__ = "technical_surveys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    technician_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("road_routes.id"), nullable=False)
    video_s3_key = Column(String(255), nullable=False)
    gps_track = Column(Geometry("LINESTRINGM", srid=4326), nullable=True)
    processing_status_id = Column(SmallInteger, ForeignKey("processing_statuses.id"), nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)

class ImageEvidence(Base):
    __tablename__ = "image_evidences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_type = Column(String(20), nullable=False)
    report_id = Column(UUID(as_uuid=True), ForeignKey("citizen_reports.id"), nullable=True)
    survey_id = Column(UUID(as_uuid=True), ForeignKey("technical_surveys.id"), nullable=True)
    image_s3_key = Column(String(255), nullable=False)
    sha256_hash = Column(String(64), unique=True, nullable=False)
    width_px = Column(Integer, nullable=False)
    height_px = Column(Integer, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(30), nullable=False)
    frame_location = Column(Geometry("POINT", srid=4326), nullable=False)
    video_second = Column(Numeric(8, 2), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

class Pothole(Base):
    __tablename__ = "potholes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    readable_code = Column(String(20), unique=True, nullable=False)
    route_id = Column(Integer, ForeignKey("road_routes.id"), nullable=True)
    centroid_location = Column(Geometry("POINT", srid=4326), nullable=False)
    ai_max_severity_id = Column(SmallInteger, ForeignKey("severity_levels.id"), nullable=False)
    validated_severity_id = Column(SmallInteger, ForeignKey("severity_levels.id"), nullable=True)
    pothole_status_id = Column(SmallInteger, ForeignKey("pothole_statuses.id"), nullable=False)
    priority_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    parent_pothole_id = Column(UUID(as_uuid=True), ForeignKey("potholes.id"), nullable=True)
    total_citizen_reports = Column(Integer, nullable=False, default=0)
    total_technical_detections = Column(Integer, nullable=False, default=0)
    first_detected_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_detected_at = Column(TIMESTAMP(timezone=True), nullable=False)

class AIDetection(Base):
    __tablename__ = "ai_detections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("image_evidences.id"), nullable=False)
    assigned_pothole_id = Column(UUID(as_uuid=True), ForeignKey("potholes.id"), nullable=False)
    proposed_severity_id = Column(SmallInteger, ForeignKey("severity_levels.id"), nullable=False)
    yolo_model_version = Column(String(50), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False)
    bounding_box = Column(JSONB, nullable=False)
    relative_area_pct = Column(Numeric(5, 2), nullable=False)
    inference_time_ms = Column(Integer, nullable=False)
    processed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

class ReviewHistory(Base):
    __tablename__ = "review_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    pothole_id = Column(UUID(as_uuid=True), ForeignKey("potholes.id"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action_type_id = Column(SmallInteger, ForeignKey("review_actions.id"), nullable=False)
    previous_state = Column(JSONB, nullable=False)
    new_state = Column(JSONB, nullable=False)
    justification = Column(String, nullable=True)
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

class CitizenNotification(Base):
    __tablename__ = "citizen_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    report_id = Column(UUID(as_uuid=True), ForeignKey("citizen_reports.id"), nullable=False)
    pothole_id = Column(UUID(as_uuid=True), ForeignKey("potholes.id"), nullable=True)
    title = Column(String(100), nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))