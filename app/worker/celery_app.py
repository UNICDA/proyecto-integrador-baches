from celery import Celery

from app.core.config import settings

# Instancia principal de Celery configurada con Redis como broker y backend
celery_app = Celery(
    "pothole_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
