"""
Data models for SANKALP Intelligent Journey Recovery Agent.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple

class TransitMode(str, Enum):
    RAIL = "RAIL"
    FLIGHT = "FLIGHT"
    BUS = "BUS"
    METRO = "METRO"
    CAB = "CAB"

class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    RAC = "RAC"
    WAITLIST = "WAITLIST"
    AVAILABLE = "AVAILABLE"
    REGRET = "REGRET"

class QuotaType(str, Enum):
    GENERAL = "GENERAL (GN)"
    CURRENT_BOOKING = "CURRENT BOOKING (CB)"
    TATKAL = "TATKAL (TQ)"
    PREMIUM_TATKAL = "PREMIUM TATKAL (PT)"
    CHART_VACANCY = "CHART VACANCY"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class LastMileTransit:
    mode: TransitMode
    carrier_name: str
    from_hub: str
    to_venue: str
    duration_minutes: int
    fare: float
    traffic_variance_mins: int = 0
    fixed_rail_guarantee: bool = True

@dataclass
class StationInfo:
    code: str
    name: str
    city: str
    state: str
    zone: str
    station_type: str = "RAIL" # "RAIL", "BUS", "AIRPORT"
    lat: float = 0.0
    lon: float = 0.0

@dataclass
class UserConstraints:
    origin: str
    destination: str
    exam_reporting_time: datetime
    hard_arrival_deadline: datetime
    budget_max: float
    exam_venue_area: str = "Central Hub"
    student_discount_eligible: bool = True
    fatigue_sensitivity: float = 0.5 # 0.0 (any) to 1.0 (needs full sleep)
    max_transfers: int = 1
    safe_buffer_minutes: int = 120

@dataclass
class JourneyLeg:
    leg_id: str
    mode: TransitMode
    carrier_id: str          # e.g., "12650" or "6E-432" or "CB-401"
    carrier_name: str        # e.g., "Karnataka Sampark Kranti Express"
    from_station: str
    to_station: str
    departure_time: datetime
    arrival_time: datetime
    fare: float
    travel_class: str        # "3A", "SL", "CC", "ECONOMY", "AC_SEATER", "2S"
    status: BookingStatus
    available_seats: int
    historical_punctuality: float # 0.0 to 1.0
    quota: QuotaType = QuotaType.GENERAL
    mean_delay_mins: float = 12.0
    delay_std_mins: float = 18.0

    @property
    def duration_minutes(self) -> int:
        return int((self.arrival_time - self.departure_time).total_seconds() / 60)

@dataclass
class Itinerary:
    itinerary_id: str
    name: str
    category: str # "SAFE", "BALANCED", "BUDGET"
    legs: List[JourneyLeg] = field(default_factory=list)
    total_fare: float = 0.0
    total_duration_minutes: int = 0
    final_arrival_time: Optional[datetime] = None
    arrival_buffer_minutes: int = 0
    num_transfers: int = 0
    utility_score: float = 0.0
    disruption_risk: float = 0.0
    transfer_buffers: List[int] = field(default_factory=list)
    monte_carlo_punctuality: float = 0.0
    confidence_interval_95: Tuple[float, float] = (0.0, 0.0)
    last_mile: Optional[LastMileTransit] = None
    venue_arrival_time: Optional[datetime] = None
    venue_buffer_minutes: int = 0
    is_budget_exceeded: bool = False

    def calculate_totals(self, exam_deadline: datetime, venue_buffer_mins: int = 60):
        self.total_fare = sum(leg.fare for leg in self.legs)
        if self.last_mile:
            self.total_fare += self.last_mile.fare
        if self.legs:
            start = self.legs[0].departure_time
            end = self.legs[-1].arrival_time
            self.final_arrival_time = end
            self.total_duration_minutes = int((end - start).total_seconds() / 60)
            self.arrival_buffer_minutes = int((exam_deadline - end).total_seconds() / 60)
            
            # Venue arrival accounting for last mile
            last_mile_mins = self.last_mile.duration_minutes if self.last_mile else venue_buffer_mins
            self.venue_arrival_time = end + timedelta(minutes=last_mile_mins)
            self.venue_buffer_minutes = int((exam_deadline - self.venue_arrival_time).total_seconds() / 60)

            self.num_transfers = max(0, len(self.legs) - 1)
            self.transfer_buffers = []
            for i in range(len(self.legs) - 1):
                buffer_mins = int((self.legs[i+1].departure_time - self.legs[i].arrival_time).total_seconds() / 60)
                self.transfer_buffers.append(buffer_mins)

@dataclass
class BeliefState:
    user_pnr: str
    cancelled_train: str
    current_location: str
    target_location: str
    exam_time: datetime
    budget: float
    disruption_verified: bool = False
    tdr_filed: bool = False
    refund_amount: float = 0.0
    active_itinerary: Optional[Itinerary] = None
    booked_pnr: Optional[str] = None
    current_leg_index: int = 0
    in_transit_delay_minutes: int = 0
    is_recovering: bool = False
    last_mile_engaged: bool = False
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    reasoning_traces: List[Dict[str, Any]] = field(default_factory=list)
