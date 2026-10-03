"""Pydantic schemas for Natural Language Query Parsing."""

from typing import Optional
from pydantic import BaseModel, Field
from .places import PlaceResponse


class ParseQueryRequest(BaseModel):
    """Request payload for natural language query parser."""

    query: str = Field(..., min_length=3, max_length=500, description="Natural language disruption query text")


class ParseQueryResponse(BaseModel):
    """Structured interpretation of natural language query."""

    raw_query: str
    origin: Optional[PlaceResponse] = None
    destination: Optional[PlaceResponse] = None
    deadline: Optional[str] = None
    budget_paise: Optional[int] = None
    budget_inr: Optional[int] = None
    injected_delay_minutes: Optional[float] = None
    is_cancellation: bool = False
    confidence_score: float
    explanation: str
