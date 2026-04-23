"""Mock paid task platform used for local development."""

from __future__ import annotations

from typing import Any

from packages.task_source.base import SourceTask, SubmitResult


class MockTaskSource:
    """Deterministic in-process task source with synthetic payouts."""

    name = "mock_marketplace"

    def __init__(self) -> None:
        self._accepted: set[str] = set()
        self._payouts: dict[str, float] = {}

    def fetch_available_tasks(self, *, limit: int = 20) -> list[SourceTask]:
        tasks: list[SourceTask] = []
        for i in range(1, limit + 1):
            external_task_id = f"mkp-{i:04d}"
            payout = round(0.03 + (i % 5) * 0.01, 4)
            self._payouts[external_task_id] = payout
            tasks.append(
                SourceTask(
                    external_task_id=external_task_id,
                    task_type="classification",
                    input_payload={"text": f"Classify item #{i}", "priority": "normal"},
                    output_schema={
                        "type": "object",
                        "required": ["label"],
                        "properties": {"label": {"type": "string"}},
                    },
                    constraints={"allowed_labels": ["A", "B", "C"]},
                    metadata={"source": self.name},
                    payout_usd=payout,
                )
            )
        return tasks

    def accept_task(self, external_task_id: str) -> bool:
        if external_task_id in self._accepted:
            return False
        self._accepted.add(external_task_id)
        return True

    def submit_result(self, *, external_task_id: str, output: dict[str, Any], final_outcome: str) -> SubmitResult:
        _ = output
        base = self.get_payout(external_task_id)
        payout = base if final_outcome == "success" else 0.0
        return SubmitResult(accepted=True, payout_usd=payout, message="submitted")

    def get_payout(self, external_task_id: str) -> float:
        if external_task_id in self._payouts:
            return self._payouts[external_task_id]
        try:
            number = int(external_task_id.split("-")[-1])
        except Exception:
            number = 1
        payout = round(0.03 + (number % 5) * 0.01, 4)
        self._payouts[external_task_id] = payout
        return payout

    def get_account_balance(self) -> float:
        return round(sum(self._payouts.values()), 4)
