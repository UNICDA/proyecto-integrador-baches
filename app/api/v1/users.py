from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.user_schema import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Registrar nuevo usuario ciudadano")
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Recibe los datos del usuario, inyecta la sesión de la base de datos 
    y delega la creación al servicio correspondiente.
    """
    return UserService.create_citizen_user(db, user_in)