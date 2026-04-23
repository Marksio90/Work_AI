"""Structured JSON logging and correlation-id middleware."""

from __future__ import annotations

import logging
import uuid

import structlog
from fastapi import Request


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level)
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(CorrelationIdFilter())

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
    )


async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id", uuid.uuid4().hex)
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response
