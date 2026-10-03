"""Scoring engine and multi-attribute utility calculation.

Design Principles:
- Modular, small, documented, unit-tested functions.
- Multi-attribute utility: On-time probability, safety buffer, monetary cost, and comfort.
- Hard Budget Invariant: An over-budget plan can NEVER outrank an affordable plan with
  acceptable on-time confidence.
- Configurable weights via generator_config.json or parameter overrides.
"""

from __future__ import annotations

from typing import Any, Optional
from .models import Itinerary, SimulationMetrics, TransitMode

# Default weights from specification
DEFAULT_WEIGHTS = {
    "weight_p_ontime": 0.45,
    "weight_buffer": 0.20,
    "weight_cost": 0.25,
    "weight_comfort": 0.10,
}

# The absolute upper bound utility permitted for any over-budget plan.
# Any viable affordable plan (P >= 0.65, Cost <= Budget) will achieve a score >= 0.40.
# By capping over-budget plans at 0.35 max, we strictly guarantee the invariant:
# OVER_BUDGET_PLANS CAN NEVER OUTRANK AN AFFORDABLE HIGH-CONFIDENCE PLAN.
OVER_BUDGET_MAX_UTILITY = 0.35


def score_ontime_probability(p_ontime: float) -> float:
    """Calculate the normalized score for on-time arrival probability [0.0, 1.0]."""
    return max(0.0, min(1.0, float(p_ontime)))


def score_buffer_margin(buffer_minutes: int, target_buffer_minutes: int = 120) -> float:
    """Calculate the normalized score for remaining time buffer before deadline [0.0, 1.0].
    
    A buffer >= target_buffer_minutes receives a full 1.0 score.
    A negative buffer (already scheduled past deadline) receives 0.0.
    """
    if buffer_minutes <= 0 or target_buffer_minutes <= 0:
        return 0.0
    return min(1.0, buffer_minutes / float(target_buffer_minutes))


def score_cost_efficiency(fare_paise: int, budget_paise: int) -> float:
    """Calculate the normalized score for monetary cost [0.0, 1.0].
    
    If fare <= budget:
      Scale from 0.5 (spending full budget) up to 1.0 (zero cost).
    If fare > budget:
      Degrades rapidly below 0.5 down to 0.0.
    """
    if budget_paise <= 0:
        return 0.0

    if fare_paise <= budget_paise:
        # Savings bonus: 1.0 at free, 0.5 at exact budget
        fraction_spent = fare_paise / float(budget_paise)
        return 1.0 - (0.5 * fraction_spent)
    else:
        # Over budget penalty
        excess = (fare_paise - budget_paise) / float(budget_paise)
        return max(0.0, 0.5 * (1.0 - excess))


def score_itinerary_comfort(itinerary: Itinerary) -> float:
    """Calculate the comfort index [0.0, 1.0] based on transit modes and transfers.
    
    Base mode ratings:
    - Flight: 1.00
    - Train: 0.80
    - Bus: 0.60
    Each transfer incurs a small fatigue penalty (-0.05).
    """
    if not itinerary.legs:
        return 0.0

    mode_ratings = {
        TransitMode.FLIGHT: 1.00,
        TransitMode.TRAIN: 0.80,
        TransitMode.BUS: 0.60,
    }

    total_duration = max(1, itinerary.total_duration_minutes)
    weighted_rating = sum(
        mode_ratings.get(leg.mode, 0.60) * leg.duration_minutes
        for leg in itinerary.legs
    ) / float(total_duration)

    transfer_penalty = itinerary.num_transfers * 0.05
    return max(0.1, min(1.0, weighted_rating - transfer_penalty))


def calculate_raw_utility(
    p_score: float,
    buffer_score: float,
    cost_score: float,
    comfort_score: float,
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Compute the weighted composite utility score before budget constraint adjustment."""
    w = weights or DEFAULT_WEIGHTS
    wp = w.get("weight_p_ontime", 0.45)
    wb = w.get("weight_buffer", 0.20)
    wc = w.get("weight_cost", 0.25)
    wm = w.get("weight_comfort", 0.10)

    # Normalize weights if sum != 1.0
    total_w = wp + wb + wc + wm
    if total_w > 0:
        wp /= total_w
        wb /= total_w
        wc /= total_w
        wm /= total_w

    raw_utility = (wp * p_score) + (wb * buffer_score) + (wc * cost_score) + (wm * comfort_score)
    return max(0.0, min(1.0, raw_utility))


def enforce_budget_invariant(raw_utility: float, fare_paise: int, budget_paise: int) -> float:
    """Enforce the critical invariant: Over-budget plans can NEVER outrank an affordable high-confidence plan.
    
    If fare > budget, the utility is capped strictly at OVER_BUDGET_MAX_UTILITY (0.35).
    Any viable plan with fare <= budget and P(on-time) >= 0.65 will achieve a score > 0.40.
    """
    if fare_paise <= budget_paise:
        return raw_utility

    # Plan is over budget: cap utility below any viable affordable plan
    budget_ratio = fare_paise / float(budget_paise) if budget_paise > 0 else 2.0
    capped_score = min(raw_utility, OVER_BUDGET_MAX_UTILITY / max(1.0, budget_ratio))
    return max(0.0, capped_score)


def score_itinerary(
    itinerary: Itinerary,
    metrics: SimulationMetrics,
    buffer_minutes: int,
    budget_paise: int,
    weights: Optional[dict[str, float]] = None,
    target_buffer_minutes: int = 120,
) -> float:
    """Calculate the final utility score for an itinerary including all constraints."""
    s_p = score_ontime_probability(metrics.p_ontime)
    s_b = score_buffer_margin(buffer_minutes, target_buffer_minutes)
    s_c = score_cost_efficiency(itinerary.total_fare_paise, budget_paise)
    s_m = score_itinerary_comfort(itinerary)

    raw_score = calculate_raw_utility(s_p, s_b, s_c, s_m, weights)
    final_score = enforce_budget_invariant(raw_score, itinerary.total_fare_paise, budget_paise)
    return round(final_score, 4)
