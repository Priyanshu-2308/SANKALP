"""FastAPI endpoint for interactive delay simulation and on-demand journey re-planning."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sankalp_engine.datasource import TransportDataSource
from sankalp_engine.engine import find_journey_recovery
from sankalp_engine.models import (
    IST,
    Itinerary,
    Leg,
    RecommendationTag,
    Transfer,
    TransitMode,
)
from sankalp_engine.simulation import simulate_itinerary_delays

from ..database import Database
from ..dependencies import get_data_source, get_database
from ..schemas.search import (
    LegResponse,
    ScoredItineraryResponse,
    SimulationMetricsResponse,
    TransferResponse,
)
from ..schemas.simulate import SimulateDelayRequest, SimulateDelayResponse

router = APIRouter(prefix="/v1/trip", tags=["Trip Monitoring & Simulation"])


def parse_itinerary_from_dict(d: dict) -> Itinerary:
    """Reconstruct an Itinerary domain model from dictionary/JSON data."""
    legs = [
        Leg(
            leg_id=l["leg_id"],
            origin_id=l["origin_id"],
            destination_id=l["destination_id"],
            mode=TransitMode(l["mode"]),
            departure_time=datetime.fromisoformat(l["departure_time"]),
            arrival_time=datetime.fromisoformat(l["arrival_time"]),
            duration_minutes=int(l["duration_minutes"]),
            distance_km=float(l["distance_km"]),
            fare_paise=int(l["fare_paise"]),
            operator_name=l["operator_name"],
            identifier=l["identifier"],
            is_simulated=bool(l.get("is_simulated", True)),
        )
        for l in d["legs"]
    ]

    transfers = [
        Transfer(
            place_id=t["place_id"],
            arrival_time=datetime.fromisoformat(t["arrival_time"]),
            departure_time=datetime.fromisoformat(t["departure_time"]),
            wait_minutes=int(t["wait_minutes"]),
            min_connection_minutes=int(t["min_connection_minutes"]),
            mode_from=TransitMode(t["mode_from"]),
            mode_to=TransitMode(t["mode_to"]),
            is_intermodal=bool(t.get("is_intermodal", False)),
        )
        for t in d.get("transfers", [])
    ]

    return Itinerary(
        itinerary_id=d["itinerary_id"],
        legs=legs,
        transfers=transfers,
        total_duration_minutes=int(d["total_duration_minutes"]),
        total_fare_paise=int(d["total_fare_paise"]),
        departure_time=datetime.fromisoformat(d["departure_time"]),
        arrival_time=datetime.fromisoformat(d["arrival_time"]),
    )


@router.post("/simulate-delay", response_model=SimulateDelayResponse)
def simulate_trip_delay(
    req: SimulateDelayRequest,
    db: Database = Depends(get_database),
    ds: TransportDataSource = Depends(get_data_source),
) -> SimulateDelayResponse:
    """Inject an artificial delay on a leg and trigger on-demand re-planning if compromised."""
    trip = db.get_trip(req.trip_id)
    if not trip:
        raise HTTPException(
            status_code=404,
            detail=f"Active trip '{req.trip_id}' not found.",
        )

    itinerary_data = trip["itinerary"]
    itinerary = parse_itinerary_from_dict(itinerary_data)

    if req.leg_index >= len(itinerary.legs):
        raise HTTPException(
            status_code=400,
            detail=f"Leg index {req.leg_index} is out of bounds (trip has {len(itinerary.legs)} legs).",
        )

    # Deduce deadline: scheduled arrival + buffer_minutes (stored in scored itinerary) or default 60m buffer
    buffer_mins = itinerary_data.get("buffer_minutes", 60)
    deadline = itinerary.arrival_time + timedelta(minutes=buffer_mins)

    # 1. Recalculate Monte Carlo simulation with injected delay
    recalc_metrics = simulate_itinerary_delays(
        itinerary=itinerary,
        deadline=deadline,
        trials_count=10000,
        injected_delays={req.leg_index: req.injected_delay_minutes},
    )

    # Check risk threshold
    # Deadline at risk if on-time chance drops below 50% or missed connection rate exceeds 40%
    is_at_risk = (recalc_metrics.p_ontime < 0.50) or (recalc_metrics.missed_connection_rate > 0.40)

    # Format risk explanation
    leg_name = itinerary.legs[req.leg_index].identifier
    if is_at_risk:
        if recalc_metrics.missed_connection_rate > 0.40:
            risk_explanation = (
                f"ALERT: A +{int(req.injected_delay_minutes)} min delay on {leg_name} "
                f"causes a {round(recalc_metrics.missed_connection_rate * 100, 1)}% chance of a broken connection. "
                "SANKALP has computed an instant recovery route below."
            )
        else:
            risk_explanation = (
                f"WARNING: A +{int(req.injected_delay_minutes)} min delay on {leg_name} "
                f"reduces on-time certainty to {round(recalc_metrics.p_ontime * 100, 1)}%. "
                "SANKALP has found a faster replacement plan."
            )
    else:
        risk_explanation = (
            f"STABLE: The +{int(req.injected_delay_minutes)} min delay on {leg_name} is absorbed by your safety buffer. "
            f"On-time arrival probability remains high at {round(recalc_metrics.p_ontime * 100, 1)}%."
        )

    # 2. On-demand re-planning if at risk
    replacement_plan_resp: ScoredItineraryResponse | None = None
    if is_at_risk:
        # Traveller's current point will be the destination of the delayed leg
        delayed_leg = itinerary.legs[req.leg_index]
        current_location_id = delayed_leg.destination_id
        final_destination_id = trip["destination_id"]

        # Expected arrival at the current location = scheduled arrival + delay
        delayed_arrival_at_current = delayed_leg.arrival_time + timedelta(
            minutes=req.injected_delay_minutes
        )

        # Run on-demand re-plan from current location to destination
        if current_location_id != final_destination_id:
            try:
                recovery_res = find_journey_recovery(
                    origin_id=current_location_id,
                    destination_id=final_destination_id,
                    departure_after=delayed_arrival_at_current,
                    deadline=deadline,
                    budget_paise=trip["total_fare_paise"] * 2,  # Emergency recovery budget
                    data_source=ds,
                )

                # Pick the safest or balanced replacement
                chosen_tag = (
                    RecommendationTag.SAFEST
                    if RecommendationTag.SAFEST in recovery_res.recommendations
                    else (
                        RecommendationTag.BALANCED
                        if RecommendationTag.BALANCED in recovery_res.recommendations
                        else None
                    )
                )

                if chosen_tag:
                    rep_scored = recovery_res.recommendations[chosen_tag]
                    rep_legs = [
                        LegResponse(
                            leg_id=l.leg_id,
                            origin_id=l.origin_id,
                            destination_id=l.destination_id,
                            mode=l.mode.value,
                            departure_time=l.departure_time.isoformat(),
                            arrival_time=l.arrival_time.isoformat(),
                            duration_minutes=l.duration_minutes,
                            distance_km=l.distance_km,
                            fare_paise=l.fare_paise,
                            fare_inr=l.fare_paise // 100,
                            operator_name=l.operator_name,
                            identifier=l.identifier,
                            is_simulated=l.is_simulated,
                        )
                        for l in rep_scored.itinerary.legs
                    ]
                    rep_transfers = [
                        TransferResponse(
                            place_id=t.place_id,
                            arrival_time=t.arrival_time.isoformat(),
                            departure_time=t.departure_time.isoformat(),
                            wait_minutes=t.wait_minutes,
                            min_connection_minutes=t.min_connection_minutes,
                            mode_from=t.mode_from.value,
                            mode_to=t.mode_to.value,
                            is_intermodal=t.is_intermodal,
                        )
                        for t in rep_scored.itinerary.transfers
                    ]
                    replacement_plan_resp = ScoredItineraryResponse(
                        itinerary_id=rep_scored.itinerary.itinerary_id,
                        tag=rep_scored.tag.value,
                        plain_reason=f"Replacement: {rep_scored.plain_reason}",
                        total_duration_minutes=rep_scored.itinerary.total_duration_minutes,
                        total_fare_paise=rep_scored.itinerary.total_fare_paise,
                        total_fare_inr=rep_scored.itinerary.total_fare_paise // 100,
                        departure_time=rep_scored.itinerary.departure_time.isoformat(),
                        arrival_time=rep_scored.itinerary.arrival_time.isoformat(),
                        num_transfers=rep_scored.itinerary.num_transfers,
                        is_multimodal=rep_scored.itinerary.is_multimodal,
                        buffer_minutes=rep_scored.buffer_minutes,
                        utility_score=rep_scored.utility_score,
                        legs=rep_legs,
                        transfers=rep_transfers,
                        metrics=SimulationMetricsResponse(
                            p_ontime=rep_scored.metrics.p_ontime,
                            p_ontime_ci_95=[
                                rep_scored.metrics.p_ontime_ci_low,
                                rep_scored.metrics.p_ontime_ci_high,
                            ],
                            trials_count=rep_scored.metrics.trials_count,
                            median_delay_minutes=rep_scored.metrics.median_delay_minutes,
                            p90_delay_minutes=rep_scored.metrics.p90_delay_minutes,
                            missed_connection_rate=rep_scored.metrics.missed_connection_rate,
                        ),
                    )
            except Exception:
                # If no alternative corridor found, replacement remains None
                pass

    return SimulateDelayResponse(
        trip_id=req.trip_id,
        leg_index=req.leg_index,
        injected_delay_minutes=req.injected_delay_minutes,
        original_p_ontime=trip["p_ontime"],
        recalculated_metrics=SimulationMetricsResponse(
            p_ontime=recalc_metrics.p_ontime,
            p_ontime_ci_95=[recalc_metrics.p_ontime_ci_low, recalc_metrics.p_ontime_ci_high],
            trials_count=recalc_metrics.trials_count,
            median_delay_minutes=recalc_metrics.median_delay_minutes,
            p90_delay_minutes=recalc_metrics.p90_delay_minutes,
            missed_connection_rate=recalc_metrics.missed_connection_rate,
        ),
        is_deadline_at_risk=is_at_risk,
        risk_explanation=risk_explanation,
        replacement_plan=replacement_plan_resp,
    )
