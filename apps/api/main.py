"""FastAPI API with task lifecycle, readiness and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from redis import Redis
from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session

from packages.cache import IdempotencyManager
from packages.config import get_settings
from packages.contracts.enums import TaskType
from packages.contracts.task_contract import TaskContract
from packages.economics import ProfitabilityEngine
from packages.persistence import (
    ApiUsageEvent,
    Base,
    PayoutReconciliation,
    Task,
    TaskEconomics,
    TaskResult,
    engine,
    get_db_session,
)
from packages.providers import factory
from packages.queue import get_economics_summary, ingest_source_tasks, process_task
from packages.telemetry import (
    ECONOMICS_ARPU_USD,
    ECONOMICS_CHURN_LIKE_RATE,
    ECONOMICS_MRR_USD,
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


class ReconciliationRequest(BaseModel):
    paid_amount_usd: float = Field(ge=0.0)


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _revenue_for_plan(plan: str) -> float:
    normalized = plan.strip().lower()
    if normalized == "pro":
        return settings.rapidapi_price_pro_usd
    if normalized == "basic":
        return settings.rapidapi_price_basic_usd
    return settings.rapidapi_price_free_usd


def _verify_rapidapi_if_enabled(x_rapidapi_proxy_secret: str | None = Header(default=None, alias="X-RapidAPI-Proxy-Secret")) -> None:
    if settings.task_source_mode != "rapidapi_inbound":
        return
    if x_rapidapi_proxy_secret != settings.rapidapi_proxy_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid RapidAPI proxy secret")


def _register_rapidapi_usage(
    *,
    db: Session,
    endpoint: str,
    task_id: str,
    subscriber_id: str | None,
    subscription: str | None,
    payload: dict,
) -> None:
    if settings.task_source_mode != "rapidapi_inbound":
        return

    subscriber = subscriber_id or "rapidapi-anonymous"
    plan = (subscription or "free").lower()
    revenue = _revenue_for_plan(plan)

    db.add(
        ApiUsageEvent(
            subscriber_id=subscriber,
            subscription_plan=plan,
            endpoint=endpoint,
            task_id=task_id,
            request_units=1,
            estimated_revenue_usd=revenue,
        )
    )

    profitability = ProfitabilityEngine(
        infra_cost_per_task_usd=settings.economics_infra_cost_per_task_usd,
        token_cost_per_1k_usd=settings.economics_token_cost_per_1k_usd,
        min_margin_usd=settings.economics_min_margin_usd,
        default_success_probability=1.0,
    )
    decision = profitability.evaluate(payload=payload, expected_payout_usd=revenue)
    db.merge(
        TaskEconomics(
            task_id=task_id,
            source_name="rapidapi",
            expected_payout_usd=revenue,
            estimated_cost_usd=decision.estimated_cost_usd,
            actual_payout_usd=None,
            expected_success_probability=1.0,
            margin_usd=decision.expected_margin_usd,
            status="queued",
        )
    )


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


@app.post("/v1/tasks", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(_verify_rapidapi_if_enabled)])
def create_task(
    payload: TaskCreateRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    x_rapidapi_user: str | None = Header(default=None, alias="X-RapidAPI-User"),
    x_rapidapi_subscription: str | None = Header(default=None, alias="X-RapidAPI-Subscription"),
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

    _register_rapidapi_usage(
        db=db,
        endpoint="POST /v1/tasks",
        task_id=task_id,
        subscriber_id=x_rapidapi_user,
        subscription=x_rapidapi_subscription,
        payload=payload.input_payload,
    )

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


@app.post("/v1/source/pull")
def pull_source_tasks(limit: int = 10) -> dict:
    if settings.task_source_mode != "mock_pull":
        return {"status": "disabled", "reason": "task_source_mode is not mock_pull"}
    async_result = ingest_source_tasks.delay(limit=limit)
    return {"status": "queued", "job_id": async_result.id, "limit": limit}


@app.get("/v1/economics/summary")
def economics_summary() -> dict:
    return get_economics_summary.delay().get(timeout=20)


@app.get("/v1/economics/kpis")
def economics_kpis(db: Session = Depends(get_db_session)) -> dict:
    now = datetime.now(timezone.utc)
    current_month = _month_key(now)
    previous_month_dt = now.replace(day=1)
    if previous_month_dt.month == 1:
        previous_month_dt = previous_month_dt.replace(year=previous_month_dt.year - 1, month=12)
    else:
        previous_month_dt = previous_month_dt.replace(month=previous_month_dt.month - 1)
    previous_month = _month_key(previous_month_dt)

    month_start = datetime.strptime(f"{current_month}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    prev_month_start = datetime.strptime(f"{previous_month}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)

    current_revenue = db.scalar(
        select(func.coalesce(func.sum(ApiUsageEvent.estimated_revenue_usd), 0.0)).where(ApiUsageEvent.created_at >= month_start)
    )
    current_active = db.scalar(
        select(func.count(func.distinct(ApiUsageEvent.subscriber_id))).where(ApiUsageEvent.created_at >= month_start)
    )
    prev_active_ids = {
        row[0]
        for row in db.execute(
            select(func.distinct(ApiUsageEvent.subscriber_id)).where(
                and_(ApiUsageEvent.created_at >= prev_month_start, ApiUsageEvent.created_at < month_start)
            )
        )
    }
    current_active_ids = {
        row[0]
        for row in db.execute(select(func.distinct(ApiUsageEvent.subscriber_id)).where(ApiUsageEvent.created_at >= month_start))
    }

    churn_like = 0.0
    if prev_active_ids:
        churn_like = round(len(prev_active_ids - current_active_ids) / len(prev_active_ids), 6)

    mrr = float(current_revenue or 0.0)
    arpu = round(mrr / max(1, int(current_active or 0)), 6)

    ECONOMICS_MRR_USD.set(mrr)
    ECONOMICS_ARPU_USD.set(arpu)
    ECONOMICS_CHURN_LIKE_RATE.set(churn_like)

    return {
        "month": current_month,
        "mrr_usd": mrr,
        "arpu_usd": arpu,
        "churn_like_rate": churn_like,
        "active_subscribers": int(current_active or 0),
    }


@app.post("/v1/economics/reconciliation/{month}")
def reconcile_month(month: str, payload: ReconciliationRequest, db: Session = Depends(get_db_session)) -> dict:
    try:
        month_start = datetime.strptime(f"{month}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Month must be YYYY-MM") from exc

    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    estimated = db.scalar(
        select(func.coalesce(func.sum(ApiUsageEvent.estimated_revenue_usd), 0.0)).where(
            and_(ApiUsageEvent.created_at >= month_start, ApiUsageEvent.created_at < next_month)
        )
    )
    estimated = float(estimated or 0.0)
    variance = round(payload.paid_amount_usd - estimated, 6)
    status_name = "matched" if abs(variance) <= 0.01 else ("overpaid" if variance > 0 else "underpaid")

    db.merge(
        PayoutReconciliation(
            month=month,
            estimated_revenue_usd=estimated,
            paid_amount_usd=payload.paid_amount_usd,
            variance_usd=variance,
            status=status_name,
        )
    )
    db.commit()
    return {
        "month": month,
        "estimated_revenue_usd": estimated,
        "paid_amount_usd": payload.paid_amount_usd,
        "variance_usd": variance,
        "status": status_name,
    }


@app.get("/v1/economics/reconciliation/{month}")
def get_reconciliation(month: str, db: Session = Depends(get_db_session)) -> dict:
    item = db.scalar(select(PayoutReconciliation).where(PayoutReconciliation.month == month))
    if item is None:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return {
        "month": item.month,
        "estimated_revenue_usd": item.estimated_revenue_usd,
        "paid_amount_usd": item.paid_amount_usd,
        "variance_usd": item.variance_usd,
        "status": item.status,
        "updated_at": item.updated_at,
    }


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
