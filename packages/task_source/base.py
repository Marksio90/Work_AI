"""Task source abstractions for external paid-task marketplaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class SourceTask:
    """External task offered by a paid platform."""

    external_task_id: str
    task_type: str
    input_payload: dict[str, Any]
    output_schema: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    payout_usd: float = 0.0


@dataclass(slots=True)
class SubmitResult:
    """Submission result returned by source connector."""

    accepted: bool
    payout_usd: float
    message: str = ""


class BaseTaskSource(Protocol):
    """Required connector surface for external task platforms."""

    name: str

    def fetch_available_tasks(self, *, limit: int = 20) -> list[SourceTask]: ...

    def accept_task(self, external_task_id: str) -> bool: ...

    def submit_result(self, *, external_task_id: str, output: dict[str, Any], final_outcome: str) -> SubmitResult: ...

    def get_payout(self, external_task_id: str) -> float: ...

    def get_account_balance(self) -> float: ...
