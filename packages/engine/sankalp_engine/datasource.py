"""Abstract transport data source protocol.

Design Principles:
- Single clean interface behind which all schedule and place lookups are performed.
- Ensures the decision engine can be tested with zero external network or database calls.
- Can be implemented by the seeded synthetic generator today or a real data adapter in the future.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from .models import Leg, Place, TransitMode


@runtime_checkable
class TransportDataSource(Protocol):
    """Protocol defining required data access methods for SANKALP."""

    def get_place(self, place_id: str) -> Optional[Place]:
        """Lookup a place by its unique ID."""
        ...

    def get_place_by_code(self, code: str) -> Optional[Place]:
        """Lookup a place by its railway or airport code (e.g. 'NDLS', 'BOM')."""
        ...

    def search_places(self, query: str, limit: int = 10) -> list[Place]:
        """Search places by substring match on name, city, code, or aliases."""
        ...

    def get_all_places(self) -> list[Place]:
        """Retrieve all bundled places."""
        ...

    def find_direct_legs(
        self,
        origin_id: str,
        destination_id: str,
        departure_after: datetime,
        departure_before: datetime,
    ) -> list[Leg]:
        """Find direct scheduled legs departing within the specified time window."""
        ...

    def find_candidate_connecting_hubs(
        self,
        origin_id: str,
        destination_id: str,
        max_hubs: int = 12,
        max_detour_ratio: float = 1.45,
    ) -> list[str]:
        """Find strategically located intermediate hubs suitable for transfers."""
        ...

    def get_minimum_connection_time(self, mode_from: TransitMode, mode_to: TransitMode) -> int:
        """Get the minimum connection time in minutes required between two modes."""
        ...
