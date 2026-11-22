import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Configuración de seguridad JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    # Configuración de almacenamiento S3 / MinIO
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT")
    S3_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER")
    S3_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME")

    # Configuración de Redis y Celery
    REDIS_URL: str = os.getenv("REDIS_URL")

    # Reglas de validación multimedia
    MAX_IMAGE_SIZE_BYTES: int = int(os.getenv("MAX_IMAGE_SIZE_BYTES", 10 * 1024 * 1024))
    ALLOWED_IMAGE_MIME_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

settings = Settings()