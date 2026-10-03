"""Unit Tests for Natural Language Journey Query Parser."""

from datetime import datetime, timedelta
import pytest
from sankalp_engine.datasource import TransportDataSource
from sankalp_engine.models import IST
from sankalp_engine.nl_parser import NaturalLanguageQueryParser
from app.dependencies import get_data_source


@pytest.fixture
def parser() -> NaturalLanguageQueryParser:
    ds: TransportDataSource = get_data_source()
    return NaturalLanguageQueryParser(data_source=ds)


def test_parse_structured_journey_query(parser: NaturalLanguageQueryParser) -> None:
    """Verify parsing a full natural language query with delay, deadline, and budget."""
    now = datetime(2026, 10, 3, 10, 0, tzinfo=IST)

    # Pick dynamic place names from data source
    places = parser.ds.get_all_places()
    orig = places[0]
    dest = places[1]

    query = f"My train from {orig.name} to {dest.name} is delayed by 2.5 hours, get me there by 8 PM under 2500 rupees"
    parsed = parser.parse(query, reference_time=now)

    assert parsed.origin is not None
    assert parsed.origin.id == orig.id
    assert parsed.destination is not None
    assert parsed.destination.id == dest.id
    assert parsed.injected_delay_minutes == 150.0  # 2.5h = 150m
    assert parsed.budget_inr == 2500
    assert parsed.budget_paise == 250000
    assert parsed.deadline is not None
    assert parsed.deadline.hour == 20  # 8 PM
    assert parsed.confidence_score >= 0.80
    assert "Origin resolved" in parsed.explanation


def test_parse_cancellation_query(parser: NaturalLanguageQueryParser) -> None:
    """Verify detecting cancellation keywords in conversational prompt."""
    now = datetime(2026, 10, 3, 14, 0, tzinfo=IST)
    places = parser.ds.get_all_places()
    orig = places[2]
    dest = places[3]

    query = f"Train from {orig.name} to {dest.name} was cancelled! Need to reach before 11 PM budget 4000"
    parsed = parser.parse(query, reference_time=now)

    assert parsed.is_cancellation is True
    assert parsed.origin is not None
    assert parsed.origin.id == orig.id
    assert parsed.destination is not None
    assert parsed.destination.id == dest.id
    assert parsed.budget_inr == 4000
    assert parsed.deadline is not None
    assert parsed.deadline.hour == 23


def test_parse_minimal_query(parser: NaturalLanguageQueryParser) -> None:
    """Verify fallback behavior when query has minimal information."""
    parsed = parser.parse("Need urgent transit assistance")
    assert parsed.origin is None
    assert parsed.destination is None
    assert parsed.budget_inr is None
    assert parsed.confidence_score < 0.50
