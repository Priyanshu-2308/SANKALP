"""Top-level SANKALP Decision Engine orchestrator.

Design Principles:
- Connects Graph Search, Monte Carlo Simulation, Scoring, and Pareto Selection.
- Pure Python and NumPy, zero external I/O.
- Sub-second execution time suitable for real-time web requests.
- Transparent 'Simulated schedules' disclosure stamped on all results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .datasource import TransportDataSource
from .explanations import format_currency_inr
from .graph_search import find_candidate_itineraries
from .models import (
    IST,
    ExclusionCode,
    ExclusionRationale,
    Place,
    RecommendationTag,
    ScoredItinerary,
)
from .pareto import select_pareto_triad
from .scoring import score_itinerary
from .simulation import simulate_itinerary_delays


@dataclass(frozen=True)
class JourneyRecoveryResult:
    """The complete response returned by the decision engine."""
    origin: Place
    destination: Place
    deadline: datetime
    budget_paise: int
    recommendations: dict[RecommendationTag, ScoredItinerary]
    pruned_candidates: list[ExclusionRationale]
    total_candidates_searched: int
    execution_time_ms: float
    data_disclaimer: str = "Simulated schedules"

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin": self.origin.to_dict(),
            "destination": self.destination.to_dict(),
            "deadline": self.deadline.isoformat(),
            "budget_paise": self.budget_paise,
            "budget_inr": self.budget_paise // 100,
            "data_disclaimer": self.data_disclaimer,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "total_candidates_searched": self.total_candidates_searched,
            "recommendations": {
                tag.value.lower(): scored.to_dict()
                for tag, scored in self.recommendations.items()
            },
            "pruned_candidates": [
                pruned.to_dict() for pruned in self.pruned_candidates
            ],
        }


def find_journey_recovery(
    origin_id: str,
    destination_id: str,
    deadline: datetime,
    budget_paise: int,
    data_source: TransportDataSource,
    departure_after: Optional[datetime] = None,
    trials_count: int = 10000,
    seed: int = 42,
    weights: Optional[dict[str, float]] = None,
    max_transfers: int = 2,
) -> JourneyRecoveryResult:
    """Find multi-modal recovery journeys, evaluate on-time probability, and rank top 3 options.
    
    Args:
        origin_id: Place ID of current location.
        destination_id: Place ID of destination.
        deadline: Strict required arrival deadline.
        budget_paise: Budget cap in integer paise.
        data_source: TransportDataSource providing places and scheduled legs.
        departure_after: Earliest departure time (defaults to current time if None).
        trials_count: Number of Monte Carlo trials (default 10,000).
        seed: Seed for stochastic reproducibility.
        weights: Optional utility function weight overrides.
        max_transfers: Maximum allowed connection points (default 2 transfers).
    """
    start_time = time.perf_counter()

    # Timezone normalization
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=IST)
    if departure_after is None:
        departure_after = datetime.now(IST)
    elif departure_after.tzinfo is None:
        departure_after = departure_after.replace(tzinfo=IST)

    orig_place = data_source.get_place(origin_id)
    if not orig_place:
        raise ValueError(f"Origin place ID '{origin_id}' not found in transport dataset.")

    dest_place = data_source.get_place(destination_id)
    if not dest_place:
        raise ValueError(f"Destination place ID '{destination_id}' not found in transport dataset.")

    if orig_place.id == dest_place.id:
        raise ValueError("Origin and destination must be distinct places.")

    # 1. Graph Search: find candidate itineraries with <= max_transfers
    candidates, initial_pruned = find_candidate_itineraries(
        origin_id=orig_place.id,
        destination_id=dest_place.id,
        departure_after=departure_after,
        deadline=deadline,
        data_source=data_source,
        max_transfers=max_transfers,
    )

    if not candidates:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        # Explicit empty state explaining why no routes could be served
        fallback_pruned = initial_pruned or [
            ExclusionRationale(
                itinerary_summary="No routes available",
                code=ExclusionCode.DEADLINE_BREACH,
                reason_text="No transit options found departing after the start time and reaching before the deadline.",
            )
        ]
        return JourneyRecoveryResult(
            origin=orig_place,
            destination=dest_place,
            deadline=deadline,
            budget_paise=budget_paise,
            recommendations={},
            pruned_candidates=fallback_pruned,
            total_candidates_searched=0,
            execution_time_ms=elapsed_ms,
        )

    # 2. Monte Carlo Simulation and Scoring for each candidate
    evaluated: list[tuple[Any, Any, int, float]] = []
    for itin in candidates:
        metrics = simulate_itinerary_delays(
            itinerary=itin,
            deadline=deadline,
            trials_count=trials_count,
            seed=seed,
        )
        buffer_minutes = int((deadline - itin.arrival_time).total_seconds() / 60.0)
        utility = score_itinerary(
            itinerary=itin,
            metrics=metrics,
            buffer_minutes=buffer_minutes,
            budget_paise=budget_paise,
            weights=weights,
        )
        evaluated.append((itin, metrics, buffer_minutes, utility))

    # 3. Pareto selection of the Triad (Safest, Balanced, Cheapest)
    recommendations, unselected_exclusions = select_pareto_triad(
        evaluated_candidates=evaluated,
        budget_paise=budget_paise,
    )

    all_pruned = initial_pruned + unselected_exclusions
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return JourneyRecoveryResult(
        origin=orig_place,
        destination=dest_place,
        deadline=deadline,
        budget_paise=budget_paise,
        recommendations=recommendations,
        pruned_candidates=all_pruned,
        total_candidates_searched=len(candidates),
        execution_time_ms=elapsed_ms,
    )
