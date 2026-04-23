"""Model jawnej odpowiedzi końcowej zadania."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from packages.contracts.enums import FinalOutcome, TaskStatus
from packages.validators.base import ValidationReport


class ScoringResult(BaseModel):
    """Wynik scoringu odpowiedzi."""

    model_config = ConfigDict(extra="forbid")

    score: float | None = Field(default=None, ge=0.0)
    max_score: float | None = Field(default=None, gt=0.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Jawna odpowiedź końcowa z informacjami walidacji, scoringu i abstain."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    status: TaskStatus
    final_outcome: FinalOutcome
    output_payload: dict[str, Any] = Field(default_factory=dict)
    validation: ValidationReport
    scoring: ScoringResult
    abstain_reason: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)



    @staticmethod
    def outcome_from_validation(report: ValidationReport) -> FinalOutcome:
        """Mapuje decyzję walidacji na deterministyczny final_outcome."""

        if report.decision == "pass":
            return FinalOutcome.SUCCESS
        if report.decision == "abstain":
            return FinalOutcome.ABSTAINED
        return FinalOutcome.FAILURE

    def deterministic_json(self) -> str:
        """Zwraca deterministyczny JSON (sortowane klucze) użyteczny m.in. do fingerprintu."""

        payload = self.model_dump(mode="json", exclude_none=False, by_alias=True)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        """Zwraca stabilny fingerprint SHA-256 dla wyniku zadania."""

        return hashlib.sha256(self.deterministic_json().encode("utf-8")).hexdigest()
