from fastapi import APIRouter, Depends
from typing import List

from app.api.dependencies import get_db, require_role
from app.schemas.catalogs_schema import RoleResponse, SeverityResponse
from app.services.catalog_service import CatalogService
from app.models.users import User
from sqlalchemy.orm import Session

router = APIRouter()

# Todos los roles registrados pueden ver los catálogos base
ALLOWED_CATALOG_ROLES = ["CITIZEN", "ADMIN", "TECHNICIAN", "REVIEWER"]

@router.get("/roles", response_model=List[RoleResponse], summary="Obtener roles de usuario")
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_CATALOG_ROLES))
):
    """
    Retorna la lista de roles estáticos del sistema ordenados por ID.
    """
    return CatalogService.get_all_roles(db)

@router.get("/severities", response_model=List[SeverityResponse], summary="Obtener niveles de severidad")
def get_severities(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_CATALOG_ROLES))
):
    """
    Retorna la lista de niveles de severidad ordenados por ID.
    """
    return CatalogService.get_all_severities(db)