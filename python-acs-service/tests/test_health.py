"""Health endpoint tests."""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Health endpoint returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
