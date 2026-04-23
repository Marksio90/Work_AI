"""Walidator kompozytowy z deterministycznymi regułami decyzji."""

from __future__ import annotations

from packages.contracts.task_contract import TaskContract
from packages.validators.base import BaseValidator, ValidationIssue, ValidationReport
from packages.validators.consistency_validator import ConsistencyValidator
from packages.validators.constraint_validator import ConstraintValidator
from packages.validators.schema_validator import SchemaValidator


class CompositeValidator(BaseValidator):
    """Uruchamia wszystkie walidatory i zwraca pojedynczą decyzję."""

    def __init__(self) -> None:
        self._validators: tuple[BaseValidator, ...] = (
            SchemaValidator(),
            ConstraintValidator(),
            ConsistencyValidator(),
        )

    def validate(self, contract: TaskContract, output_payload: dict) -> ValidationReport:
        issues: list[ValidationIssue] = []
        for validator in self._validators:
            report = validator.validate(contract=contract, output_payload=output_payload)
            issues.extend(report.issues)

        has_hard_errors = any(issue.hard for issue in issues)
        has_soft_quality_or_consistency = any(not issue.hard for issue in issues)
        abstain_allowed = contract.execution_policy.abstain_allowed

        if has_hard_errors:
            decision = "validation_error"
            passed = False
        elif has_soft_quality_or_consistency and abstain_allowed:
            decision = "abstain"
            passed = False
        elif has_soft_quality_or_consistency:
            decision = "validation_error"
            passed = False
        else:
            decision = "pass"
            passed = True

        return ValidationReport(decision=decision, passed=passed, issues=issues)
