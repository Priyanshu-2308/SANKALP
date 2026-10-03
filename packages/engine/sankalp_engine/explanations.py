"""Plain-language explanations and justification generator.

Design Principles:
- Generates clear, human-readable rationales for why routes were selected.
- Generates concise, understandable exclusion explanations for pruned candidates.
- Pure Python string formatting, zero hallucinations or external APIs.
"""

from __future__ import annotations

from .models import (
    ExclusionCode,
    ExclusionRationale,
    Itinerary,
    RecommendationTag,
    ScoredItinerary,
    SimulationMetrics,
)


def format_currency_inr(paise: int) -> str:
    """Format integer paise into Indian Rupee format (e.g. 125000 -> '₹1,250')."""
    rupees = paise // 100
    s = str(rupees)
    if len(s) <= 3:
        return f"₹{s}"
    # Indian numbering format: comma before last 3 digits, then every 2 digits
    last3 = s[-3:]
    remaining = s[:-3]
    parts = []
    while len(remaining) > 2:
        parts.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        parts.insert(0, remaining)
    formatted = ",".join(parts) + "," + last3
    return f"₹{formatted}"


def format_duration(minutes: int) -> str:
    """Format duration in minutes into 'Xh Ym'."""
    hours = minutes // 60
    mins = minutes % 60
    if hours == 0:
        return f"{mins}m"
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def generate_recommendation_reason(
    tag: RecommendationTag,
    itinerary: Itinerary,
    metrics: SimulationMetrics,
    buffer_minutes: int,
    budget_paise: int,
) -> str:
    """Generate a crisp 1-sentence plain-language justification for a chosen recommendation."""
    p_pct = f"{round(metrics.p_ontime * 100, 1)}%"
    buf_str = format_duration(buffer_minutes)
    fare_str = format_currency_inr(itinerary.total_fare_paise)

    if tag == RecommendationTag.SAFEST:
        if buffer_minutes > 0:
            return f"Highest on-time arrival certainty ({p_pct}) with a {buf_str} safety buffer before your deadline."
        return f"Highest on-time arrival certainty ({p_pct}) among all feasible options."

    elif tag == RecommendationTag.CHEAPEST:
        savings = budget_paise - itinerary.total_fare_paise
        if savings > 0:
            return f"Lowest fare at {fare_str} ({format_currency_inr(savings)} under budget) with a solid {p_pct} reliability index."
        return f"Lowest cost alternative at {fare_str} with {p_pct} on-time arrival chance."

    elif tag == RecommendationTag.BALANCED:
        mode_desc = "multi-modal" if itinerary.is_multimodal else itinerary.legs[0].mode.value.lower()
        return f"Best overall balance of speed ({format_duration(itinerary.total_duration_minutes)}), {p_pct} reliability, and price ({fare_str})."

    return f"Feasible alternative route arriving with {p_pct} on-time confidence."


def classify_exclusion(
    itinerary: Itinerary,
    metrics: SimulationMetrics,
    budget_paise: int,
    deadline_slack_minutes: int,
) -> ExclusionRationale:
    """Classify why an unselected itinerary was excluded and provide a plain-language explanation."""
    # Summary of the route
    if itinerary.is_multimodal:
        modes = " + ".join(l.mode.value.capitalize() for l in itinerary.legs)
        summary = f"{modes} route ({format_duration(itinerary.total_duration_minutes)})"
    else:
        summary = f"{itinerary.legs[0].operator_name} ({itinerary.legs[0].identifier})"

    # 1. Budget violation
    if itinerary.total_fare_paise > budget_paise:
        excess = itinerary.total_fare_paise - budget_paise
        return ExclusionRationale(
            itinerary_summary=summary,
            code=ExclusionCode.BUDGET_EXCEEDED,
            reason_text=f"Total cost ({format_currency_inr(itinerary.total_fare_paise)}) exceeds your budget by {format_currency_inr(excess)}.",
        )

    # 2. High disruption / missed connection risk
    if metrics.missed_connection_rate > 0.35:
        risk_pct = round(metrics.missed_connection_rate * 100, 1)
        return ExclusionRationale(
            itinerary_summary=summary,
            code=ExclusionCode.CONNECTION_RISK,
            reason_text=f"Transfer window carries a high risk ({risk_pct}%) of missed connection due to tight transfer buffer.",
        )

    # 3. Low overall on-time probability
    if metrics.p_ontime < 0.60:
        return ExclusionRationale(
            itinerary_summary=summary,
            code=ExclusionCode.DEADLINE_BREACH,
            reason_text=f"On-time arrival probability is only {round(metrics.p_ontime * 100, 1)}%, which is below the safe threshold.",
        )

    # 4. Pareto dominated
    return ExclusionRationale(
        itinerary_summary=summary,
        code=ExclusionCode.PARETO_DOMINATED,
        reason_text="Outperformed by another route in both on-time reliability and journey duration.",
    )
