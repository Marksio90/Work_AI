"""Prometheus metrics registry."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

TASKS_CREATED_TOTAL = Counter("tasks_created_total", "Number of created tasks")
TASKS_COMPLETED_TOTAL = Counter("tasks_completed_total", "Number of completed tasks", ["status"])
TASK_DURATION_SECONDS = Histogram("task_duration_seconds", "Task processing duration")


def render_metrics() -> tuple[bytes, str]:
    payload = generate_latest()
    return payload, CONTENT_TYPE_LATEST
