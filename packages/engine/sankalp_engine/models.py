"""Domain models for the SANKALP journey-recovery decision engine.

Design Principles:
- Pure Python dataclasses with strict type annotations.
- Timezone-aware datetimes (Asia/Kolkata).
- Money represented as integer paise (1 INR = 100 paise) to prevent floating-point rounding bugs.
- Clear separation between raw schedules, graph itineraries, Monte Carlo simulation metrics, and ranked results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
# Standard Indian Standard Time timezone (UTC+05:30)
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")


class TransitMode(str, Enum):
    """Supported multi-modal transit options."""
    TRAIN = "TRAIN"
    BUS = "BUS"
    FLIGHT = "FLIGHT"


class PlaceType(str, Enum):
    """Categorization of transit nodes in India."""
    RAIL_STATION = "rail_station"
    AIRPORT = "airport"
    BUS_TERMINAL = "bus_terminal"


class RecommendationTag(str, Enum):
    """The triad of recommendations presented to the traveller."""
    SAFEST = "SAFEST"
    BALANCED = "BALANCED"
    CHEAPEST = "CHEAPEST"
    OTHER = "OTHER"


class ExclusionCode(str, Enum):
    """Structured classification for why candidate routes were pruned."""
    DEADLINE_BREACH = "EXCLUDED_DEADLINE_BREACH"
    BUDGET_EXCEEDED = "EXCLUDED_BUDGET_EXCEEDED"
    CONNECTION_RISK = "EXCLUDED_CONNECTION_RISK"
    PARETO_DOMINATED = "EXCLUDED_PARETO_DOMINATED"
    NO_RELIABLE_ROUTE = "EXCLUDED_NO_RELIABLE_ROUTE"


@dataclass(frozen=True)
class Place:
    """A physical transit node (railway station, airport, or bus terminal)."""
    id: str
    name: str
    code: str
    place_type: PlaceType
    city: str
    state: str
    latitude: float
    longitude: float
    aliases: list[str] = field(default_factory=list)
    tier: int = 2

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["place_type"] = self.place_type.value
        return data


@dataclass(frozen=True)
class Leg:
    """A direct, single-mode transit segment between two places."""
    leg_id: str
    origin_id: str
    destination_id: str
    mode: TransitMode
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    distance_km: float
    fare_paise: int
    operator_name: str
    identifier: str  # e.g. "Express 12001", "AI-804", "Shivneri AC"
    is_simulated: bool = True

    def __post_init__(self) -> None:
        # Enforce timezone awareness
        if self.departure_time.tzinfo is None:
            object.__setattr__(self, "departure_time", self.departure_time.replace(tzinfo=IST))
        if self.arrival_time.tzinfo is None:
            object.__setattr__(self, "arrival_time", self.arrival_time.replace(tzinfo=IST))

    def to_dict(self) -> dict[str, Any]:
        return {
            "leg_id": self.leg_id,
            "origin_id": self.origin_id,
            "destination_id": self.destination_id,
            "mode": self.mode.value,
            "departure_time": self.departure_time.isoformat(),
            "arrival_time": self.arrival_time.isoformat(),
            "duration_minutes": self.duration_minutes,
            "distance_km": round(self.distance_km, 1),
            "fare_paise": self.fare_paise,
            "operator_name": self.operator_name,
            "identifier": self.identifier,
            "is_simulated": self.is_simulated,
        }


@dataclass(frozen=True)
class Transfer:
    """A connection node between two consecutive legs."""
    place_id: str
    arrival_time: datetime
    departure_time: datetime
    wait_minutes: int
    min_connection_minutes: int
    mode_from: TransitMode
    mode_to: TransitMode
    is_intermodal: bool = False

    def __post_init__(self) -> None:
        if self.arrival_time.tzinfo is None:
            object.__setattr__(self, "arrival_time", self.arrival_time.replace(tzinfo=IST))
        if self.departure_time.tzinfo is None:
            object.__setattr__(self, "departure_time", self.departure_time.replace(tzinfo=IST))

    def to_dict(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "arrival_time": self.arrival_time.isoformat(),
            "departure_time": self.departure_time.isoformat(),
            "wait_minutes": self.wait_minutes,
            "min_connection_minutes": self.min_connection_minutes,
            "mode_from": self.mode_from.value,
            "mode_to": self.mode_to.value,
            "is_intermodal": self.is_intermodal,
        }


@dataclass(frozen=True)
class Itinerary:
    """A complete journey path from origin to destination (direct or with transfers)."""
    itinerary_id: str
    legs: list[Leg]
    transfers: list[Transfer]
    total_duration_minutes: int
    total_fare_paise: int
    departure_time: datetime
    arrival_time: datetime

    @property
    def num_transfers(self) -> int:
        return len(self.transfers)

    @property
    def is_multimodal(self) -> bool:
        unique_modes = {leg.mode for leg in self.legs}
        return len(unique_modes) > 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "itinerary_id": self.itinerary_id,
            "legs": [leg.to_dict() for leg in self.legs],
            "transfers": [transfer.to_dict() for transfer in self.transfers],
            "num_transfers": self.num_transfers,
            "is_multimodal": self.is_multimodal,
            "total_duration_minutes": self.total_duration_minutes,
            "total_fare_paise": self.total_fare_paise,
            "departure_time": self.departure_time.isoformat(),
            "arrival_time": self.arrival_time.isoformat(),
        }


@dataclass(frozen=True)
class SimulationMetrics:
    """Stochastic results from 10,000 Monte Carlo trials."""
    p_ontime: float  # Estimated probability [0.0, 1.0] of arriving <= deadline
    p_ontime_ci_low: float  # Wilson 95% confidence interval lower bound
    p_ontime_ci_high: float  # Wilson 95% confidence interval upper bound
    trials_count: int
    median_delay_minutes: float
    p90_delay_minutes: float
    missed_connection_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "p_ontime": round(self.p_ontime, 4),
            "p_ontime_ci_95": [round(self.p_ontime_ci_low, 4), round(self.p_ontime_ci_high, 4)],
            "trials_count": self.trials_count,
            "median_delay_minutes": round(self.median_delay_minutes, 1),
            "p90_delay_minutes": round(self.p90_delay_minutes, 1),
            "missed_connection_rate": round(self.missed_connection_rate, 4),
        }


@dataclass(frozen=True)
class ScoredItinerary:
    """An evaluated itinerary with simulation metrics, utility score, and human reason."""
    itinerary: Itinerary
    metrics: SimulationMetrics
    buffer_minutes: int  # Minutes between scheduled arrival and deadline
    utility_score: float  # Normalized composite utility score [0.0, 1.0]
    tag: RecommendationTag
    plain_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.itinerary.to_dict(),
            "metrics": self.metrics.to_dict(),
            "buffer_minutes": self.buffer_minutes,
            "utility_score": round(self.utility_score, 4),
            "tag": self.tag.value,
            "plain_reason": self.plain_reason,
        }


@dataclass(frozen=True)
class ExclusionRationale:
    """A human-readable reason why a candidate itinerary was pruned."""
    itinerary_summary: str
    code: ExclusionCode
    reason_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "itinerary_summary": self.itinerary_summary,
            "code": self.code.value,
            "reason_text": self.reason_text,
        }
