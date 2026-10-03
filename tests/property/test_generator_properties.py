"""Property-based tests for generator invariants using Hypothesis."""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st
from sankalp_engine.generator import SeededScheduleGenerator
from sankalp_engine.models import IST

gen = SeededScheduleGenerator()
places = gen.get_all_places()
place_ids = [p.id for p in places if p.tier <= 2]


@given(
    orig_idx=st.integers(min_value=0, max_value=len(place_ids) - 1),
    dest_idx=st.integers(min_value=0, max_value=len(place_ids) - 1),
    start_hour=st.integers(min_value=0, max_value=12),
    window_hours=st.integers(min_value=6, max_value=24),
)
def test_generator_invariants(orig_idx: int, dest_idx: int, start_hour: int, window_hours: int) -> None:
    if orig_idx == dest_idx:
        return

    orig_id = place_ids[orig_idx]
    dest_id = place_ids[dest_idx]

    base_time = datetime(2026, 10, 5, start_hour, 0, tzinfo=IST)
    end_time = base_time + timedelta(hours=window_hours)

    legs = gen.find_direct_legs(orig_id, dest_id, base_time, end_time)

    for leg in legs:
        # Invariant 1: Departure precedes arrival
        assert leg.departure_time < leg.arrival_time
        # Invariant 2: Positive duration
        assert leg.duration_minutes > 0
        # Invariant 3: Positive integer paise fare
        assert isinstance(leg.fare_paise, int)
        assert leg.fare_paise > 0
        # Invariant 4: Departure is within the requested window
        assert base_time <= leg.departure_time <= end_time
        # Invariant 5: Timezone is Asia/Kolkata
        assert leg.departure_time.tzinfo == IST
        assert leg.arrival_time.tzinfo == IST
        # Invariant 6: Labeled as simulated schedule
        assert leg.is_simulated is True
