from packages.contracts.execution_policy import ExecutionPolicy
from packages.contracts.task_contract import TaskContract
from packages.validators.composite_validator import CompositeValidator


def _contract(abstain_allowed: bool = True) -> TaskContract:
    return TaskContract(
        task_id="t1",
        task_type="generation",
        input_payload={"prompt": "x"},
        output_schema={
            "type": "object",
            "required": ["summary"],
            "properties": {"summary": {"type": "string"}},
            "additionalProperties": True,
        },
        constraints={"quality_required_fields": ["summary"]},
        execution_policy=ExecutionPolicy(abstain_allowed=abstain_allowed),
    )


def test_composite_validator_abstain_when_soft_issue_and_allowed():
    validator = CompositeValidator()
    report = validator.validate(_contract(abstain_allowed=True), {"summary": ""})

    assert report.decision == "abstain"
    assert report.passed is False


def test_composite_validator_validation_error_when_soft_issue_and_not_allowed():
    validator = CompositeValidator()
    report = validator.validate(_contract(abstain_allowed=False), {"summary": ""})

    assert report.decision == "validation_error"
    assert report.passed is False
