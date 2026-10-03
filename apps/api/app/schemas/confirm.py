"""Pydantic schemas for the single-use token approval and booking mock flow."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ConfirmTokenRequest(BaseModel):
    """Request to issue a single-use token when opening the Confirm page."""
    itinerary_id: str = Field(..., description="ID of the plan selected on the Results page")


class ConfirmTokenResponse(BaseModel):
    """Single-use approval token with short TTL."""
    itinerary_id: str
    approval_token: str = Field(..., description="Cryptographically random single-use approval token")
    expires_at: str = Field(..., description="ISO-8601 expiration timestamp")
    ttl_seconds: int = Field(default=900, description="Token validity window (15 minutes)")
    security_notice: str = Field(
        default="This token can be redeemed exactly once. Any double-approval attempt will be rejected.",
        description="Security rule notice",
    )


class ApprovePlanRequest(BaseModel):
    """Request payload to approve and lock in a recovery itinerary."""
    approval_token: str = Field(..., description="Single-use token issued on Confirm page load")
    itinerary_id: str = Field(..., description="Target itinerary ID")
    origin_id: str
    destination_id: str
    total_fare_paise: int
    p_ontime: float
    itinerary: dict[str, Any] = Field(..., description="Full itinerary data for audit archiving")


class ApprovePlanResponse(BaseModel):
    """Mock approval confirmation object."""
    status: str = "APPROVED"
    trip_id: str = Field(..., description="Persistent trip tracking ID")
    itinerary_id: str
    approved_at: str
    operator_handoff_note: str = Field(
        default="In a production system, this step seamlessly hands off passenger credentials and routing to the respective transport operator portals (IRCTC / RedBus / Airline PNR). No real money was charged.",
        description="Portfolio transparency note",
    )
    data_disclaimer: str = "Simulated schedules"


class TripDetailResponse(BaseModel):
    """Full saved trip audit representation."""
    trip_id: str
    approval_token: str
    itinerary_id: str
    origin_id: str
    destination_id: str
    action: str
    total_fare_paise: int
    total_fare_inr: int
    p_ontime: float
    created_at: str
    itinerary: dict[str, Any]
    data_disclaimer: str = "Simulated schedules"
