"""Unit tests for engine domain models."""

from datetime import datetime
from sankalp_engine.models import (
    IST,
    Itinerary,
    Leg,
    Place,
    PlaceType,
    Transfer,
    TransitMode,
)


def test_place_creation() -> None:
    p = Place(
        id="STN_NDLS",
        name="New Delhi",
        code="NDLS",
        place_type=PlaceType.RAIL_STATION,
        city="New Delhi",
        state="Delhi",
        latitude=28.6429,
        longitude=77.2195,
        aliases=["Delhi", "NDLS"],
        tier=1,
    )
    d = p.to_dict()
    assert d["code"] == "NDLS"
    assert d["place_type"] == "rail_station"
    assert d["tier"] == 1


def test_leg_timezone_enforcement() -> None:
    # Naive datetimes should be automatically cast to Asia/Kolkata
    naive_dep = datetime(2026, 10, 4, 10, 0)
    naive_arr = datetime(2026, 10, 4, 14, 0)
    leg = Leg(
        leg_id="leg_1",
        origin_id="STN_PUNE",
        destination_id="STN_CSMT",
        mode=TransitMode.TRAIN,
        departure_time=naive_dep,
        arrival_time=naive_arr,
        duration_minutes=240,
        distance_km=150.0,
        fare_paise=120000,
        operator_name="Indian Railways",
        identifier="12128",
    )
    assert leg.departure_time.tzinfo == IST
    assert leg.arrival_time.tzinfo == IST
    assert leg.fare_paise == 120000
    assert leg.is_simulated is True


def test_itinerary_properties() -> None:
    t1 = datetime(2026, 10, 4, 8, 0, tzinfo=IST)
    t2 = datetime(2026, 10, 4, 11, 0, tzinfo=IST)
    t3 = datetime(2026, 10, 4, 12, 0, tzinfo=IST)
    t4 = datetime(2026, 10, 4, 14, 0, tzinfo=IST)

    leg1 = Leg(
        leg_id="l1",
        origin_id="STN_A",
        destination_id="STN_B",
        mode=TransitMode.TRAIN,
        departure_time=t1,
        arrival_time=t2,
        duration_minutes=180,
        distance_km=180.0,
        fare_paise=25000,
        operator_name="IR",
        identifier="T1",
    )
    leg2 = Leg(
        leg_id="l2",
        origin_id="STN_B",
        destination_id="STN_C",
        mode=TransitMode.BUS,
        departure_time=t3,
        arrival_time=t4,
        duration_minutes=120,
        distance_km=100.0,
        fare_paise=15000,
        operator_name="BusOp",
        identifier="B1",
    )
    transfer = Transfer(
        place_id="STN_B",
        arrival_time=t2,
        departure_time=t3,
        wait_minutes=60,
        min_connection_minutes=40,
        mode_from=TransitMode.TRAIN,
        mode_to=TransitMode.BUS,
        is_intermodal=True,
    )

    itin = Itinerary(
        itinerary_id="itin_1",
        legs=[leg1, leg2],
        transfers=[transfer],
        total_duration_minutes=360,
        total_fare_paise=40000,
        departure_time=t1,
        arrival_time=t4,
    )

    assert itin.num_transfers == 1
    assert itin.is_multimodal is True
    assert itin.total_fare_paise == 40000
