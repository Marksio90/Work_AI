"""Walidator zgodności ze schematem output_schema."""

from __future__ import annotations

from typing import Any

from packages.contracts.task_contract import TaskContract
from packages.validators.base import BaseValidator, ValidationIssue, ValidationReport


_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "object": (dict,),
    "array": (list,),
    "null": (type(None),),
}


class SchemaValidator(BaseValidator):
    """Waliduje output_payload względem prostego podzbioru JSON Schema."""

    def validate(self, contract: TaskContract, output_payload: dict) -> ValidationReport:
        issues: list[ValidationIssue] = []
        schema = contract.output_schema or {}

        required = schema.get("required", [])
        for field in required:
            if field not in output_payload:
                issues.append(
                    ValidationIssue(
                        code="missing_required_field",
                        message=f"Brak wymaganego pola '{field}'.",
                        path=f"$.{field}",
                        hard=True,
                    )
                )

        properties = schema.get("properties", {})
        for field, spec in properties.items():
            if field not in output_payload:
                continue
            expected_type = spec.get("type")
            if expected_type is None:
                continue

            value = output_payload[field]
            if not self._is_instance(value=value, expected_type=expected_type):
                issues.append(
                    ValidationIssue(
                        code="type_mismatch",
                        message=(
                            f"Pole '{field}' ma niepoprawny typ. "
                            f"Oczekiwano '{expected_type}'."
                        ),
                        path=f"$.{field}",
                        hard=True,
                    )
                )

        if schema.get("additionalProperties") is False and properties:
            allowed = set(properties.keys())
            for field in sorted(output_payload.keys()):
                if field not in allowed:
                    issues.append(
                        ValidationIssue(
                            code="additional_property_not_allowed",
                            message=f"Pole '{field}' nie jest dozwolone przez schema.",
                            path=f"$.{field}",
                            hard=True,
                        )
                    )

        return ValidationReport(
            decision="pass",
            passed=not issues,
            issues=issues,
        )

    def _is_instance(self, value: Any, expected_type: str | list[str]) -> bool:
        if isinstance(expected_type, str):
            expected = [expected_type]
        else:
            expected = list(expected_type)

        for item in expected:
            py_types = _TYPE_MAP.get(item)
            if not py_types:
                continue
            if item == "integer" and isinstance(value, bool):
                continue
            if isinstance(value, py_types):
                return True
        return False
