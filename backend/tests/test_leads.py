"""Lead CRUD tests: the core REST/HTTP teaching surface."""
from fastapi.testclient import TestClient


def _create(client: TestClient, **overrides: object) -> dict:
    """Helper: create one lead via the API and return the response body."""
    payload = {"name": "Test User", "phone": "9000000001", **overrides}
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_lead_computes_score_and_priority(client: TestClient) -> None:
    """Given a valid payload with phone + requirement
    When POST /api/v1/leads is called
    Then 201 is returned with the deterministic score applied."""
    body = _create(client, requirement="whatsapp automation")
    lead = body["lead"]
    assert body["success"] is True
    assert lead["lead_score"] == 35  # phone 20 + requirement 15
    assert lead["priority"] == "low"
    assert lead["status"] == "new"
    assert lead["source"] == "api"


def test_create_lead_rejects_blank_name(client: TestClient) -> None:
    """Given a blank name
    When POST /api/v1/leads is called
    Then 422 is returned in the standard error envelope."""
    response = client.post("/api/v1/leads", json={"name": "", "phone": "9000000001"})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_create_lead_rejects_bad_phone(client: TestClient) -> None:
    """Given a phone number that is too short
    When POST /api/v1/leads is called
    Then 422 is returned."""
    response = client.post("/api/v1/leads", json={"name": "A", "phone": "123"})
    assert response.status_code == 422


def test_get_lead_by_id(client: TestClient) -> None:
    """Given an existing lead
    When GET /api/v1/leads/{id} is called
    Then the same lead is returned."""
    created = _create(client)["lead"]
    response = client.get(f"/api/v1/leads/{created['id']}")
    assert response.status_code == 200
    assert response.json()["lead"]["name"] == "Test User"


def test_get_missing_lead_returns_404_envelope(client: TestClient) -> None:
    """Given no lead with id 999999
    When GET is called
    Then 404 with code LEAD_NOT_FOUND is returned."""
    response = client.get("/api/v1/leads/999999")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "LEAD_NOT_FOUND"


def test_list_leads_filters_by_priority(client: TestClient) -> None:
    """Given leads of different priorities
    When GET /api/v1/leads?priority=high is called
    Then only high-priority leads are returned."""
    _create(client, name="Low Lead", phone="9000000001")
    _create(
        client, name="High Lead", phone="9000000002",
        requirement="whatsapp automation", business_type="real estate",
        city="Mumbai", monthly_queries=500, timeline="ASAP",
        email="high@example.com",
    )
    response = client.get("/api/v1/leads", params={"priority": "high"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["leads"][0]["name"] == "High Lead"


def test_update_lead_recomputes_score(client: TestClient) -> None:
    """Given an existing low-score lead
    When PATCH adds scoring fields
    Then the score and priority are recomputed."""
    created = _create(client)["lead"]
    response = client.patch(
        f"/api/v1/leads/{created['id']}",
        json={"city": "Mumbai", "monthly_queries": 500, "requirement": "voice bot"},
    )
    assert response.status_code == 200
    lead = response.json()["lead"]
    # phone 20 + requirement 15 + city 10 + volume 15 = 60 -> medium
    assert lead["lead_score"] == 60
    assert lead["priority"] == "medium"


def test_update_missing_lead_returns_404(client: TestClient) -> None:
    """Given no lead with id 999999
    When PATCH is called
    Then 404 is returned."""
    response = client.patch("/api/v1/leads/999999", json={"city": "Mumbai"})
    assert response.status_code == 404


def test_delete_lead_returns_204(client: TestClient) -> None:
    """Given an existing lead
    When DELETE is called
    Then 204 is returned and the lead is gone."""
    created = _create(client)["lead"]
    assert client.delete(f"/api/v1/leads/{created['id']}").status_code == 204
    assert client.get(f"/api/v1/leads/{created['id']}").status_code == 404


def test_delete_missing_lead_returns_404(client: TestClient) -> None:
    """Given no lead with id 999999
    When DELETE is called
    Then 404 is returned."""
    assert client.delete("/api/v1/leads/999999").status_code == 404
