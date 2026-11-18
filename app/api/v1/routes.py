from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import get_db, require_role
from app.schemas.route_schema import RouteResponse
from app.services.route_service import RouteService
from app.models.users import User

router = APIRouter()

@router.get("/", response_model=List[RouteResponse], summary="Obtener rutas viales de estudio")
def get_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "TECHNICIAN", "REVIEWER"]))
):
    """
    Retorna la lista de rutas viales y sus geometrías (MultiLineString) en formato texto.
    """
    return RouteService.get_all_routes(db)