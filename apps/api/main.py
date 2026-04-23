"""FastAPI API with task lifecycle, readiness and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from redis import Redis
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from packages.cache import IdempotencyManager
from packages.config import get_settings
from packages.contracts.enums import TaskType
from packages.contracts.task_contract import TaskContract
from packages.persistence import Base, Task, TaskResult, engine, get_db_session
from packages.providers import factory
from packages.queue import process_task
from packages.telemetry import (
    TASKS_COMPLETED_TOTAL,
    TASKS_CREATED_TOTAL,
    configure_logging,
    correlation_middleware,
    render_metrics,
)

settings = get_settings()
configure_logging(settings.log_level)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Work-AI API", version="1.0.0")
app.middleware("http")(correlation_middleware)


class TaskCreateRequest(BaseModel):
    task_type: TaskType
    input_payload: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/v1/ready")
def ready() -> dict:
    redis_ok = False
    db_ok = False

    try:
        redis_ok = Redis.from_url(settings.redis_url).ping()
    except Exception:
        redis_ok = False

    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        db_ok = True
    except Exception:
        db_ok = False

    if redis_ok and db_ok:
        return {"status": "ready"}
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"redis": redis_ok, "db": db_ok})


@app.post("/v1/tasks", status_code=status.HTTP_202_ACCEPTED)
def create_task(
    payload: TaskCreateRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    idem = IdempotencyManager()
    if idempotency_key:
        existing_task = idem.get_task_for_idempotency(idempotency_key)
        if existing_task:
            return {"task_id": existing_task, "status": "queued", "idempotent_replay": True}

    task_id = uuid4().hex
    contract = TaskContract(
        task_id=task_id,
        task_type=payload.task_type,
        input_payload=payload.input_payload,
        output_schema=payload.output_schema,
        constraints=payload.constraints,
        metadata=payload.metadata,
    )
    dedup_key = contract.fingerprint()
    if not idem.register_dedup(dedup_key, contract.model_dump(mode="json")):
        raise HTTPException(status_code=409, detail="Duplicate task payload in TTL window")

    task = Task(
        id=task_id,
        status="queued",
        task_type=payload.task_type.value,
        request_payload=contract.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        dedup_key=dedup_key,
        correlation_id=request.state.correlation_id,
    )
    db.add(task)
    db.commit()

    if idempotency_key:
        idem.register_idempotency(idempotency_key, task_id)

    async_result = process_task.delay(task_id)
    TASKS_CREATED_TOTAL.inc()
    return {"task_id": task_id, "queue_id": async_result.id, "status": "queued"}


@app.get("/v1/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db_session)) -> dict:
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    result = db.scalar(select(TaskResult).where(TaskResult.task_id == task_id))
    response = {
        "task_id": task.id,
        "status": task.status,
        "task_type": task.task_type,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
    if result:
        response["result"] = {
            "final_outcome": result.final_outcome,
            "output_payload": result.output_payload,
            "score": result.score,
            "confidence": result.confidence,
        }
        TASKS_COMPLETED_TOTAL.labels(status=task.status).inc()
    return response


@app.post("/v1/tasks/{task_id}/cancel")
def cancel_task(task_id: str, db: Session = Depends(get_db_session)) -> dict:
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in {"succeeded", "failed", "abstained"}:
        return {"task_id": task_id, "status": task.status, "cancelled": False}

    process_task.AsyncResult(task_id).revoke(terminate=True)
    task.status = "failed"
    db.commit()
    return {"task_id": task_id, "status": task.status, "cancelled": True}


@app.get("/v1/providers")
def providers() -> dict:
    return {
        "providers": [
            {"name": "mock", "enabled": True},
            {"name": "ollama", "enabled": True},
        ],
        "default": settings.provider_name,
        "factory_module": factory.__name__,
    }


@app.get("/v1/metrics")
def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)


@app.post("/v1/debug/sync")
async def debug_sync(payload: TaskContract) -> dict:
    provider = factory.create_provider({"provider": settings.provider_name, "model": settings.provider_model})
    from packages.orchestrator.task_orchestrator import TaskOrchestrator

    result = await TaskOrchestrator(provider=provider).execute(payload)
    return {"task_id": payload.task_id, "result": result.model_dump(mode="json")}


@app.post("/v1/debug/contract-validation")
def contract_validation(payload: dict) -> dict:
    try:
        contract = TaskContract.model_validate(payload)
        return {"valid": True, "fingerprint": contract.fingerprint()}
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
