"""Task orchestrator implementing a deterministic execution pipeline."""

from __future__ import annotations

import time
from typing import Any

from packages.contracts.enums import FinalOutcome, TaskStatus
from packages.contracts.task_contract import TaskContract
from packages.contracts.task_result import TaskResult
from packages.providers.base import BaseLLMProvider
from packages.scoring.quality_engine import QualityEngine
from packages.validators.base import BaseValidator, ValidationReport
from packages.validators.composite_validator import CompositeValidator


class TaskOrchestrator:
    """Executes tasks through steps:

    accept → preprocess → choose strategy → inference → repair →
    validate → score → outcome → persist → telemetry.
    """

    def __init__(
        self,
        *,
        provider: BaseLLMProvider,
        validator: BaseValidator | None = None,
        quality_engine: QualityEngine | None = None,
    ) -> None:
        self._provider = provider
        self._validator = validator or CompositeValidator()
        self._quality_engine = quality_engine or QualityEngine()

    async def execute(self, contract: TaskContract) -> TaskResult:
        started = time.perf_counter()
        trace: dict[str, Any] = {"steps": []}

        self._step(trace, "accept", {"task_id": contract.task_id, "task_type": contract.task_type.value})
        processed = self._preprocess(contract)
        self._step(trace, "preprocess", processed["metadata"])

        strategy = self._choose_strategy(contract)
        self._step(trace, "choose strategy", strategy)

        output_payload = await self._inference(processed=processed, strategy=strategy)
        self._step(trace, "inference", {"output_keys": sorted(output_payload.keys())})

        repair_count, output_payload = self._repair(contract=contract, output_payload=output_payload)
        self._step(trace, "repair", {"repair_count": repair_count})

        validation = self._validate(contract=contract, output_payload=output_payload)
        self._step(trace, "validate", {"decision": validation.decision, "issues": len(validation.issues)})

        latency_ms = (time.perf_counter() - started) * 1000.0
        scoring = self._score(
            contract=contract,
            output_payload=output_payload,
            validation=validation,
            latency_ms=latency_ms,
            repair_count=repair_count,
        )
        self._step(trace, "score", {"score": scoring.score, "confidence": scoring.confidence})

        status, final_outcome, abstain_reason = self._outcome(validation=validation, scoring_details=scoring.details)
        self._step(trace, "outcome", {"status": status.value, "final_outcome": final_outcome.value})

        result = TaskResult(
            task_id=contract.task_id,
            status=status,
            final_outcome=final_outcome,
            output_payload=output_payload,
            validation=validation,
            scoring=scoring,
            abstain_reason=abstain_reason,
            metadata={"trace": trace, "strategy": strategy},
        )

        self._persist(result)
        self._step(trace, "persist", {"persisted": True})

        self._telemetry(contract=contract, result=result, latency_ms=latency_ms)
        self._step(trace, "telemetry", {"latency_ms": round(latency_ms, 2)})

        return result

    def _preprocess(self, contract: TaskContract) -> dict[str, Any]:
        payload = dict(contract.input_payload)
        payload["_task_type"] = contract.task_type.value
        return {"prompt_payload": payload, "metadata": {"input_keys": sorted(contract.input_payload.keys())}}

    def _choose_strategy(self, contract: TaskContract) -> dict[str, Any]:
        if contract.output_schema:
            return {"mode": "structured", "reason": "output_schema_present"}
        return {"mode": "text", "reason": "no_schema"}

    async def _inference(self, *, processed: dict[str, Any], strategy: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Task payload: {processed['prompt_payload']}"
        if strategy["mode"] == "structured":
            return await self._provider.generate_structured(prompt=prompt, schema={"type": "object"})
        text = await self._provider.generate_text(prompt=prompt)
        return {"text": text}

    def _repair(self, *, contract: TaskContract, output_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        required = (contract.output_schema or {}).get("required", [])
        repaired = dict(output_payload)
        repairs = 0

        for field in required:
            if field not in repaired:
                repaired[field] = None
                repairs += 1

        return repairs, repaired

    def _validate(self, *, contract: TaskContract, output_payload: dict[str, Any]) -> ValidationReport:
        return self._validator.validate(contract=contract, output_payload=output_payload)

    def _score(
        self,
        *,
        contract: TaskContract,
        output_payload: dict[str, Any],
        validation: ValidationReport,
        latency_ms: float,
        repair_count: int,
    ):
        expected_fields = len((contract.output_schema or {}).get("required", []))
        if expected_fields == 0:
            expected_fields = len(output_payload)
        filled_fields = sum(1 for value in output_payload.values() if value not in (None, "", [], {}))

        semantic_validity_score = 1.0 if validation.decision == "pass" else (0.65 if validation.decision == "abstain" else 0.25)
        confidence_score = 1.0 - min(1.0, (len(validation.issues) * 0.2))

        return self._quality_engine.score(
            validation_report=validation,
            confidence_score=confidence_score,
            latency_ms=latency_ms,
            repair_count=repair_count,
            expected_fields=expected_fields,
            filled_fields=filled_fields,
            semantic_validity_score=semantic_validity_score,
        )

    @staticmethod
    def _outcome(*, validation: ValidationReport, scoring_details: dict[str, Any]) -> tuple[TaskStatus, FinalOutcome, str | None]:
        recommendation = str(scoring_details.get("recommended_outcome", "error"))

        if validation.decision == "pass" and recommendation == "success":
            return TaskStatus.SUCCEEDED, FinalOutcome.SUCCESS, None
        if validation.decision == "abstain" or recommendation == "abstain":
            return TaskStatus.ABSTAINED, FinalOutcome.ABSTAINED, "quality_below_success_threshold"
        return TaskStatus.FAILED, FinalOutcome.FAILURE, None

    @staticmethod
    def _persist(result: TaskResult) -> None:
        """Persistence hook (placeholder)."""

    @staticmethod
    def _telemetry(*, contract: TaskContract, result: TaskResult, latency_ms: float) -> None:
        """Telemetry hook (placeholder)."""

    @staticmethod
    def _step(trace: dict[str, Any], name: str, details: dict[str, Any]) -> None:
        trace["steps"].append({"name": name, "details": details})
