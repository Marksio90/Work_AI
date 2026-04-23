"""Celery task definitions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from celery.utils.log import get_task_logger
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from packages.config import get_settings
from packages.contracts.task_contract import TaskContract
from packages.economics import ProfitabilityEngine
from packages.orchestrator.task_orchestrator import TaskOrchestrator
from packages.persistence import ExternalTask, SessionLocal, Task, TaskAttempt, TaskEconomics, TaskResult
from packages.providers.factory import create_provider
from packages.queue.celery_app import celery_app
from packages.task_source import create_task_source

logger = get_task_logger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_task(self, task_id: str) -> dict:
    """Process single task and store status + failure metadata."""

    settings = get_settings()
    db = SessionLocal()
    source = create_task_source(settings.task_source_name)
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

        _submit_external_if_needed(db=db, source=source, task_id=task_id, result=result.model_dump(mode="json"))
        _close_inbound_economics_if_needed(db=db, task_id=task_id, task_status=result.status.value)

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


@celery_app.task
def ingest_source_tasks(limit: int | None = None) -> dict:
    """Fetches paid tasks from configured source and enqueues profitable ones."""

    settings = get_settings()
    source = create_task_source(settings.task_source_name)
    profitability = ProfitabilityEngine(
        infra_cost_per_task_usd=settings.economics_infra_cost_per_task_usd,
        token_cost_per_1k_usd=settings.economics_token_cost_per_1k_usd,
        min_margin_usd=settings.economics_min_margin_usd,
        default_success_probability=settings.economics_default_success_probability,
    )

    batch_size = limit or settings.task_source_poll_batch_size
    source_tasks = source.fetch_available_tasks(limit=batch_size)

    db = SessionLocal()
    accepted = 0
    skipped = 0
    for item in source_tasks:
        exists = db.scalar(
            select(ExternalTask).where(
                ExternalTask.source_name == source.name,
                ExternalTask.external_task_id == item.external_task_id,
            )
        )
        if exists:
            skipped += 1
            continue

        decision = profitability.evaluate(payload=item.input_payload, expected_payout_usd=item.payout_usd)
        if not decision.should_accept:
            skipped += 1
            continue

        if not source.accept_task(item.external_task_id):
            skipped += 1
            continue

        task_id = uuid4().hex
        contract = TaskContract(
            task_id=task_id,
            task_type=item.task_type,
            input_payload=item.input_payload,
            output_schema=item.output_schema,
            constraints=item.constraints,
            metadata={**item.metadata, "source_name": source.name, "external_task_id": item.external_task_id},
        )
        task = Task(
            id=task_id,
            status="queued",
            task_type=contract.task_type.value,
            request_payload=contract.model_dump(mode="json"),
            dedup_key=contract.fingerprint(),
        )
        db.add(task)
        db.add(
            ExternalTask(
                source_name=source.name,
                external_task_id=item.external_task_id,
                internal_task_id=task_id,
                status="accepted",
                expected_payout_usd=decision.expected_payout_usd,
                estimated_cost_usd=decision.estimated_cost_usd,
                expected_margin_usd=decision.expected_margin_usd,
            )
        )
        db.merge(
            TaskEconomics(
                task_id=task_id,
                source_name=source.name,
                expected_payout_usd=decision.expected_payout_usd,
                estimated_cost_usd=decision.estimated_cost_usd,
                actual_payout_usd=None,
                expected_success_probability=decision.expected_success_probability,
                margin_usd=decision.expected_margin_usd,
                status="queued",
            )
        )
        db.commit()

        process_task.delay(task_id)
        accepted += 1

    db.close()
    return {"source": source.name, "fetched": len(source_tasks), "accepted": accepted, "skipped": skipped}


@celery_app.task
def get_economics_summary() -> dict:
    """Returns aggregate profitability metrics."""

    db = SessionLocal()
    row = db.execute(
        select(
            func.count(TaskEconomics.task_id),
            func.coalesce(func.sum(TaskEconomics.expected_payout_usd), 0.0),
            func.coalesce(func.sum(TaskEconomics.estimated_cost_usd), 0.0),
            func.coalesce(func.sum(TaskEconomics.actual_payout_usd), 0.0),
            func.coalesce(func.avg(TaskEconomics.margin_usd), 0.0),
        )
    ).one()
    db.close()
    return {
        "tasks": int(row[0]),
        "expected_payout_usd": float(row[1]),
        "estimated_cost_usd": float(row[2]),
        "actual_payout_usd": float(row[3]),
        "avg_margin_usd": float(row[4]),
    }


def _close_inbound_economics_if_needed(*, db: Session, task_id: str, task_status: str) -> None:
    economics = db.scalar(select(TaskEconomics).where(TaskEconomics.task_id == task_id))
    if economics is None or economics.source_name != "rapidapi":
        return
    if economics.actual_payout_usd is None:
        economics.actual_payout_usd = economics.expected_payout_usd
    economics.margin_usd = round(economics.actual_payout_usd - economics.estimated_cost_usd, 6)
    economics.status = task_status


def _submit_external_if_needed(*, db: Session, source, task_id: str, result: dict) -> None:
    external = db.scalar(select(ExternalTask).where(ExternalTask.internal_task_id == task_id))
    if external is None:
        return

    submit = source.submit_result(
        external_task_id=external.external_task_id,
        output=result.get("output_payload", {}),
        final_outcome=result.get("final_outcome", "failure"),
    )
    external.status = "submitted" if submit.accepted else "submit_failed"
    external.submitted_at = datetime.now(timezone.utc)

    economics = db.scalar(select(TaskEconomics).where(TaskEconomics.task_id == task_id))
    if economics:
        economics.actual_payout_usd = submit.payout_usd
        economics.margin_usd = round(submit.payout_usd - economics.estimated_cost_usd, 6)
        economics.status = external.status
