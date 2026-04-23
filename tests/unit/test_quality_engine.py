from packages.scoring.quality_engine import QualityEngine
from packages.validators.base import ValidationIssue, ValidationReport


def test_quality_engine_success_threshold():
    engine = QualityEngine()
    report = ValidationReport(decision="pass", passed=True, issues=[])

    result = engine.score(
        validation_report=report,
        confidence_score=0.9,
        latency_ms=1200,
        repair_count=0,
        expected_fields=2,
        filled_fields=2,
        semantic_validity_score=1.0,
    )

    assert result.score >= 0.8
    assert result.details["recommended_outcome"] == "success"


def test_quality_engine_penalties_push_to_error():
    engine = QualityEngine()
    report = ValidationReport(
        decision="validation_error",
        passed=False,
        issues=[ValidationIssue(code="bad", message="bad", hard=True)],
    )

    result = engine.score(
        validation_report=report,
        confidence_score=0.1,
        latency_ms=9000,
        repair_count=10,
        expected_fields=4,
        filled_fields=1,
        semantic_validity_score=0.2,
    )

    assert result.details["latency_penalty"] == 0.2
    assert result.details["repair_penalty"] == 0.3
    assert result.details["recommended_outcome"] == "error"
