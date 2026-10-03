"""FastAPI endpoints for single-use approval tokens, booking confirmation, and trip retrieval."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sankalp_engine.models import IST

from ..database import Database
from ..dependencies import get_database
from ..schemas.confirm import (
    ApprovePlanRequest,
    ApprovePlanResponse,
    ConfirmTokenRequest,
    ConfirmTokenResponse,
    TripDetailResponse,
)

router = APIRouter(prefix="/v1", tags=["Approval & Trips"])


@router.post("/recover/confirm-token", response_model=ConfirmTokenResponse)
def issue_confirm_token(
    req: ConfirmTokenRequest,
    db: Database = Depends(get_database),
) -> ConfirmTokenResponse:
    """Issue a single-use, 15-minute cryptographically signed approval token."""
    token = db.create_approval_token(itinerary_id=req.itinerary_id, ttl_minutes=15)
    expires_at = (datetime.now(IST) + timedelta(minutes=15)).isoformat()

    return ConfirmTokenResponse(
        itinerary_id=req.itinerary_id,
        approval_token=token,
        expires_at=expires_at,
        ttl_seconds=900,
    )


@router.post("/recover/approve", response_model=ApprovePlanResponse)
def approve_recovery_plan(
    req: ApprovePlanRequest,
    db: Database = Depends(get_database),
) -> ApprovePlanResponse:
    """Atomically redeem a single-use token and approve the recovery journey."""
    is_redeemed = db.verify_and_redeem_token(
        token=req.approval_token,
        itinerary_id=req.itinerary_id,
    )

    if not is_redeemed:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "Approval token is invalid, expired, or has already been used. "
                "Each approval token can only be redeemed once."
            ),
        )

    trip_id = db.record_trip_approval(
        approval_token=req.approval_token,
        itinerary_id=req.itinerary_id,
        origin_id=req.origin_id,
        destination_id=req.destination_id,
        total_fare_paise=req.total_fare_paise,
        p_ontime=req.p_ontime,
        itinerary_data=req.itinerary,
        action="APPROVED",
    )

    now_iso = datetime.now(IST).isoformat()
    return ApprovePlanResponse(
        status="APPROVED",
        trip_id=trip_id,
        itinerary_id=req.itinerary_id,
        approved_at=now_iso,
    )


@router.get("/trips/{trip_id}", response_model=TripDetailResponse)
def get_trip_details(
    trip_id: str,
    db: Database = Depends(get_database),
) -> TripDetailResponse:
    """Retrieve full details of an approved recovery trip."""
    trip = db.get_trip(trip_id)
    if not trip:
        raise HTTPException(
            status_code=404,
            detail=f"Trip ID '{trip_id}' not found in audit database.",
        )

    return TripDetailResponse(
        trip_id=trip["trip_id"],
        approval_token=trip["approval_token"],
        itinerary_id=trip["itinerary_id"],
        origin_id=trip["origin_id"],
        destination_id=trip["destination_id"],
        action=trip["action"],
        total_fare_paise=trip["total_fare_paise"],
        total_fare_inr=trip["total_fare_paise"] // 100,
        p_ontime=trip["p_ontime"],
        created_at=trip["created_at"],
        itinerary=trip["itinerary"],
    )
