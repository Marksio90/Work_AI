"""Walidator spójności i jakości odpowiedzi (miękkie reguły)."""

from __future__ import annotations

from packages.contracts.task_contract import TaskContract
from packages.validators.base import BaseValidator, ValidationIssue, ValidationReport


class ConsistencyValidator(BaseValidator):
    """Wykrywa niespójność i niską jakość, bez oznaczania błędów jako hard."""

    def validate(self, contract: TaskContract, output_payload: dict) -> ValidationReport:
        constraints = contract.constraints or {}
        issues: list[ValidationIssue] = []

        for field in constraints.get("quality_required_fields", []):
            value = output_payload.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(
                    ValidationIssue(
                        code="low_quality_missing_content",
                        message=f"Pole jakościowe '{field}' jest puste.",
                        path=f"$.{field}",
                        severity="warning",
                        hard=False,
                    )
                )

        for left, right in constraints.get("mutually_exclusive", []):
            if output_payload.get(left) is not None and output_payload.get(right) is not None:
                issues.append(
                    ValidationIssue(
                        code="inconsistent_mutually_exclusive",
                        message=f"Pola '{left}' i '{right}' nie mogą być jednocześnie ustawione.",
                        path="$",
                        severity="warning",
                        hard=False,
                    )
                )

        return ValidationReport(decision="pass", passed=not issues, issues=issues)
