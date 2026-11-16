from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.user_schema import UserLogin, Token
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/login", response_model=Token, summary="Autenticar usuario y emitir JWT")
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """
    Recibe las credenciales, delega la validación y la emisión del token al servicio.
    """
    user = AuthService.authenticate_user(db, user_in)
    return AuthService.create_token_response(db, user)