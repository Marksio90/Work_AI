"""Factory for task source connectors."""

from __future__ import annotations

from packages.task_source.base import BaseTaskSource
from packages.task_source.mock_source import MockTaskSource


def create_task_source(source_name: str) -> BaseTaskSource:
    normalized = source_name.strip().lower()
    if normalized in {"mock", "mock_marketplace"}:
        return MockTaskSource()
    raise ValueError(f"Unsupported task source: {source_name}")
