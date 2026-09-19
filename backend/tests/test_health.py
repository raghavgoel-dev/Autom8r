"""Health endpoint tests."""
from fastapi.testclient import TestClient


def test_health_returns_ok_and_mock_mode(client: TestClient) -> None:
    """Given the app running with LLM disabled
    When GET /health is called
    Then it returns 200 with status ok and llm_mode 'mock'."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "autom8r"
    assert body["llm_mode"] == "mock"
