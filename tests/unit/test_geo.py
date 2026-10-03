"""Unit tests for geographic calculations."""

from sankalp_engine.geo import detour_ratio, haversine_distance_km, place_distance_km
from sankalp_engine.models import Place, PlaceType


def test_haversine_distance_accuracy() -> None:
    # New Delhi (28.6429, 77.2195) to Mumbai CSMT (18.9402, 72.8356)
    # Great circle distance is ~1167 km
    dist = haversine_distance_km(28.6429, 77.2195, 18.9402, 72.8356)
    assert 1140.0 <= dist <= 1175.0

    # Pune (18.5284, 73.8743) to Mumbai CSMT (18.9402, 72.8356)
    # Great circle distance is ~115 - 125 km
    pune_bom = haversine_distance_km(18.5284, 73.8743, 18.9402, 72.8356)
    assert 115.0 <= pune_bom <= 125.0


def test_detour_ratio() -> None:
    delhi = Place(
        id="STN_NDLS", name="Delhi", code="NDLS", place_type=PlaceType.RAIL_STATION,
        city="Delhi", state="Delhi", latitude=28.6429, longitude=77.2195
    )
    bhopal = Place(
        id="STN_BPL", name="Bhopal", code="BPL", place_type=PlaceType.RAIL_STATION,
        city="Bhopal", state="Madhya Pradesh", latitude=23.2684, longitude=77.4126
    )
    nagpur = Place(
        id="STN_NGP", name="Nagpur", code="NGP", place_type=PlaceType.RAIL_STATION,
        city="Nagpur", state="Maharashtra", latitude=21.1524, longitude=79.0882
    )

    # Bhopal is almost directly on the Delhi -> Nagpur axis
    ratio = detour_ratio(delhi, bhopal, nagpur)
    assert 1.0 <= ratio <= 1.15  # Very direct detour
