import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Carga las variables de entorno desde el archivo .env físico
load_dotenv()

# Lee la variable sin ningún valor por defecto quemado
DATABASE_URL = os.getenv("DATABASE_URL")

# Medida de seguridad: Si no existe la variable, detenemos la aplicación de inmediato
if not DATABASE_URL:
    raise ValueError("ERROR CRÍTICO: La variable de entorno DATABASE_URL no está configurada.")

# Creación del motor
engine = create_engine(DATABASE_URL)

# Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para los modelos ORM
Base = declarative_base()

def get_db():
    """Generador de dependencias para proveer la sesión de BD a FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()