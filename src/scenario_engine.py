"""Transparent scenario estimates; these are not employment predictions."""

from typing import Any


MODERATE_WEIGHTS = {"base_match": 0.75, "trend_score": 0.25}
FAST_WEIGHTS = {
    "base_match": 0.60,
    "trend_score": 0.35,
    "ai_technology_readiness": 0.05,
}


def _weighted_estimate(
    match: dict[str, Any],
    weights: dict[str, float],
) -> tuple[float | None, dict[str, float]]:
    available = {
        key: float(match[key])
        for key in weights
        if match.get(key) is not None
    }
    total_weight = sum(weights[key] for key in available)
    if not total_weight:
        return None, {}
    estimate = sum(
        available[key] * weights[key] for key in available
    ) / total_weight
    effective_weights = {
        key: weights[key] / total_weight for key in available
    }
    return estimate, effective_weights


def build_scenario_comparison(
    matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Estimate role scores under moderate and fast-change assumptions.

    Missing trend evidence or AI-related technology data is omitted from the
    formula and remaining weights are renormalized. Missing evidence is never
    converted to zero.
    """
    rows = []
    for match in matches:
        base = match.get("base_match", match.get("overall"))
        if base is None:
            continue
        scenario_input = {
            "base_match": float(base),
            "trend_score": (
                float(match["trend_score"])
                if match.get("trend_adjusted")
                and match.get("trend_score") is not None
                else None
            ),
            "ai_technology_readiness": match.get("ai_technology_readiness"),
        }
        moderate, moderate_weights = _weighted_estimate(
            scenario_input, MODERATE_WEIGHTS
        )
        fast, fast_weights = _weighted_estimate(scenario_input, FAST_WEIGHTS)
        rows.append(
            {
                "role": match["role"],
                "base_match": float(base),
                "trend_score": scenario_input["trend_score"],
                "ai_technology_readiness": scenario_input[
                    "ai_technology_readiness"
                ],
                "moderate_ai_disruption": moderate,
                "fast_ai_disruption": fast,
                "moderate_weights": moderate_weights,
                "fast_weights": fast_weights,
                "trend_direction": match.get(
                    "trend_direction", "Insufficient signal"
                ),
            }
        )
    return rows
