from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=3, example="Juan Pérez")
    email: EmailStr = Field(..., example="juan.perez@email.com")
    password: str = Field(..., min_length=6, max_length=72, example="secreta123")
    # Por defecto, todos los registros desde la app móvil pública serán "CITIZEN"

class UserResponse(BaseModel):
    id: str  # UUID convertido a string para compatibilidad JSON
    full_name: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True