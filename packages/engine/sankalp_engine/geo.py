"""Geographic calculations using the Haversine formula.

Design Principles:
- Pure mathematical functions with no external dependencies.
- Great-circle distance calculations for realistic transit routes.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Place

# Earth's mean radius in kilometers
EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic coordinates in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_KM * c


def place_distance_km(p1: Place, p2: Place) -> float:
    """Calculate distance in km between two Place objects."""
    return haversine_distance_km(p1.latitude, p1.longitude, p2.latitude, p2.longitude)


def detour_ratio(origin: Place, hub: Place, destination: Place) -> float:
    """Calculate the detour ratio of routing via an intermediate hub.
    
    A direct line has detour ratio 1.0. A reasonable detour for transport in India
    is typically <= 1.45 (e.g. connecting via Nagpur, Bhopal, or Delhi).
    """
    direct_dist = place_distance_km(origin, destination)
    if direct_dist <= 1.0:
        return 1.0
    via_dist = place_distance_km(origin, hub) + place_distance_km(hub, destination)
    return via_dist / direct_dist
