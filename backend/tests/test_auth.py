"""Admin authentication tests (Bearer token) + admin endpoints."""
from fastapi.testclient import TestClient

from tests.conftest import ADMIN_HEADERS


def test_stats_without_token_returns_401(client: TestClient) -> None:
    """Given no Authorization header
    When GET /api/v1/admin/stats is called
    Then 401 UNAUTHORIZED is returned."""
    response = client.get("/api/v1/admin/stats")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_stats_with_wrong_token_returns_401(client: TestClient) -> None:
    """Given an incorrect Bearer token
    When GET stats is called
    Then 401 is returned."""
    response = client.get("/api/v1/admin/stats", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_stats_with_malformed_header_returns_401(client: TestClient) -> None:
    """Given a non-Bearer Authorization header
    When GET stats is called
    Then 401 is returned."""
    response = client.get("/api/v1/admin/stats", headers={"Authorization": "Token abc"})
    assert response.status_code == 401


def test_stats_with_valid_token(client: TestClient) -> None:
    """Given the correct admin token
    When GET stats is called
    Then 200 is returned with all six metric keys."""
    response = client.get("/api/v1/admin/stats", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    stats = response.json()["stats"]
    assert set(stats) == {
        "total_leads", "new_leads", "qualified_leads",
        "high_priority_leads", "medium_priority_leads", "low_priority_leads",
    }
    assert stats["total_leads"] == 0


def test_recent_leads_requires_and_accepts_token(client: TestClient) -> None:
    """Given the admin token
    When GET recent-leads is called
    Then 200 with the list envelope is returned."""
    assert client.get("/api/v1/admin/recent-leads").status_code == 401
    response = client.get("/api/v1/admin/recent-leads", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json()["success"] is True
