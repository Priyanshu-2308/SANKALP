"""API Tests for Natural Language Query Parser Endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_data_source


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_api_parse_natural_language_query(client: TestClient) -> None:
    """Verify endpoint extracts structured origin, destination, deadline, and budget."""
    ds = get_data_source()
    places = ds.get_all_places()
    orig = places[0]
    dest = places[1]

    query_text = (
        f"My train from {orig.name} to {dest.name} is delayed by 3 hours, "
        "need to arrive before 9 PM with budget 3500 rupees"
    )

    resp = client.post("/v1/recover/parse-query", json={"query": query_text})
    assert resp.status_code == 200
    data = resp.json()

    assert data["raw_query"] == query_text
    assert data["origin"] is not None
    assert data["origin"]["id"] == orig.id
    assert data["destination"] is not None
    assert data["destination"]["id"] == dest.id
    assert data["injected_delay_minutes"] == 180.0
    assert data["budget_inr"] == 3500
    assert data["budget_paise"] == 350000
    assert data["deadline"] is not None
    assert data["confidence_score"] >= 0.80
    assert len(data["explanation"]) > 0


def test_api_parse_query_short_input_validation(client: TestClient) -> None:
    """Verify short or invalid queries are properly validated."""
    resp = client.post("/v1/recover/parse-query", json={"query": "hi"})
    assert resp.status_code == 422  # Pydantic validation error (min_length=3)
