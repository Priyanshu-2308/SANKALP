"""Unit tests for Monte Carlo transit delay simulation and Wilson intervals."""

from datetime import datetime, timedelta
import numpy as np
from sankalp_engine.models import IST, Itinerary, Leg, Transfer, TransitMode
from sankalp_engine.simulation import simulate_itinerary_delays
from sankalp_engine.statistics import wilson_score_interval


def test_wilson_score_interval_properties() -> None:
    # 9500 successes out of 10000 trials (95%)
    ci_low, ci_high = wilson_score_interval(9500, 10000)
    assert 0.94 <= ci_low <= 0.95
    assert 0.95 <= ci_high <= 0.96
    assert ci_low < 0.95 < ci_high

    # Edge cases: 0 successes, 10000 successes
    low_0, high_0 = wilson_score_interval(0, 10000)
    assert low_0 == 0.0
    assert high_0 < 0.001

    low_10k, high_10k = wilson_score_interval(10000, 10000)
    assert low_10k > 0.999
    assert high_10k == 1.0


def test_single_leg_simulation_sensitivity() -> None:
    dep = datetime(2026, 10, 5, 8, 0, tzinfo=IST)
    arr = datetime(2026, 10, 5, 12, 0, tzinfo=IST)  # 4 hours running

    leg = Leg(
        leg_id="l1", origin_id="A", destination_id="B",
        mode=TransitMode.TRAIN, departure_time=dep, arrival_time=arr,
        duration_minutes=240, distance_km=250.0, fare_paise=35000,
        operator_name="IR", identifier="12001",
    )
    itin = Itinerary(
        itinerary_id="it1", legs=[leg], transfers=[],
        total_duration_minutes=240, total_fare_paise=35000,
        departure_time=dep, arrival_time=arr,
    )

    # Generous deadline: 2 hours after scheduled arrival -> high P(on-time)
    deadline_generous = arr + timedelta(hours=2)
    met_generous = simulate_itinerary_delays(itin, deadline_generous, trials_count=5000, seed=123)
    assert met_generous.p_ontime > 0.90
    assert met_generous.missed_connection_rate == 0.0

    # Tight deadline: 5 minutes after scheduled arrival -> lower P(on-time)
    deadline_tight = arr + timedelta(minutes=5)
    met_tight = simulate_itinerary_delays(itin, deadline_tight, trials_count=5000, seed=123)
    assert met_tight.p_ontime < met_generous.p_ontime


def test_transfer_cascading_delay_misses_connection() -> None:
    t1 = datetime(2026, 10, 5, 8, 0, tzinfo=IST)
    t2 = datetime(2026, 10, 5, 11, 0, tzinfo=IST)  # Leg 1 arrives 11:00
    # Tight transfer: Departs at 11:35 (only 35 mins wait, minimum connection is 30 mins)
    t3 = datetime(2026, 10, 5, 11, 35, tzinfo=IST)
    t4 = datetime(2026, 10, 5, 14, 0, tzinfo=IST)

    leg1 = Leg(
        leg_id="l1", origin_id="A", destination_id="B",
        mode=TransitMode.TRAIN, departure_time=t1, arrival_time=t2,
        duration_minutes=180, distance_km=200.0, fare_paise=25000,
        operator_name="IR", identifier="T1",
    )
    leg2 = Leg(
        leg_id="l2", origin_id="B", destination_id="C",
        mode=TransitMode.TRAIN, departure_time=t3, arrival_time=t4,
        duration_minutes=145, distance_km=150.0, fare_paise=20000,
        operator_name="IR", identifier="T2",
    )
    transfer = Transfer(
        place_id="B", arrival_time=t2, departure_time=t3,
        wait_minutes=35, min_connection_minutes=30,
        mode_from=TransitMode.TRAIN, mode_to=TransitMode.TRAIN,
    )
    itin = Itinerary(
        itinerary_id="it_conn", legs=[leg1, leg2], transfers=[transfer],
        total_duration_minutes=360, total_fare_paise=45000,
        departure_time=t1, arrival_time=t4,
    )

    # Any delay > 5 mins on Leg 1 will breach the 30m MCT and cause a missed connection!
    deadline = t4 + timedelta(hours=3)
    metrics = simulate_itinerary_delays(itin, deadline, trials_count=5000, seed=42)
    # The missed connection rate should be significant due to right-skewed train delays
    assert metrics.missed_connection_rate > 0.40
    assert metrics.p_ontime <= (1.0 - metrics.missed_connection_rate) + 1e-5


def test_injected_delay_simulation() -> None:
    dep = datetime(2026, 10, 5, 8, 0, tzinfo=IST)
    arr = datetime(2026, 10, 5, 12, 0, tzinfo=IST)
    leg = Leg(
        leg_id="l1", origin_id="A", destination_id="B",
        mode=TransitMode.TRAIN, departure_time=dep, arrival_time=arr,
        duration_minutes=240, distance_km=250.0, fare_paise=35000,
        operator_name="IR", identifier="12001",
    )
    itin = Itinerary(
        itinerary_id="it1", legs=[leg], transfers=[],
        total_duration_minutes=240, total_fare_paise=35000,
        departure_time=dep, arrival_time=arr,
    )
    # Deadline is 30 mins after scheduled arrival
    deadline = arr + timedelta(minutes=30)

    # Injecting a 60 min delay ensures 100% of trials fail to meet the 30 min deadline
    met_injected = simulate_itinerary_delays(
        itin, deadline, trials_count=1000, seed=42, injected_delays={0: 60.0}
    )
    assert met_injected.p_ontime == 0.0
