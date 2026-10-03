"""Pydantic schemas for transit place endpoints."""

from typing import Optional
from pydantic import BaseModel, Field


class PlaceResponse(BaseModel):
    """Transit node representation (station, airport, bus terminal)."""
    id: str = Field(..., description="Unique place identifier, e.g. 'STN_NDLS'")
    name: str = Field(..., description="Full English place name")
    code: str = Field(..., description="Station or airport code, e.g. 'NDLS'")
    place_type: str = Field(..., description="rail_station, airport, or bus_terminal")
    city: str = Field(..., description="City or district name")
    state: str = Field(..., description="State or Union Territory")
    latitude: float = Field(..., description="Geographic latitude coordinate")
    longitude: float = Field(..., description="Geographic longitude coordinate")
    tier: int = Field(..., description="Hub tier: 1 (Metro/Major), 2 (Regional), 3 (Feeder)")
    aliases: list[str] = Field(default_factory=list, description="Common nicknames or alternate spellings")


class PlaceSearchResponse(BaseModel):
    """Autocomplete search results."""
    query: str
    count: int
    results: list[PlaceResponse]
    data_disclaimer: str = "Simulated schedules"
