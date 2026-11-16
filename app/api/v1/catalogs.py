from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import get_db
from app.schemas.catalogs_schema import RoleResponse, SeverityResponse
from app.services.catalog_service import CatalogService

router = APIRouter()

@router.get("/roles", response_model=List[RoleResponse], summary="Obtener roles de usuario")
def get_roles(db: Session = Depends(get_db)):
    """
    Retorna la lista de roles estáticos del sistema ordenados por ID.
    """
    return CatalogService.get_all_roles(db)

@router.get("/severities", response_model=List[SeverityResponse], summary="Obtener niveles de severidad")
def get_severities(db: Session = Depends(get_db)):
    """
    Retorna la lista de niveles de severidad ordenados por ID.
    """
    return CatalogService.get_all_severities(db)