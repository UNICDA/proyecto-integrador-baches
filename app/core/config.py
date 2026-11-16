import os

class Settings:
    # En producción esto debe venir de variables de entorno (.env)
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

settings = Settings()