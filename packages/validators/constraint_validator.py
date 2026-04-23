"""Walidator twardych ograniczeń kontraktu."""

from __future__ import annotations

from packages.contracts.task_contract import TaskContract
from packages.validators.base import BaseValidator, ValidationIssue, ValidationReport


class ConstraintValidator(BaseValidator):
    """Waliduje constraints traktowane jako twarde wymagania kontraktu."""

    def validate(self, contract: TaskContract, output_payload: dict) -> ValidationReport:
        constraints = contract.constraints or {}
        issues: list[ValidationIssue] = []

        for field in constraints.get("required_non_empty", []):
            value = output_payload.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(
                    ValidationIssue(
                        code="required_non_empty",
                        message=f"Pole '{field}' musi być niepuste.",
                        path=f"$.{field}",
                        hard=True,
                    )
                )

        for field, forbidden_values in constraints.get("forbidden_values", {}).items():
            value = output_payload.get(field)
            if value in forbidden_values:
                issues.append(
                    ValidationIssue(
                        code="forbidden_value",
                        message=f"Pole '{field}' zawiera niedozwoloną wartość.",
                        path=f"$.{field}",
                        hard=True,
                    )
                )

        for field, min_len in constraints.get("min_length", {}).items():
            value = output_payload.get(field)
            if isinstance(value, str) and len(value) < int(min_len):
                issues.append(
                    ValidationIssue(
                        code="min_length",
                        message=f"Pole '{field}' jest krótsze niż {min_len}.",
                        path=f"$.{field}",
                        hard=True,
                    )
                )

        for field, max_len in constraints.get("max_length", {}).items():
            value = output_payload.get(field)
            if isinstance(value, str) and len(value) > int(max_len):
                issues.append(
                    ValidationIssue(
                        code="max_length",
                        message=f"Pole '{field}' przekracza długość {max_len}.",
                        path=f"$.{field}",
                        hard=True,
                    )
                )

        for field, bounds in constraints.get("numeric_ranges", {}).items():
            if field not in output_payload:
                continue
            value = output_payload[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            minimum = bounds.get("min")
            maximum = bounds.get("max")
            if minimum is not None and value < minimum:
                issues.append(
                    ValidationIssue(
                        code="below_minimum",
                        message=f"Pole '{field}' jest poniżej minimum {minimum}.",
                        path=f"$.{field}",
                        hard=True,
                    )
                )
            if maximum is not None and value > maximum:
                issues.append(
                    ValidationIssue(
                        code="above_maximum",
                        message=f"Pole '{field}' przekracza maksimum {maximum}.",
                        path=f"$.{field}",
                        hard=True,
                    )
                )

        return ValidationReport(decision="pass", passed=not issues, issues=issues)
