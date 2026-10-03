"""Unit tests for time-dependent graph search."""

from datetime import datetime, timedelta
from sankalp_engine.generator import SeededScheduleGenerator
from sankalp_engine.graph_search import find_candidate_itineraries
from sankalp_engine.models import IST


def test_graph_search_direct_and_transfers() -> None:
    gen = SeededScheduleGenerator()
    start_time = datetime(2026, 10, 6, 6, 0, tzinfo=IST)
    deadline = start_time + timedelta(hours=14)  # 8:00 PM

    candidates, pruned = find_candidate_itineraries(
        origin_id="STN_PUNE",
        destination_id="STN_CSMT",
        departure_after=start_time,
        deadline=deadline,
        data_source=gen,
        max_transfers=1,
    )

    # Should find multiple direct options between Pune and Mumbai
    assert len(candidates) > 0
    for itin in candidates:
        assert itin.arrival_time <= deadline
        assert itin.departure_time >= start_time
        assert itin.total_duration_minutes > 0


def test_graph_search_mct_enforcement() -> None:
    gen = SeededScheduleGenerator()
    start_time = datetime(2026, 10, 6, 8, 0, tzinfo=IST)
    deadline = start_time + timedelta(hours=24)

    candidates, _ = find_candidate_itineraries(
        origin_id="STN_NDLS",
        destination_id="STN_MAS",
        departure_after=start_time,
        deadline=deadline,
        data_source=gen,
        max_transfers=1,
    )

    # All transfer points must strictly respect Minimum Connection Time
    for itin in candidates:
        for transfer in itin.transfers:
            assert transfer.wait_minutes >= transfer.min_connection_minutes
