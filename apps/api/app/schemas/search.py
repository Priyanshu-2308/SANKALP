"""Pydantic schemas for journey recovery search endpoints."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class RecoverySearchRequest(BaseModel):
    """Request payload for finding multi-modal recovery routes."""
    origin_id: str = Field(..., description="Departure place ID or station code")
    destination_id: str = Field(..., description="Destination place ID or station code")
    deadline: datetime = Field(..., description="Target arrival deadline (ISO-8601, preferably Asia/Kolkata)")
    budget_paise: Optional[int] = Field(None, description="Maximum budget in paise (e.g. 250000 = ₹2,500)")
    budget_inr: Optional[int] = Field(None, description="Maximum budget in Indian Rupees (e.g. 2500)")
    departure_after: Optional[datetime] = Field(None, description="Earliest allowed departure time")

    @model_validator(mode="after")
    def resolve_budget(self) -> "RecoverySearchRequest":
        # Synchronize budget_paise and budget_inr
        if self.budget_paise is None and self.budget_inr is not None:
            self.budget_paise = self.budget_inr * 100
        elif self.budget_paise is not None and self.budget_inr is None:
            self.budget_inr = self.budget_paise // 100
        elif self.budget_paise is None and self.budget_inr is None:
            # Default reasonable budget: ₹5,000 (500,000 paise)
            self.budget_paise = 500000
            self.budget_inr = 5000
        return self


class LegResponse(BaseModel):
    leg_id: str
    origin_id: str
    destination_id: str
    mode: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    distance_km: float
    fare_paise: int
    fare_inr: int
    operator_name: str
    identifier: str
    is_simulated: bool = True


class TransferResponse(BaseModel):
    place_id: str
    arrival_time: str
    departure_time: str
    wait_minutes: int
    min_connection_minutes: int
    mode_from: str
    mode_to: str
    is_intermodal: bool


class SimulationMetricsResponse(BaseModel):
    p_ontime: float = Field(..., description="Estimated on-time arrival probability [0.0, 1.0]")
    p_ontime_ci_95: list[float] = Field(..., description="Wilson 95% Confidence Interval [low, high]")
    trials_count: int = Field(default=10000, description="Monte Carlo simulation iterations")
    median_delay_minutes: float
    p90_delay_minutes: float
    missed_connection_rate: float


class ScoredItineraryResponse(BaseModel):
    itinerary_id: str
    tag: str = Field(..., description="SAFEST, BALANCED, or CHEAPEST")
    plain_reason: str = Field(..., description="Plain-language justification for why this plan was chosen")
    total_duration_minutes: int
    total_fare_paise: int
    total_fare_inr: int
    departure_time: str
    arrival_time: str
    num_transfers: int
    is_multimodal: bool
    buffer_minutes: int
    utility_score: float
    legs: list[LegResponse]
    transfers: list[TransferResponse]
    metrics: SimulationMetricsResponse


class ExclusionRationaleResponse(BaseModel):
    itinerary_summary: str
    code: str
    reason_text: str


class RecoverySearchResponse(BaseModel):
    search_id: str
    origin: dict[str, Any]
    destination: dict[str, Any]
    deadline: str
    budget_paise: int
    budget_inr: int
    total_candidates_searched: int
    execution_time_ms: float
    data_disclaimer: str = "Simulated schedules"
    recommendations: dict[str, ScoredItineraryResponse]
    pruned_candidates: list[ExclusionRationaleResponse]
