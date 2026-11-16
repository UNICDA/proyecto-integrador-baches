import re
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=3, example="Juan Pérez")
    email: EmailStr = Field(..., example="juan.perez@email.com")
    password: str = Field(..., example="Password123!")

    @field_validator('password')
    def validate_password_strength(cls, value):
        # Mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número y 1 carácter especial
        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if not re.match(pattern, value):
            raise ValueError(
                "La contraseña debe tener mínimo 8 caracteres, e incluir al menos "
                "una mayúscula, una minúscula, un número y un signo especial (@$!%*?&)."
            )
        return value

class UserResponse(BaseModel):
    id: str  # UUID convertido a string para compatibilidad JSON
    full_name: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    token_expires_in: int