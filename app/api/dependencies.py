from typing import Generator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.database import SessionLocal
from app.models.users import User
# Asumiendo que las variables están en tu config.py
from app.core.config import settings
def get_db() -> Generator[Session, None, None]:
    """
    Dependencia de FastAPI para inyectar la sesión de base de datos.
    Garantiza que la sesión se abra al iniciar la petición y se cierre al finalizar,
    incluso si ocurre un error.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Step 1: Security Scheme Setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Step 2: Current User Middleware
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificamos el JWT
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        role_code: str = payload.get("role")
        
        if user_id is None or role_code is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
        
    # Validamos que el usuario exista y esté activo en la BD
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario no existe o se encuentra inactivo."
        )
        
    # Inyectamos el rol del token temporalmente en el objeto para evitar un JOIN extra a la BD
    user.token_role = role_code 
    return user

# Step 3: Role-Based Authorization Factory
def require_role(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if getattr(current_user, "token_role", None) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere uno de los siguientes roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker