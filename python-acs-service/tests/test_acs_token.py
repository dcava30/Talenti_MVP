"""Internal calls endpoint tests."""
from fastapi.testclient import TestClient


def test_internal_calls_validate_payload_with_secret(client: TestClient) -> None:
    """With valid secret, payload validation is enforced by pydantic models."""
    response = client.post(
        "/internal/calls/create",
        headers={"X-ACS-Worker-Secret": "test-worker-secret"},
        json={},
    )
    assert response.status_code == 422
