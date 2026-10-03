"""API Tests for Delay Simulation and On-Demand Re-planning."""

from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sankalp_engine.models import IST
from app.main import app
from app.dependencies import get_data_source


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def approved_trip_id(client: TestClient) -> str:
    """Fixture to create an approved trip for simulation testing."""
    ds = get_data_source()
    nodes = ds.get_all_places()
    orig = nodes[0]
    dest = nodes[1]
    now = datetime.now(IST)

    itin_id = "itin_sim_fixture_1"
    token_resp = client.post("/v1/recover/confirm-token", json={"itinerary_id": itin_id})
    token = token_resp.json()["approval_token"]

    itinerary_dict = {
        "itinerary_id": itin_id,
        "legs": [
            {
                "leg_id": "leg_sim_1",
                "origin_id": orig.id,
                "destination_id": dest.id,
                "mode": "TRAIN",
                "departure_time": (now + timedelta(hours=1)).isoformat(),
                "arrival_time": (now + timedelta(hours=4)).isoformat(),
                "duration_minutes": 180,
                "distance_km": 300.0,
                "fare_paise": 65000,
                "operator_name": "Express",
                "identifier": "EX-101",
                "is_simulated": True,
            }
        ],
        "transfers": [],
        "total_duration_minutes": 180,
        "total_fare_paise": 65000,
        "departure_time": (now + timedelta(hours=1)).isoformat(),
        "arrival_time": (now + timedelta(hours=4)).isoformat(),
        "buffer_minutes": 60,
    }

    approve_resp = client.post(
        "/v1/recover/approve",
        json={
            "itinerary_id": itin_id,
            "approval_token": token,
            "origin_id": orig.id,
            "destination_id": dest.id,
            "total_fare_paise": 65000,
            "p_ontime": 0.92,
            "itinerary": itinerary_dict,
        },
    )
    return approve_resp.json()["trip_id"]


def test_simulate_minor_delay_stable(client: TestClient, approved_trip_id: str) -> None:
    """Verify minor delay within safety buffer keeps plan stable."""
    payload = {
        "trip_id": approved_trip_id,
        "leg_index": 0,
        "injected_delay_minutes": 10.0,
    }
    resp = client.post("/v1/trip/simulate-delay", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["trip_id"] == approved_trip_id
    assert data["injected_delay_minutes"] == 10.0
    assert data["is_deadline_at_risk"] is False
    assert "STABLE" in data["risk_explanation"]
    assert data["replacement_plan"] is None


def test_simulate_major_delay_triggers_risk(client: TestClient, approved_trip_id: str) -> None:
    """Verify major delay exceeding buffer marks deadline at risk."""
    payload = {
        "trip_id": approved_trip_id,
        "leg_index": 0,
        "injected_delay_minutes": 180.0,
    }
    resp = client.post("/v1/trip/simulate-delay", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["trip_id"] == approved_trip_id
    assert data["is_deadline_at_risk"] is True
    assert ("ALERT" in data["risk_explanation"]) or ("WARNING" in data["risk_explanation"])
    assert data["recalculated_metrics"]["p_ontime"] < 0.50


def test_simulate_delay_out_of_bounds_leg(client: TestClient, approved_trip_id: str) -> None:
    """Verify out-of-bounds leg index returns HTTP 400."""
    payload = {
        "trip_id": approved_trip_id,
        "leg_index": 5,
        "injected_delay_minutes": 30.0,
    }
    resp = client.post("/v1/trip/simulate-delay", json=payload)
    assert resp.status_code == 400
    assert "out of bounds" in resp.json()["detail"].lower()


def test_simulate_delay_nonexistent_trip(client: TestClient) -> None:
    """Verify simulating delay on invalid trip returns HTTP 404."""
    payload = {
        "trip_id": "trip_does_not_exist_404",
        "leg_index": 0,
        "injected_delay_minutes": 20.0,
    }
    resp = client.post("/v1/trip/simulate-delay", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
