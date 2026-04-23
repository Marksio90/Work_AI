from packages.contracts.task_contract import TaskContract
from packages.contracts.task_result import TaskResult
from packages.validators.base import ValidationReport


def test_contract_fingerprint_is_stable_and_idempotent():
    contract = TaskContract(
        task_id="fp-1",
        task_type="classification",
        input_payload={"a": 1, "b": 2},
        output_schema={},
        constraints={},
    )
    assert contract.fingerprint() == contract.fingerprint()


def test_task_result_fingerprint_is_stable():
    result = TaskResult(
        task_id="r-1",
        status="succeeded",
        final_outcome="success",
        output_payload={"label": "ok"},
        validation=ValidationReport(decision="pass", passed=True, issues=[]),
        scoring={"score": 1.0, "max_score": 1.0, "confidence": 1.0, "details": {}},
    )
    assert result.fingerprint() == result.fingerprint()
