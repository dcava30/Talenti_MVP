"""Auth endpoint tests."""
from fastapi.testclient import TestClient


def test_login_returns_token(client: TestClient) -> None:
    """Login returns a bearer token."""
    response = client.post("/auth/login", json={"username": "user@example.com", "password": "password123"})
    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"
