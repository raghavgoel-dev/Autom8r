"""Webhook tests: shared-secret auth + idempotent ingestion."""
from fastapi.testclient import TestClient

from tests.conftest import WEBHOOK_HEADERS

_EVENT = {
    "event": "lead.created",
    "source": "website-demo",
    "timestamp": "2026-09-19T10:30:00Z",
    "event_id": "evt-test-1",
    "data": {
        "name": "Aman",
        "phone": "9999999999",
        "requirement": "customer support automation",
        "city": "Gurgaon",
    },
}


def test_webhook_without_secret_returns_401(client: TestClient) -> None:
    """Given no X-Webhook-Secret header
    When POST /api/v1/webhooks/lead is called
    Then 401 UNAUTHORIZED is returned in the envelope."""
    response = client.post("/api/v1/webhooks/lead", json=_EVENT)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_webhook_with_wrong_secret_returns_401(client: TestClient) -> None:
    """Given an incorrect secret
    When POST is called
    Then 401 is returned and no lead is created."""
    response = client.post(
        "/api/v1/webhooks/lead", json=_EVENT, headers={"X-Webhook-Secret": "wrong"}
    )
    assert response.status_code == 401
    assert client.get("/api/v1/leads").json()["count"] == 0


def test_webhook_creates_lead(client: TestClient) -> None:
    """Given a valid event and secret
    When POST is called
    Then 201 is returned with a scored lead from the event source."""
    response = client.post("/api/v1/webhooks/lead", json=_EVENT, headers=WEBHOOK_HEADERS)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["duplicate"] is False
    lead = body["lead"]
    assert lead["name"] == "Aman"
    assert lead["source"] == "website-demo"
    # phone 20 + requirement 15 + city 10 = 45 -> medium
    assert lead["lead_score"] == 45
    assert lead["priority"] == "medium"


def test_webhook_duplicate_event_is_acknowledged_not_recreated(client: TestClient) -> None:
    """Given an event_id that was already processed
    When the same event is redelivered
    Then 200 duplicate=true is returned and only one lead exists."""
    first = client.post("/api/v1/webhooks/lead", json=_EVENT, headers=WEBHOOK_HEADERS)
    assert first.status_code == 201
    second = client.post("/api/v1/webhooks/lead", json=_EVENT, headers=WEBHOOK_HEADERS)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert client.get("/api/v1/leads").json()["count"] == 1


def test_webhook_invalid_payload_returns_422(client: TestClient) -> None:
    """Given an event missing required data fields
    When POST is called with a valid secret
    Then 422 is returned."""
    response = client.post(
        "/api/v1/webhooks/lead",
        json={"event": "lead.created", "source": "x", "data": {"name": "NoPhone"}},
        headers=WEBHOOK_HEADERS,
    )
    assert response.status_code == 422
