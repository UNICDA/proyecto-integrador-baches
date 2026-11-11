from sqlalchemy import Column, String, Boolean, text, ForeignKey, Integer, Numeric, SmallInteger
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id = Column(SmallInteger, ForeignKey("user_roles.id"), nullable=False)
    full_name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    fcm_token = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    role = relationship("UserRole")

class RoadRoute(Base):
    __tablename__ = "road_routes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    road_geometry = Column(Geometry("MULTILINESTRING", srid=4326), nullable=False)
    buffer_meters = Column(Numeric(5, 2), nullable=False, default=15.00)
    priority_weight = Column(Numeric(3, 2), nullable=False, default=1.00)