"""Entrypoint for Celery worker."""

from packages.queue import celery_app

__all__ = ["celery_app"]
