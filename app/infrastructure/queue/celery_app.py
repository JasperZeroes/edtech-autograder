from __future__ import annotations

from celery import Celery

from app.infrastructure.grading.settings import get_grading_settings


settings = get_grading_settings()

celery_app = Celery(
    "edtech_autograder",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
)
