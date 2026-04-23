"""Celery task definitions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy import select

from packages.config import get_settings
from packages.contracts.task_contract import TaskContract
from packages.orchestrator.task_orchestrator import TaskOrchestrator
from packages.persistence import SessionLocal, Task, TaskAttempt, TaskResult
from packages.providers.factory import create_provider
from packages.queue.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_task(self, task_id: str) -> dict:
    """Process single task and store status + failure metadata."""

    settings = get_settings()
    db = SessionLocal()
    try:
        task = db.scalar(select(Task).where(Task.id == task_id))
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        attempt = TaskAttempt(task_id=task_id, attempt_no=self.request.retries + 1, status="running")
        db.add(attempt)

        task.status = "running"
        db.commit()

        provider = create_provider({"provider": settings.provider_name, "model": settings.provider_model})
        orchestrator = TaskOrchestrator(provider=provider)
        contract = TaskContract.model_validate(task.request_payload)
        result = asyncio.run(orchestrator.execute(contract))

        task.status = result.status.value
        db.merge(
            TaskResult(
                task_id=task_id,
                output_payload=result.output_payload,
                final_outcome=result.final_outcome.value,
                score=result.scoring.score,
                confidence=result.scoring.confidence,
            )
        )
        attempt.status = "succeeded"
        attempt.finished_at = datetime.now(timezone.utc)
        db.commit()

        return {"task_id": task_id, "status": task.status}
    except Exception as exc:
        db.rollback()
        failed_attempt = TaskAttempt(
            task_id=task_id,
            attempt_no=self.request.retries + 1,
            status="failed",
            error_message=str(exc),
            finished_at=datetime.now(timezone.utc),
        )
        db.add(failed_attempt)
        task = db.scalar(select(Task).where(Task.id == task_id))
        if task:
            task.status = "failed"
        db.commit()
        logger.exception("task_failed", task_id=task_id)
        raise
    finally:
        db.close()
