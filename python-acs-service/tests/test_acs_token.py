"""ACS token endpoint tests."""
from fastapi.testclient import TestClient


def _get_token(client: TestClient) -> str:
    response = client.post("/auth/login", json={"username": "acs@example.com", "password": "password123"})
    return response.json()["access_token"]


def test_acs_token_returns_mocked_in_dev(client: TestClient) -> None:
    """ACS token endpoint returns mocked token in dev when config missing."""
    token = _get_token(client)
    response = client.post("/acs/token", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["mocked"] is True
    assert payload["token"]
