from sqlalchemy import Column, String, Text, Boolean, Numeric, SmallInteger
from app.core.database import Base

class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

class SeverityLevel(Base):
    __tablename__ = "severity_levels"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    priority_weight = Column(Numeric(4, 2), nullable=False)
    color_hex = Column(String(7), nullable=False)
    min_area_threshold_pct = Column(Numeric(5, 2), nullable=False)

class PotholeStatus(Base):
    __tablename__ = "pothole_statuses"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(60), nullable=False)
    is_public_visible = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=True)

class ProcessingStatus(Base):
    __tablename__ = "processing_statuses"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(60), nullable=False)
    is_final_state = Column(Boolean, nullable=False, default=False)

class ReviewAction(Base):
    __tablename__ = "review_actions"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(60), nullable=False)
    description = Column(Text, nullable=True)