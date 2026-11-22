import hashlib
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings


MIME_TO_EXTENSION = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}


class StorageService:
    """
    Servicio encargado de la validación de archivos multimedia y la gestión
    de objetos en el almacenamiento compatible con S3 (MinIO).
    """

    @staticmethod
    def get_s3_client():
        """Inicializa y retorna el cliente S3 configurado para MinIO."""
        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    @staticmethod
    def ensure_bucket_exists() -> None:
        """Verifica si el bucket configurado existe en MinIO y lo crea si no existe."""
        client = StorageService.get_s3_client()
        bucket_name = settings.S3_BUCKET_NAME
        try:
            client.head_bucket(Bucket=bucket_name)
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket", "NotFound"):
                try:
                    client.create_bucket(Bucket=bucket_name)
                except (ClientError, BotoCoreError) as create_exc:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"No se pudo crear el bucket de almacenamiento: {str(create_exc)}",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al verificar el bucket en el servicio de almacenamiento.",
                )
        except BotoCoreError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo establecer conexión con el servicio de almacenamiento S3.",
            )

    @staticmethod
    def validate_and_inspect_image(file_bytes: bytes, content_type: Optional[str]) -> dict:
        """
        Valida tipo MIME, tamaño máximo e integridad binaria de la imagen con Pillow.
        Retorna dimensiones, tamaño en bytes, tipo MIME y huella SHA-256.
        """
        if not content_type or content_type not in settings.ALLOWED_IMAGE_MIME_TYPES:
            allowed_str = ", ".join(settings.ALLOWED_IMAGE_MIME_TYPES)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de archivo no permitido. Tipos aceptados: {allowed_str}.",
            )

        size_bytes = len(file_bytes)
        if size_bytes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo de imagen enviado está vacío.",
            )

        if size_bytes > settings.MAX_IMAGE_SIZE_BYTES:
            max_mb = settings.MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"La imagen supera el tamaño máximo permitido de {max_mb} MB.",
            )

        try:
            # Verificar integridad estructural de la imagen
            with Image.open(BytesIO(file_bytes)) as img:
                img.verify()

            # Reabrir para extraer metadatos (verify() cierra el puntero interno)
            with Image.open(BytesIO(file_bytes)) as img:
                detected_format = img.format
                width_px, height_px = img.size
        except (UnidentifiedImageError, OSError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo enviado no es una imagen válida o se encuentra corrupto.",
            )

        if detected_format not in ALLOWED_PIL_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El contenido real de la imagen no corresponde a un formato permitido (JPEG, PNG o WEBP).",
            )

        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        return {
            "width_px": width_px,
            "height_px": height_px,
            "size_bytes": size_bytes,
            "mime_type": content_type,
            "sha256_hash": sha256_hash,
        }

    @staticmethod
    def upload_file(file_bytes: bytes, content_type: str, folder: str = "citizen_reports") -> str:
        """
        Sube los bytes de la imagen a MinIO bajo una ruta organizada por fecha y UUID.
        Retorna la llave S3 generada (image_s3_key).
        """
        StorageService.ensure_bucket_exists()
        client = StorageService.get_s3_client()

        extension = MIME_TO_EXTENSION.get(content_type, "bin")
        now = datetime.now(timezone.utc)
        s3_key = f"{folder}/{now.strftime('%Y')}/{now.strftime('%m')}/{uuid.uuid4()}.{extension}"

        try:
            client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
            )
        except (ClientError, BotoCoreError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al subir la evidencia fotográfica al almacenamiento S3.",
            )

        return s3_key

    @staticmethod
    def delete_file(s3_key: str) -> None:
        """Elimina un objeto de MinIO para evitar archivos huérfanos tras un rollback."""
        try:
            client = StorageService.get_s3_client()
            client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
        except Exception as exc:
            # Se registra en consola sin ocultar la excepción original del rollback
            print(f"Advertencia: No se pudo eliminar el objeto huérfano '{s3_key}' en S3: {str(exc)}")
