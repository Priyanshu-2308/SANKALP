"""Pareto-optimal selection and recommendation triad extraction.

Design Principles:
- Multi-objective Pareto dominance filtering: (P(on-time) max, Cost min, Duration min).
- Extraction of exactly three clear choices: Safest, Balanced, and Cheapest.
- Clear separation between selected recommendations and pruned/excluded routes.
- Pure Python logic, zero I/O.
"""

from __future__ import annotations

from typing import Tuple

from .explanations import classify_exclusion, generate_recommendation_reason
from .models import (
    ExclusionRationale,
    Itinerary,
    RecommendationTag,
    ScoredItinerary,
    SimulationMetrics,
)


def is_pareto_dominated(
    candidate: Tuple[Itinerary, SimulationMetrics, int, float],
    others: list[Tuple[Itinerary, SimulationMetrics, int, float]],
) -> bool:
    """Check if a candidate is strictly Pareto-dominated by any other candidate.
    
    Candidate A dominates Candidate B iff:
      P_A >= P_B AND Cost_A <= Cost_B AND Duration_A <= Duration_B
      AND strictly better in at least one attribute.
    """
    itin_b, met_b, _, _ = candidate
    p_b = met_b.p_ontime
    cost_b = itin_b.total_fare_paise
    dur_b = itin_b.total_duration_minutes

    for itin_a, met_a, _, _ in others:
        if itin_a.itinerary_id == itin_b.itinerary_id:
            continue
        p_a = met_a.p_ontime
        cost_a = itin_a.total_fare_paise
        dur_a = itin_a.total_duration_minutes

        # Check weak dominance
        if p_a >= p_b and cost_a <= cost_b and dur_a <= dur_b:
            # Check strict improvement in at least one dimension
            if p_a > p_b or cost_a < cost_b or dur_a < dur_b:
                return True

    return False


def select_pareto_triad(
    evaluated_candidates: list[Tuple[Itinerary, SimulationMetrics, int, float]],
    budget_paise: int,
) -> Tuple[dict[RecommendationTag, ScoredItinerary], list[ExclusionRationale]]:
    """Filter candidates and extract the Safest, Balanced, and Cheapest options.
    
    Args:
        evaluated_candidates: List of (Itinerary, SimulationMetrics, buffer_minutes, utility_score)
        budget_paise: The user's target budget cap in paise.
        
    Returns:
        recommendations: Dictionary of RecommendationTag -> ScoredItinerary
        exclusions: List of ExclusionRationale for non-selected options.
    """
    if not evaluated_candidates:
        return {}, []

    # Sort all candidates by utility score descending as base ranking
    all_by_utility = sorted(evaluated_candidates, key=lambda item: item[3], reverse=True)

    # 1. Safest: Highest on-time probability within budget (or highest overall if none within budget)
    affordable = [c for c in all_by_utility if c[0].total_fare_paise <= budget_paise]
    pool_for_safest = affordable if affordable else all_by_utility
    # Sort by p_ontime descending, then buffer descending
    safest_item = max(pool_for_safest, key=lambda c: (c[1].p_ontime, c[2]))

    # 2. Balanced: Highest overall composite utility score
    balanced_item = all_by_utility[0]
    # If Balanced matches Safest, attempt to pick the next highest utility if distinct
    if balanced_item[0].itinerary_id == safest_item[0].itinerary_id and len(all_by_utility) > 1:
        # Check if 2nd option has solid utility
        candidate_2nd = all_by_utility[1]
        if candidate_2nd[3] >= 0.30:
            balanced_item = candidate_2nd

    # 3. Cheapest: Lowest total fare among plans with acceptable reliability (P >= 0.65)
    viable_cheapest_pool = [c for c in all_by_utility if c[1].p_ontime >= 0.65]
    if not viable_cheapest_pool:
        # Fallback to any route with non-zero probability
        viable_cheapest_pool = [c for c in all_by_utility if c[1].p_ontime > 0.10]
    if not viable_cheapest_pool:
        viable_cheapest_pool = all_by_utility

    cheapest_item = min(viable_cheapest_pool, key=lambda c: (c[0].total_fare_paise, -c[1].p_ontime))
    # If cheapest matches Safest or Balanced, look for next cheapest if available
    used_ids = {safest_item[0].itinerary_id, balanced_item[0].itinerary_id}
    if cheapest_item[0].itinerary_id in used_ids:
        remaining_cheapest = [c for c in viable_cheapest_pool if c[0].itinerary_id not in used_ids]
        if remaining_cheapest:
            cheapest_item = min(remaining_cheapest, key=lambda c: (c[0].total_fare_paise, -c[1].p_ontime))

    # Assemble recommendations
    selected_map: dict[RecommendationTag, ScoredItinerary] = {}
    chosen_ids: set[str] = set()

    # Create Safest
    itin_s, met_s, buf_s, u_s = safest_item
    reason_s = generate_recommendation_reason(RecommendationTag.SAFEST, itin_s, met_s, buf_s, budget_paise)
    selected_map[RecommendationTag.SAFEST] = ScoredItinerary(
        itinerary=itin_s,
        metrics=met_s,
        buffer_minutes=buf_s,
        utility_score=u_s,
        tag=RecommendationTag.SAFEST,
        plain_reason=reason_s,
    )
    chosen_ids.add(itin_s.itinerary_id)

    # Create Balanced (if distinct or fallback)
    itin_b, met_b, buf_b, u_b = balanced_item
    reason_b = generate_recommendation_reason(RecommendationTag.BALANCED, itin_b, met_b, buf_b, budget_paise)
    selected_map[RecommendationTag.BALANCED] = ScoredItinerary(
        itinerary=itin_b,
        metrics=met_b,
        buffer_minutes=buf_b,
        utility_score=u_b,
        tag=RecommendationTag.BALANCED,
        plain_reason=reason_b,
    )
    chosen_ids.add(itin_b.itinerary_id)

    # Create Cheapest (if distinct or fallback)
    itin_c, met_c, buf_c, u_c = cheapest_item
    reason_c = generate_recommendation_reason(RecommendationTag.CHEAPEST, itin_c, met_c, buf_c, budget_paise)
    selected_map[RecommendationTag.CHEAPEST] = ScoredItinerary(
        itinerary=itin_c,
        metrics=met_c,
        buffer_minutes=buf_c,
        utility_score=u_c,
        tag=RecommendationTag.CHEAPEST,
        plain_reason=reason_c,
    )
    chosen_ids.add(itin_c.itinerary_id)

    # Classify non-selected candidates for exclusion explanations
    exclusions: list[ExclusionRationale] = []
    for item in evaluated_candidates:
        itin, met, buf, _ = item
        if itin.itinerary_id not in chosen_ids:
            exclusion = classify_exclusion(itin, met, budget_paise, buf)
            exclusions.append(exclusion)

    return selected_map, exclusions
