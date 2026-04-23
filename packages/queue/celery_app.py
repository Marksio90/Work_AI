"""Celery app with retry and timeout configuration."""

from __future__ import annotations

from celery import Celery

from packages.config import get_settings

settings = get_settings()

celery_app = Celery("work_ai", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    task_default_retry_delay=5,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
)
