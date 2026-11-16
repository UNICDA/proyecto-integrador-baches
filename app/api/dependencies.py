from typing import Generator
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

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

# Alias rápido para usar en los endpoints: db: Session = Depends(get_db)