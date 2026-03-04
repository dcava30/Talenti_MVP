"""Internal recordings endpoint tests."""
from fastapi.testclient import TestClient


def test_internal_recordings_require_shared_secret(client: TestClient) -> None:
    """Recording routes are internal-only and require a shared secret."""
    response = client.post(
        "/internal/recordings/start",
        json={"interview_id": "int-1", "server_call_id": "srv-1"},
    )
    assert response.status_code == 401
