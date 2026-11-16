import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.users import User
from app.schemas.user_schema import UserLogin

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica la contraseña limitando la entrada a 72 bytes."""
        password_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))

    @staticmethod
    def authenticate_user(db: Session, user_login: UserLogin) -> User:
        """Busca al usuario y valida sus credenciales."""
        user = db.query(User).filter(User.email == user_login.email).first()
        if not user or not AuthService.verify_password(user_login.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo electrónico o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    @staticmethod
    def create_token_response(user: User) -> dict:
        """Genera el JWT y construye el diccionario completo de respuesta del token."""
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Payload del token
        to_encode = {
            "sub": str(user.id),
            "role_id": user.role_id,
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Retorna la estructura completa delegando esta lógica fuera del controlador
        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "token_expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }