"""API Tests for Multi-Modal Journey Recovery Search Endpoints."""

from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sankalp_engine.models import IST
from app.main import app
from app.dependencies import get_data_source


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_recovery_search_successful(client: TestClient) -> None:
    """Verify executing a valid recovery search returns Pareto recommendations with metrics."""
    ds = get_data_source()
    nodes = ds.get_all_places()
    origin = nodes[0]
    destination = nodes[1]

    now = datetime.now(IST)
    dep_time = now + timedelta(hours=2)
    deadline = now + timedelta(hours=36)

    payload = {
        "origin_id": origin.id,
        "destination_id": destination.id,
        "departure_after": dep_time.isoformat(),
        "deadline": deadline.isoformat(),
        "budget_paise": 600000,
    }

    response = client.post("/v1/recover/search", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "search_id" in data
    assert data["origin"]["id"] == origin.id
    assert data["destination"]["id"] == destination.id
    assert "Simulated schedules" in data["data_disclaimer"]
    assert "recommendations" in data
    assert isinstance(data["recommendations"], dict)

    # Check structure of at least one returned recommendation
    if data["recommendations"]:
        rec = next(iter(data["recommendations"].values()))
        assert "itinerary_id" in rec
        assert "tag" in rec
        assert "plain_reason" in rec
        assert "legs" in rec
        assert "metrics" in rec
        assert len(rec["legs"]) >= 1

        metrics = rec["metrics"]
        assert 0.0 <= metrics["p_ontime"] <= 1.0
        assert len(metrics["p_ontime_ci_95"]) == 2
        assert metrics["p_ontime_ci_95"][0] <= metrics["p_ontime_ci_95"][1]
        assert metrics["trials_count"] == 10000


def test_recovery_search_same_origin_destination(client: TestClient) -> None:
    """Verify search returns HTTP 400 when origin equals destination."""
    ds = get_data_source()
    node = ds.get_all_places()[0]

    now = datetime.now(IST)
    payload = {
        "origin_id": node.id,
        "destination_id": node.id,
        "deadline": (now + timedelta(hours=12)).isoformat(),
    }

    response = client.post("/v1/recover/search", json=payload)
    assert response.status_code == 400
    assert "distinct" in response.json()["detail"].lower()


def test_recovery_search_invalid_origin(client: TestClient) -> None:
    """Verify search returns HTTP 404 when origin place does not exist."""
    ds = get_data_source()
    valid_dest = ds.get_all_places()[0]

    now = datetime.now(IST)
    payload = {
        "origin_id": "invalid_origin_xyz",
        "destination_id": valid_dest.id,
        "deadline": (now + timedelta(hours=12)).isoformat(),
    }

    response = client.post("/v1/recover/search", json=payload)
    assert response.status_code == 404
    assert "origin" in response.json()["detail"].lower()


def test_recovery_search_invalid_destination(client: TestClient) -> None:
    """Verify search returns HTTP 404 when destination place does not exist."""
    ds = get_data_source()
    valid_orig = ds.get_all_places()[0]

    now = datetime.now(IST)
    payload = {
        "origin_id": valid_orig.id,
        "destination_id": "invalid_dest_xyz",
        "deadline": (now + timedelta(hours=12)).isoformat(),
    }

    response = client.post("/v1/recover/search", json=payload)
    assert response.status_code == 404
    assert "destination" in response.json()["detail"].lower()
