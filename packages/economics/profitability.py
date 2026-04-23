"""Profitability engine for paid external tasks."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any


@dataclass(slots=True)
class ProfitabilityDecision:
    estimated_cost_usd: float
    expected_payout_usd: float
    expected_success_probability: float
    expected_margin_usd: float
    should_accept: bool


class ProfitabilityEngine:
    """Simple deterministic margin model used before accepting a source task."""

    def __init__(
        self,
        *,
        infra_cost_per_task_usd: float,
        token_cost_per_1k_usd: float,
        min_margin_usd: float,
        default_success_probability: float,
    ) -> None:
        self._infra_cost_per_task_usd = infra_cost_per_task_usd
        self._token_cost_per_1k_usd = token_cost_per_1k_usd
        self._min_margin_usd = min_margin_usd
        self._default_success_probability = default_success_probability

    def evaluate(self, *, payload: dict[str, Any], expected_payout_usd: float) -> ProfitabilityDecision:
        prompt_size = len(str(payload))
        estimated_tokens = max(150, ceil(prompt_size / 4) * 2)
        token_cost = (estimated_tokens / 1000.0) * self._token_cost_per_1k_usd
        estimated_cost = round(self._infra_cost_per_task_usd + token_cost, 6)

        expected_revenue = expected_payout_usd * self._default_success_probability
        expected_margin = round(expected_revenue - estimated_cost, 6)

        return ProfitabilityDecision(
            estimated_cost_usd=estimated_cost,
            expected_payout_usd=round(expected_payout_usd, 6),
            expected_success_probability=self._default_success_probability,
            expected_margin_usd=expected_margin,
            should_accept=expected_margin >= self._min_margin_usd,
        )
