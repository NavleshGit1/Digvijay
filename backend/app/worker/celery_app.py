from celery import Celery
from kombu import Queue

from app.core.config import settings

celery_app = Celery(
    "airops_nexus_worker",
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
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    task_queues=[
        Queue("default", routing_key="default"),
        Queue("optimise", routing_key="optimise"),
        Queue("ml", routing_key="ml"),
        Queue("simulate", routing_key="simulate"),
        Queue("report", routing_key="report"),
        Queue("ingest", routing_key="ingest"),
    ],
    task_default_queue="default",
)
