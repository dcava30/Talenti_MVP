import importlib
import sys

import pytest

from fastapi.testclient import TestClient
from conftest import backend_root, clear_app_modules, prepare_test_environment, reset_database_with_migrations


def create_client() -> TestClient:
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    database_url = prepare_test_environment()
    reset_database_with_migrations(database_url)
    clear_app_modules()
    import app.core.config as config

    importlib.reload(config)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_health_endpoint() -> None:
    client = create_client()
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_routes_exist() -> None:
    client = create_client()

    response = client.get("/api/v1/interviews/active", params={"application_id": "app-1"})
    assert response.status_code == 401

    response = client.get("/api/v1/applications")
    assert response.status_code == 401

    response = client.get("/api/v1/audit-log")
    assert response.status_code == 401

    response = client.patch("/api/v1/interview-scores/score-1", json={})
    assert response.status_code == 401

    response = client.post("/api/v1/interviews", json={"application_id": "app-1"})
    assert response.status_code == 401

    response = client.post("/api/v1/interviews/start", json={"application_id": "app-1"})
    assert response.status_code == 401

    response = client.post("/api/v1/interviews/int-1/complete", json={"duration_seconds": 30})
    assert response.status_code == 401

    response = client.post(
        "/api/v1/call-automation/calls",
        json={"interview_id": "int-1", "target_identity": "8:acs:user"},
    )
    assert response.status_code == 401

    response = client.post(
        "/api/storage/upload-url",
        json={"file_name": "resume.pdf", "purpose": "candidate_cv"},
    )
    assert response.status_code == 401

    response = client.post(
        "/api/v1/interview/chat",
        json={"interview_id": "int-1", "messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 401
