"""Unit tests for utility scoring and the hard budget invariant."""

from datetime import datetime
from sankalp_engine.models import (
    IST,
    Itinerary,
    Leg,
    SimulationMetrics,
    TransitMode,
)
from sankalp_engine.scoring import (
    enforce_budget_invariant,
    score_buffer_margin,
    score_cost_efficiency,
    score_itinerary,
    score_itinerary_comfort,
    score_ontime_probability,
)


def create_dummy_itinerary(fare_paise: int, mode: TransitMode = TransitMode.TRAIN) -> Itinerary:
    t1 = datetime(2026, 10, 5, 8, 0, tzinfo=IST)
    t2 = datetime(2026, 10, 5, 12, 0, tzinfo=IST)
    leg = Leg(
        leg_id="l1", origin_id="A", destination_id="B",
        mode=mode, departure_time=t1, arrival_time=t2,
        duration_minutes=240, distance_km=250.0, fare_paise=fare_paise,
        operator_name="Op", identifier="ID1",
    )
    return Itinerary(
        itinerary_id="it1", legs=[leg], transfers=[],
        total_duration_minutes=240, total_fare_paise=fare_paise,
        departure_time=t1, arrival_time=t2,
    )


def test_score_components() -> None:
    # Probability: [0, 1]
    assert score_ontime_probability(0.95) == 0.95
    assert score_ontime_probability(1.5) == 1.0
    assert score_ontime_probability(-0.2) == 0.0

    # Buffer: full score at target 120 mins
    assert score_buffer_margin(120, 120) == 1.0
    assert score_buffer_margin(60, 120) == 0.5
    assert score_buffer_margin(-10, 120) == 0.0

    # Cost: fare <= budget
    assert score_cost_efficiency(0, 100000) == 1.0  # Free
    assert score_cost_efficiency(100000, 100000) == 0.5  # Full budget
    assert score_cost_efficiency(150000, 100000) < 0.5  # Over budget


def test_hard_budget_invariant() -> None:
    """CRITICAL TEST: An over-budget plan can NEVER outrank an affordable high-confidence plan."""
    budget_paise = 200000  # ₹2,000

    # Affordable Plan: ₹1,500 (under budget), P(on-time) = 85%, solid buffer
    itin_affordable = create_dummy_itinerary(fare_paise=150000, mode=TransitMode.TRAIN)
    metrics_affordable = SimulationMetrics(
        p_ontime=0.85, p_ontime_ci_low=0.84, p_ontime_ci_high=0.86,
        trials_count=10000, median_delay_minutes=12.0, p90_delay_minutes=25.0,
        missed_connection_rate=0.0,
    )
    score_affordable = score_itinerary(
        itinerary=itin_affordable,
        metrics=metrics_affordable,
        buffer_minutes=60,
        budget_paise=budget_paise,
    )

    # Over-budget Plan: ₹5,000 (exceeds ₹2,000 budget), but 99% P(on-time) and luxury flight
    itin_overbudget = create_dummy_itinerary(fare_paise=500000, mode=TransitMode.FLIGHT)
    metrics_overbudget = SimulationMetrics(
        p_ontime=0.99, p_ontime_ci_low=0.985, p_ontime_ci_high=0.995,
        trials_count=10000, median_delay_minutes=5.0, p90_delay_minutes=10.0,
        missed_connection_rate=0.0,
    )
    score_overbudget = score_itinerary(
        itinerary=itin_overbudget,
        metrics=metrics_overbudget,
        buffer_minutes=120,
        budget_paise=budget_paise,
    )

    # INVARIANT CHECK: The affordable plan MUST strictly outrank the over-budget plan!
    assert score_affordable > score_overbudget
    # Over budget plan score must be capped below 0.35
    assert score_overbudget <= 0.35
    assert score_affordable >= 0.40
