"""Transparent quality scoring engine for task outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from packages.contracts.task_result import ScoringResult
from packages.validators.base import ValidationReport


@dataclass(frozen=True)
class QualityWeights:
    """Weights for each positive signal in the quality formula."""

    structural_validity: float = 0.30
    semantic_validity: float = 0.25
    completeness: float = 0.20
    confidence: float = 0.25


@dataclass(frozen=True)
class QualityThresholds:
    """Decision thresholds for score-based outcome recommendation."""

    success_min: float = 0.80
    abstain_min: float = 0.55


class QualityEngine:
    """Computes deterministic quality score with explicit penalties.

    Formula (all terms normalized to [0, 1]):
      base_score =
          w_s * structural_validity_score +
          w_m * semantic_validity_score +
          w_c * completeness_score +
          w_f * confidence_score

      final_score = clamp(base_score - latency_penalty - repair_penalty, 0, 1)
    """

    def __init__(
        self,
        *,
        weights: QualityWeights | None = None,
        thresholds: QualityThresholds | None = None,
    ) -> None:
        self._weights = weights or QualityWeights()
        self._thresholds = thresholds or QualityThresholds()

    def score(
        self,
        *,
        validation_report: ValidationReport,
        confidence_score: float,
        latency_ms: float,
        repair_count: int,
        expected_fields: int,
        filled_fields: int,
        semantic_validity_score: float,
    ) -> ScoringResult:
        structural_validity_score = self._structural_validity_score(validation_report)
        completeness_score = self._completeness_score(expected_fields=expected_fields, filled_fields=filled_fields)

        confidence_score = _clamp01(confidence_score)
        semantic_validity_score = _clamp01(semantic_validity_score)
        latency_penalty = self._latency_penalty(latency_ms)
        repair_penalty = self._repair_penalty(repair_count)

        base_score = (
            self._weights.structural_validity * structural_validity_score
            + self._weights.semantic_validity * semantic_validity_score
            + self._weights.completeness * completeness_score
            + self._weights.confidence * confidence_score
        )
        final_score = _clamp01(base_score - latency_penalty - repair_penalty)

        if final_score >= self._thresholds.success_min:
            recommended_outcome = "success"
        elif final_score >= self._thresholds.abstain_min:
            recommended_outcome = "abstain"
        else:
            recommended_outcome = "error"

        return ScoringResult(
            score=round(final_score, 6),
            max_score=1.0,
            confidence=confidence_score,
            details={
                "formula": "final=max(0,min(1,base-latency_penalty-repair_penalty))",
                "base_score": round(base_score, 6),
                "structural_validity_score": round(structural_validity_score, 6),
                "semantic_validity_score": round(semantic_validity_score, 6),
                "completeness_score": round(completeness_score, 6),
                "confidence_score": round(confidence_score, 6),
                "latency_penalty": round(latency_penalty, 6),
                "repair_penalty": round(repair_penalty, 6),
                "weights": {
                    "structural_validity": self._weights.structural_validity,
                    "semantic_validity": self._weights.semantic_validity,
                    "completeness": self._weights.completeness,
                    "confidence": self._weights.confidence,
                },
                "thresholds": {
                    "success_min": self._thresholds.success_min,
                    "abstain_min": self._thresholds.abstain_min,
                },
                "recommended_outcome": recommended_outcome,
                "repair_count": repair_count,
                "latency_ms": latency_ms,
                "filled_fields": filled_fields,
                "expected_fields": expected_fields,
            },
        )

    @staticmethod
    def _structural_validity_score(validation_report: ValidationReport) -> float:
        if validation_report.passed and validation_report.decision == "pass":
            return 1.0

        hard_issues = sum(1 for issue in validation_report.issues if issue.hard)
        soft_issues = sum(1 for issue in validation_report.issues if not issue.hard)

        score = 1.0 - min(1.0, (hard_issues * 0.5) + (soft_issues * 0.15))
        return _clamp01(score)

    @staticmethod
    def _completeness_score(*, expected_fields: int, filled_fields: int) -> float:
        if expected_fields <= 0:
            return 1.0
        return _clamp01(filled_fields / expected_fields)

    @staticmethod
    def _latency_penalty(latency_ms: float) -> float:
        if latency_ms <= 1_500:
            return 0.0
        if latency_ms <= 4_000:
            return 0.05
        if latency_ms <= 8_000:
            return 0.10
        return 0.20

    @staticmethod
    def _repair_penalty(repair_count: int) -> float:
        if repair_count <= 0:
            return 0.0
        return min(0.30, repair_count * 0.08)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
