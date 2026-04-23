"""Offline evaluation harness for local fixture-based quality checks."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.contracts.task_contract import TaskContract
from packages.orchestrator.task_orchestrator import TaskOrchestrator
from packages.providers.mock_provider import MockProvider


class FixtureAwareProvider(MockProvider):
    """Mock provider with deterministic branches based on fixture metadata."""

    async def generate_structured(self, *, prompt: str, schema: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        if "fixture-error-1" in prompt:
            raise RuntimeError("fixture-simulated-provider-error")
        if "fixture-abstain-1" in prompt:
            return {"title": "Skrót", "summary": ""}
        if "fixture-success-1" in prompt:
            return {"customer": "Jan Kowalski", "quantity": 2}
        return await super().generate_structured(prompt=prompt, schema=schema, **kwargs)


def load_fixtures(fixtures_dir: Path) -> list[TaskContract]:
    contracts: list[TaskContract] = []
    for path in sorted(fixtures_dir.glob("*.json")):
        contracts.append(TaskContract.model_validate_json(path.read_text(encoding="utf-8")))
    return contracts


async def evaluate(contracts: list[TaskContract]) -> dict[str, Any]:
    orchestrator = TaskOrchestrator(provider=FixtureAwareProvider())
    rows: list[dict[str, Any]] = []

    for contract in contracts:
        started = time.perf_counter()
        result = await orchestrator.execute(contract)
        elapsed = (time.perf_counter() - started) * 1000
        rows.append(
            {
                "task_id": contract.task_id,
                "status": result.status.value,
                "final_outcome": result.final_outcome.value,
                "score": result.scoring.score,
                "latency_ms": round(elapsed, 2),
                "valid_output": result.validation.decision == "pass",
            }
        )

    quality_scores = [row["score"] for row in rows if isinstance(row.get("score"), (int, float))]
    avg_latency = statistics.fmean(row["latency_ms"] for row in rows) if rows else 0.0
    valid_rate = (sum(1 for row in rows if row["valid_output"]) / len(rows)) if rows else 0.0

    return {
        "summary": {
            "tasks_total": len(rows),
            "quality_avg": round(statistics.fmean(quality_scores), 4) if quality_scores else 0.0,
            "latency_avg_ms": round(avg_latency, 2),
            "valid_output_rate": round(valid_rate, 4),
        },
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline evaluation on task fixtures.")
    parser.add_argument("--fixtures-dir", default="tests/fixtures/tasks", help="Path to task fixtures")
    parser.add_argument("--report-path", default="artifacts/offline-eval-report.json", help="Output report path")
    args = parser.parse_args()

    fixtures_dir = Path(args.fixtures_dir)
    report_path = Path(args.report_path)
    contracts = load_fixtures(fixtures_dir)

    report = asyncio.run(evaluate(contracts))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
