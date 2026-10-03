"""FastAPI endpoints for place lookup and station autocomplete."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sankalp_engine.datasource import TransportDataSource

from ..dependencies import get_data_source
from ..schemas.places import PlaceResponse, PlaceSearchResponse

router = APIRouter(prefix="/v1/places", tags=["Places & Stations"])


@router.get("/search", response_model=PlaceSearchResponse)
def search_places(
    q: str = Query("", description="Search term for station name, city, code, or alias"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    ds: TransportDataSource = Depends(get_data_source),
) -> PlaceSearchResponse:
    """Search for railway stations, airports, or bus terminals across India."""
    results = ds.search_places(query=q, limit=limit)
    mapped = [
        PlaceResponse(
            id=p.id,
            name=p.name,
            code=p.code,
            place_type=p.place_type.value,
            city=p.city,
            state=p.state,
            latitude=p.latitude,
            longitude=p.longitude,
            tier=p.tier,
            aliases=p.aliases,
        )
        for p in results
    ]
    return PlaceSearchResponse(
        query=q,
        count=len(mapped),
        results=mapped,
    )


@router.get("/{place_id}", response_model=PlaceResponse)
def get_place_by_id(
    place_id: str,
    ds: TransportDataSource = Depends(get_data_source),
) -> PlaceResponse:
    """Retrieve details of a specific station or airport by ID or code."""
    place = ds.get_place(place_id) or ds.get_place_by_code(place_id)
    if not place:
        raise HTTPException(
            status_code=404,
            detail=f"Transit node '{place_id}' not found in bundled dataset.",
        )
    return PlaceResponse(
        id=place.id,
        name=place.name,
        code=place.code,
        place_type=place.place_type.value,
        city=place.city,
        state=place.state,
        latitude=place.latitude,
        longitude=place.longitude,
        tier=place.tier,
        aliases=place.aliases,
    )
