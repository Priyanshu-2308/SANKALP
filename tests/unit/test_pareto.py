"""Unit tests for Pareto selection and triad extraction."""

from datetime import datetime
from sankalp_engine.models import (
    IST,
    Itinerary,
    Leg,
    RecommendationTag,
    SimulationMetrics,
    TransitMode,
)
from sankalp_engine.pareto import is_pareto_dominated, select_pareto_triad


def make_dummy(itin_id: str, fare: int, duration: int, p_ontime: float, utility: float):
    t1 = datetime(2026, 10, 6, 8, 0, tzinfo=IST)
    t2 = datetime(2026, 10, 6, 8 + duration // 60, duration % 60, tzinfo=IST)
    leg = Leg(
        leg_id=f"leg_{itin_id}", origin_id="A", destination_id="B",
        mode=TransitMode.TRAIN, departure_time=t1, arrival_time=t2,
        duration_minutes=duration, distance_km=200.0, fare_paise=fare,
        operator_name="IR", identifier="101",
    )
    itin = Itinerary(
        itinerary_id=itin_id, legs=[leg], transfers=[],
        total_duration_minutes=duration, total_fare_paise=fare,
        departure_time=t1, arrival_time=t2,
    )
    met = SimulationMetrics(
        p_ontime=p_ontime, p_ontime_ci_low=p_ontime - 0.02, p_ontime_ci_high=p_ontime + 0.02,
        trials_count=10000, median_delay_minutes=10.0, p90_delay_minutes=20.0,
        missed_connection_rate=0.0,
    )
    buffer_mins = 60
    return (itin, met, buffer_mins, utility)


def test_pareto_dominance() -> None:
    # A: 95% on-time, ₹1,000, 180 mins
    cand_a = make_dummy("A", 100000, 180, 0.95, 0.85)
    # B: 85% on-time, ₹1,500, 240 mins (strictly worse than A in ALL dimensions)
    cand_b = make_dummy("B", 150000, 240, 0.85, 0.60)
    # C: 99% on-time, ₹3,000, 90 mins (higher price, but faster and more reliable)
    cand_c = make_dummy("C", 300000, 90, 0.99, 0.75)

    assert is_pareto_dominated(cand_b, [cand_a, cand_c]) is True
    assert is_pareto_dominated(cand_a, [cand_b, cand_c]) is False
    assert is_pareto_dominated(cand_c, [cand_a, cand_b]) is False


def test_select_pareto_triad() -> None:
    budget = 250000  # ₹2,500
    c1 = make_dummy("P1_safest", 200000, 200, 0.97, 0.80)
    c2 = make_dummy("P2_cheapest", 80000, 240, 0.82, 0.78)
    c3 = make_dummy("P3_balanced", 140000, 150, 0.92, 0.86)

    evaluated = [c1, c2, c3]
    triad, exclusions = select_pareto_triad(evaluated, budget)

    assert RecommendationTag.SAFEST in triad
    assert RecommendationTag.BALANCED in triad
    assert RecommendationTag.CHEAPEST in triad

    assert triad[RecommendationTag.SAFEST].itinerary.itinerary_id == "P1_safest"
    assert triad[RecommendationTag.BALANCED].itinerary.itinerary_id == "P3_balanced"
    assert triad[RecommendationTag.CHEAPEST].itinerary.itinerary_id == "P2_cheapest"
