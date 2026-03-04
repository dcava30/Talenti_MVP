"""Internal worker auth tests."""
from fastapi.testclient import TestClient


def test_internal_calls_require_shared_secret(client: TestClient) -> None:
    """Internal call routes reject requests without the worker secret."""
    response = client.post(
        "/internal/calls/create",
        json={"interview_id": "int-1", "target_identity": "8:acs:user"},
    )
    assert response.status_code == 401
