"""API Tests for Place Search and Station Autocomplete Endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_data_source


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_root_status(client: TestClient) -> None:
    """Verify root endpoint returns system status and simulated data disclaimer."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "Simulated schedules" in data["data_disclaimer"]


def test_health_check(client: TestClient) -> None:
    """Verify health check endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_search_places_empty_query(client: TestClient) -> None:
    """Verify searching with empty query returns default list of major transit hubs."""
    response = client.get("/v1/places/search?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert len(data["results"]) <= 10
    first = data["results"][0]
    assert "id" in first
    assert "name" in first
    assert "code" in first
    assert "place_type" in first


def test_search_places_by_code_and_name(client: TestClient) -> None:
    """Verify searching by code or partial name returns matching hubs."""
    ds = get_data_source()
    sample_node = ds.get_all_places()[0]

    response = client.get(f"/v1/places/search?q={sample_node.code}")
    assert response.status_code == 200
    data = response.json()
    assert any(p["id"] == sample_node.id for p in data["results"])


def test_get_place_by_id(client: TestClient) -> None:
    """Verify looking up a place by its unique ID returns complete metadata."""
    ds = get_data_source()
    sample_node = ds.get_all_places()[0]

    response = client.get(f"/v1/places/{sample_node.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_node.id
    assert data["code"] == sample_node.code
    assert data["name"] == sample_node.name


def test_get_place_not_found(client: TestClient) -> None:
    """Verify looking up a nonexistent place ID returns HTTP 404."""
    response = client.get("/v1/places/nonexistent_xyz_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
