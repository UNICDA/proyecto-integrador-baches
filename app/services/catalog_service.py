from sqlalchemy.orm import Session
from app.models.catalogs import UserRole, SeverityLevel

class CatalogService:
    @staticmethod
    def get_all_roles(db: Session):
        """Obtiene todos los roles ordenados por ID."""
        return db.query(UserRole).order_by(UserRole.id).all()

    @staticmethod
    def get_all_severities(db: Session):
        """Obtiene todos los niveles de severidad ordenados por ID."""
        return db.query(SeverityLevel).order_by(SeverityLevel.id).all()