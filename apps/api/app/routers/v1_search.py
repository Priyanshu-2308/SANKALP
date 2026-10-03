"""FastAPI endpoints for multi-modal journey recovery search."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sankalp_engine.datasource import TransportDataSource
from sankalp_engine.engine import find_journey_recovery
from sankalp_engine.nl_parser import NaturalLanguageQueryParser

from ..dependencies import get_data_source
from ..schemas.nl_query import ParseQueryRequest, ParseQueryResponse
from ..schemas.places import PlaceResponse
from ..schemas.search import (
    ExclusionRationaleResponse,
    LegResponse,
    RecoverySearchRequest,
    RecoverySearchResponse,
    ScoredItineraryResponse,
    SimulationMetricsResponse,
    TransferResponse,
)

router = APIRouter(prefix="/v1/recover", tags=["Recovery Search"])


@router.post("/search", response_model=RecoverySearchResponse)
def execute_recovery_search(
    req: RecoverySearchRequest,
    ds: TransportDataSource = Depends(get_data_source),
) -> RecoverySearchResponse:
    """Execute multi-modal recovery search and return Safest, Balanced, and Cheapest plans."""
    # Resolve origin and destination (accept either ID or code)
    orig_place = ds.get_place(req.origin_id) or ds.get_place_by_code(req.origin_id)
    if not orig_place:
        raise HTTPException(
            status_code=404,
            detail=f"Origin place identifier '{req.origin_id}' not found.",
        )

    dest_place = ds.get_place(req.destination_id) or ds.get_place_by_code(req.destination_id)
    if not dest_place:
        raise HTTPException(
            status_code=404,
            detail=f"Destination place identifier '{req.destination_id}' not found.",
        )

    if orig_place.id == dest_place.id:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination stations must be distinct.",
        )

    try:
        result = find_journey_recovery(
            origin_id=orig_place.id,
            destination_id=dest_place.id,
            deadline=req.deadline,
            budget_paise=req.budget_paise or 500000,
            data_source=ds,
            departure_after=req.departure_after,
            trials_count=10000,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search engine failure: {str(e)}")

    # Map scored itineraries into API response models
    recommendations_map: dict[str, ScoredItineraryResponse] = {}
    for tag, scored in result.recommendations.items():
        legs_resp = [
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
            for l in scored.itinerary.legs
        ]

        transfers_resp = [
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
            for t in scored.itinerary.transfers
        ]

        metrics_resp = SimulationMetricsResponse(
            p_ontime=scored.metrics.p_ontime,
            p_ontime_ci_95=[scored.metrics.p_ontime_ci_low, scored.metrics.p_ontime_ci_high],
            trials_count=scored.metrics.trials_count,
            median_delay_minutes=scored.metrics.median_delay_minutes,
            p90_delay_minutes=scored.metrics.p90_delay_minutes,
            missed_connection_rate=scored.metrics.missed_connection_rate,
        )

        recommendations_map[tag.value.lower()] = ScoredItineraryResponse(
            itinerary_id=scored.itinerary.itinerary_id,
            tag=scored.tag.value,
            plain_reason=scored.plain_reason,
            total_duration_minutes=scored.itinerary.total_duration_minutes,
            total_fare_paise=scored.itinerary.total_fare_paise,
            total_fare_inr=scored.itinerary.total_fare_paise // 100,
            departure_time=scored.itinerary.departure_time.isoformat(),
            arrival_time=scored.itinerary.arrival_time.isoformat(),
            num_transfers=scored.itinerary.num_transfers,
            is_multimodal=scored.itinerary.is_multimodal,
            buffer_minutes=scored.buffer_minutes,
            utility_score=scored.utility_score,
            legs=legs_resp,
            transfers=transfers_resp,
            metrics=metrics_resp,
        )

    pruned_resp = [
        ExclusionRationaleResponse(
            itinerary_summary=p.itinerary_summary,
            code=p.code.value,
            reason_text=p.reason_text,
        )
        for p in result.pruned_candidates
    ]

    return RecoverySearchResponse(
        search_id=f"sch_{uuid.uuid4().hex[:8]}",
        origin=result.origin.to_dict(),
        destination=result.destination.to_dict(),
        deadline=result.deadline.isoformat(),
        budget_paise=result.budget_paise,
        budget_inr=result.budget_paise // 100,
        total_candidates_searched=result.total_candidates_searched,
        execution_time_ms=result.execution_time_ms,
        data_disclaimer=result.data_disclaimer,
        recommendations=recommendations_map,
        pruned_candidates=pruned_resp,
    )


@router.post("/parse-query", response_model=ParseQueryResponse)
def parse_natural_language_query(
    req: ParseQueryRequest,
    ds: TransportDataSource = Depends(get_data_source),
) -> ParseQueryResponse:
    """Parse unstructured journey disruption text into structured recovery parameters."""
    parser = NaturalLanguageQueryParser(data_source=ds)
    parsed = parser.parse(req.query)

    orig_resp = None
    if parsed.origin:
        orig_resp = PlaceResponse(
            id=parsed.origin.id,
            name=parsed.origin.name,
            code=parsed.origin.code,
            place_type=parsed.origin.place_type.value,
            city=parsed.origin.city,
            state=parsed.origin.state,
            latitude=parsed.origin.latitude,
            longitude=parsed.origin.longitude,
            tier=parsed.origin.tier,
            aliases=parsed.origin.aliases,
        )

    dest_resp = None
    if parsed.destination:
        dest_resp = PlaceResponse(
            id=parsed.destination.id,
            name=parsed.destination.name,
            code=parsed.destination.code,
            place_type=parsed.destination.place_type.value,
            city=parsed.destination.city,
            state=parsed.destination.state,
            latitude=parsed.destination.latitude,
            longitude=parsed.destination.longitude,
            tier=parsed.destination.tier,
            aliases=parsed.destination.aliases,
        )

    return ParseQueryResponse(
        raw_query=parsed.raw_query,
        origin=orig_resp,
        destination=dest_resp,
        deadline=parsed.deadline.isoformat() if parsed.deadline else None,
        budget_paise=parsed.budget_paise,
        budget_inr=parsed.budget_inr,
        injected_delay_minutes=parsed.injected_delay_minutes,
        is_cancellation=parsed.is_cancellation,
        confidence_score=parsed.confidence_score,
        explanation=parsed.explanation,
    )

