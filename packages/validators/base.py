"""Bazowe modele i interfejs walidatorów."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from packages.contracts.task_contract import TaskContract

ValidationDecision = Literal["pass", "validation_error", "abstain"]
IssueSeverity = Literal["error", "warning"]


class ValidationIssue(BaseModel):
    """Pojedynczy problem wykryty podczas walidacji."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: str = Field(default="$")
    severity: IssueSeverity = Field(default="error")
    hard: bool = Field(default=False)


class ValidationReport(BaseModel):
    """Raport końcowy z walidacji payloadu odpowiedzi."""

    model_config = ConfigDict(extra="forbid")

    decision: ValidationDecision = Field(default="pass")
    passed: bool = Field(default=True)
    issues: list[ValidationIssue] = Field(default_factory=list)


class BaseValidator(ABC):
    """Abstrakcyjny interfejs walidatora."""

    @abstractmethod
    def validate(self, contract: TaskContract, output_payload: dict) -> ValidationReport:
        """Zwraca raport walidacji dla payloadu odpowiedzi."""
