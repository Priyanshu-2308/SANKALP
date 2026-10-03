"""Pydantic schemas for delay injection and on-demand re-planning."""

from typing import Any, Optional
from pydantic import BaseModel, Field

from .search import ScoredItineraryResponse, SimulationMetricsResponse


class SimulateDelayRequest(BaseModel):
    """Payload to inject an artificial delay on a trip leg."""
    trip_id: str = Field(..., description="The approved trip identifier")
    leg_index: int = Field(default=0, ge=0, description="0-indexed leg number to inject delay on")
    injected_delay_minutes: float = Field(..., gt=0.0, description="Delay duration in minutes (e.g. 60.0)")


class SimulateDelayResponse(BaseModel):
    """Response detailing cascade degradation and on-demand re-planned alternative."""
    trip_id: str
    leg_index: int
    injected_delay_minutes: float
    original_p_ontime: float
    recalculated_metrics: SimulationMetricsResponse
    is_deadline_at_risk: bool = Field(
        ...,
        description="True if on-time probability drops below 50% or a connecting transfer is broken",
    )
    risk_explanation: str
    replacement_plan: Optional[ScoredItineraryResponse] = Field(
        default=None,
        description="On-demand replacement itinerary computed from current delayed location/time if deadline is at risk",
    )
    data_disclaimer: str = "Simulated schedules"
