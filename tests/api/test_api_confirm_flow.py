"""API Tests for Single-Use Approval Tokens, Trip Confirmation, and Audit Log."""

from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sankalp_engine.models import IST
from app.main import app
from app.dependencies import get_data_source


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_approval_token_issuance_and_single_use_redemption(client: TestClient) -> None:
    """Verify approval token issuance, atomic redemption, and strict 410 rejection on second use."""
    itinerary_id = "itin_test_mock_123"

    # 1. Request single-use token
    token_resp = client.post(
        "/v1/recover/confirm-token",
        json={"itinerary_id": itinerary_id},
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert token_data["itinerary_id"] == itinerary_id
    assert "approval_token" in token_data
    token = token_data["approval_token"]
    assert len(token) >= 32
    assert token_data["ttl_seconds"] == 900

    # 2. Build mock approval payload
    ds = get_data_source()
    nodes = ds.get_all_places()
    orig = nodes[0]
    dest = nodes[1]

    now = datetime.now(IST)
    itinerary_dict = {
        "itinerary_id": itinerary_id,
        "legs": [
            {
                "leg_id": "leg_1",
                "origin_id": orig.id,
                "destination_id": dest.id,
                "mode": "TRAIN",
                "departure_time": (now + timedelta(hours=1)).isoformat(),
                "arrival_time": (now + timedelta(hours=6)).isoformat(),
                "duration_minutes": 300,
                "distance_km": 400.0,
                "fare_paise": 85000,
                "operator_name": "Indian Railways",
                "identifier": "12345",
                "is_simulated": True,
            }
        ],
        "transfers": [],
        "total_duration_minutes": 300,
        "total_fare_paise": 85000,
        "departure_time": (now + timedelta(hours=1)).isoformat(),
        "arrival_time": (now + timedelta(hours=6)).isoformat(),
    }

    approve_payload = {
        "itinerary_id": itinerary_id,
        "approval_token": token,
        "origin_id": orig.id,
        "destination_id": dest.id,
        "total_fare_paise": 85000,
        "p_ontime": 0.88,
        "itinerary": itinerary_dict,
    }

    # 3. Redeem token for the first time -> Should succeed
    approve_resp = client.post("/v1/recover/approve", json=approve_payload)
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()
    assert approve_data["status"] == "APPROVED"
    assert "trip_id" in approve_data
    trip_id = approve_data["trip_id"]

    # 4. Attempt to reuse the SAME token -> MUST return HTTP 410 GONE
    reuse_resp = client.post("/v1/recover/approve", json=approve_payload)
    assert reuse_resp.status_code == 410
    assert "already been used" in reuse_resp.json()["detail"].lower()

    # 5. Retrieve trip by ID -> Should return full audit details
    trip_resp = client.get(f"/v1/trips/{trip_id}")
    assert trip_resp.status_code == 200
    trip_data = trip_resp.json()
    assert trip_data["trip_id"] == trip_id
    assert trip_data["origin_id"] == orig.id
    assert trip_data["destination_id"] == dest.id
    assert trip_data["total_fare_paise"] == 85000
    assert trip_data["total_fare_inr"] == 850
    assert trip_data["action"] == "APPROVED"
    assert trip_data["itinerary"]["itinerary_id"] == itinerary_id


def test_get_nonexistent_trip(client: TestClient) -> None:
    """Verify retrieving a non-existent trip returns HTTP 404."""
    resp = client.get("/v1/trips/trip_invalid_00000")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
