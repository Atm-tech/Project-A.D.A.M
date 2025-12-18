from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "adam_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_acks_late = True
celery_app.conf.worker_max_tasks_per_child = 100
celery_app.conf.task_routes = {
    "app.worker.tasks.*": {"queue": "ingestion"},
}
