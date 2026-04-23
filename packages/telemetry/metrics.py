"""Prometheus metrics registry."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

TASKS_CREATED_TOTAL = Counter("tasks_created_total", "Number of created tasks")
TASKS_COMPLETED_TOTAL = Counter("tasks_completed_total", "Number of completed tasks", ["status"])
TASK_DURATION_SECONDS = Histogram("task_duration_seconds", "Task processing duration")

ECONOMICS_MRR_USD = Gauge("economics_mrr_usd", "Estimated monthly recurring revenue in USD")
ECONOMICS_ARPU_USD = Gauge("economics_arpu_usd", "Average revenue per active subscriber in USD")
ECONOMICS_CHURN_LIKE_RATE = Gauge("economics_churn_like_rate", "Churn-like ratio based on active subscribers")


def render_metrics() -> tuple[bytes, str]:
    payload = generate_latest()
    return payload, CONTENT_TYPE_LATEST
