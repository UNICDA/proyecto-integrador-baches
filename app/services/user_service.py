import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.users import User
from app.models.catalogs import UserRole
from app.schemas.user_schema import UserCreate

# Configuración para el hashing seguro de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    @staticmethod
    def create_citizen_user(db: Session, user_in: UserCreate) -> User:
        """
        Crea un nuevo usuario ciudadano en la base de datos.
        Valida si el correo ya existe, asigna el rol CITIZEN y encripta la contraseña.
        """
        # 1. Validar si el correo ya existe
        existing_user = db.query(User).filter(User.email == user_in.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado."
            )
        
        # 2. Buscar el ID del rol CITIZEN
        citizen_role = db.query(UserRole).filter(UserRole.code == "CITIZEN").first()
        if not citizen_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno: Rol CITIZEN no configurado en la base de datos."
            )

        # 3. Hashear la contraseña
        #hashed_password = pwd_context.hash(user_in.password)
        password_bytes = user_in.password.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        hashed_password = hashed_bytes.decode("utf-8")

        # 4. Crear el registro del usuario
        new_user = User(
            full_name=user_in.full_name,
            email=user_in.email,
            password_hash=hashed_password,
            role_id=citizen_role.id
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Convertir UUID a string explícitamente para el mapeo del esquema Pydantic
        new_user.id = str(new_user.id) 
        return new_user