"""SANKALP Journey Recovery Engine package."""

from .datasource import TransportDataSource
from .engine import JourneyRecoveryResult, find_journey_recovery
from .explanations import (
    classify_exclusion,
    format_currency_inr,
    format_duration,
    generate_recommendation_reason,
)
from .generator import SeededScheduleGenerator
from .geo import detour_ratio, haversine_distance_km, place_distance_km
from .graph_search import find_candidate_itineraries
from .models import (
    IST,
    ExclusionCode,
    ExclusionRationale,
    Itinerary,
    Leg,
    Place,
    PlaceType,
    RecommendationTag,
    ScoredItinerary,
    SimulationMetrics,
    Transfer,
    TransitMode,
)
from .pareto import is_pareto_dominated, select_pareto_triad
from .scoring import (
    enforce_budget_invariant,
    score_buffer_margin,
    score_cost_efficiency,
    score_itinerary,
    score_itinerary_comfort,
    score_ontime_probability,
)
from .simulation import simulate_itinerary_delays
from .statistics import sample_lognormal_delays, wilson_score_interval

__all__ = [
    "IST",
    "TransitMode",
    "PlaceType",
    "RecommendationTag",
    "ExclusionCode",
    "Place",
    "Leg",
    "Transfer",
    "Itinerary",
    "SimulationMetrics",
    "ScoredItinerary",
    "ExclusionRationale",
    "TransportDataSource",
    "SeededScheduleGenerator",
    "find_candidate_itineraries",
    "simulate_itinerary_delays",
    "score_itinerary",
    "enforce_budget_invariant",
    "select_pareto_triad",
    "find_journey_recovery",
    "JourneyRecoveryResult",
    "haversine_distance_km",
    "place_distance_km",
    "detour_ratio",
    "wilson_score_interval",
    "format_currency_inr",
    "format_duration",
]
