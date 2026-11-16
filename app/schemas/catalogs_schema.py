from pydantic import BaseModel, Field
from typing import Optional

# --- ROLES DE USUARIO ---
class RoleBase(BaseModel):
    code: str = Field(..., example="CITIZEN")
    name: str = Field(..., example="Ciudadano")
    description: Optional[str] = None

class RoleResponse(RoleBase):
    id: int
    
    class Config:
        from_attributes = True  # Permite leer desde el ORM de SQLAlchemy

# --- NIVELES DE SEVERIDAD ---
class SeverityResponse(BaseModel):
    id: int
    code: str
    name: str
    priority_weight: float
    color_hex: str
    
    class Config:
        from_attributes = True