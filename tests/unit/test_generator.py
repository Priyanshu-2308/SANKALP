"""Unit tests for the SeededScheduleGenerator."""

from datetime import datetime, timedelta
from sankalp_engine.generator import SeededScheduleGenerator
from sankalp_engine.models import IST, TransitMode


def test_generator_initialization() -> None:
    gen = SeededScheduleGenerator()
    places = gen.get_all_places()
    assert len(places) > 100

    ndls = gen.get_place("STN_NDLS")
    assert ndls is not None
    assert ndls.code == "NDLS"

    bom = gen.get_place_by_code("BOM")
    assert bom is not None
    assert bom.code == "BOM"


def test_search_places() -> None:
    gen = SeededScheduleGenerator()

    # Search by code
    res_code = gen.search_places("NDLS")
    assert len(res_code) >= 1
    assert res_code[0].code == "NDLS"

    # Search by city name
    res_pune = gen.search_places("Pune")
    assert len(res_pune) >= 1
    assert any("pune" in p.name.lower() or "pune" in p.city.lower() for p in res_pune)

    # Search by alias
    res_vizag = gen.search_places("Vizag")
    assert len(res_vizag) >= 1
    assert res_vizag[0].code in ("VSKP", "VTZ")


def test_generator_determinism() -> None:
    """CRITICAL TEST: Verify that querying the generator twice with identical parameters
    produces exactly identical legs, timestamps, identifiers, and fares.
    """
    gen1 = SeededScheduleGenerator(seed_salt="test-salt")
    gen2 = SeededScheduleGenerator(seed_salt="test-salt")

    t_start = datetime(2026, 10, 10, 6, 0, tzinfo=IST)
    t_end = datetime(2026, 10, 10, 23, 0, tzinfo=IST)

    legs1 = gen1.find_direct_legs("STN_PUNE", "STN_CSMT", t_start, t_end)
    legs2 = gen2.find_direct_legs("STN_PUNE", "STN_CSMT", t_start, t_end)

    assert len(legs1) > 0
    assert len(legs1) == len(legs2)

    for l1, l2 in zip(legs1, legs2):
        assert l1.leg_id == l2.leg_id
        assert l1.departure_time == l2.departure_time
        assert l1.arrival_time == l2.arrival_time
        assert l1.duration_minutes == l2.duration_minutes
        assert l1.fare_paise == l2.fare_paise
        assert l1.identifier == l2.identifier
        assert l1.is_simulated is True


def test_find_candidate_connecting_hubs() -> None:
    gen = SeededScheduleGenerator()
    # Connecting between Delhi and Chennai
    hubs = gen.find_candidate_connecting_hubs("STN_NDLS", "STN_MAS", max_hubs=8)
    assert len(hubs) > 0
    # Nagpur or Bhopal should be natural candidates
    hub_codes = [gen.get_place(hid).code for hid in hubs if gen.get_place(hid)]
    assert any(c in hub_codes for c in ["NGP", "BPL", "BZA", "GWL", "VGLJ"])


def test_minimum_connection_time() -> None:
    gen = SeededScheduleGenerator()
    train_train = gen.get_minimum_connection_time(TransitMode.TRAIN, TransitMode.TRAIN)
    train_flight = gen.get_minimum_connection_time(TransitMode.TRAIN, TransitMode.FLIGHT)
    flight_flight = gen.get_minimum_connection_time(TransitMode.FLIGHT, TransitMode.FLIGHT)

    assert train_train == 30
    assert train_flight == 120
    assert flight_flight == 60
