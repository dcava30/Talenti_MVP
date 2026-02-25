import importlib
import os
import sys
from pathlib import Path

import pytest

from fastapi.testclient import TestClient


def create_client(tmp_path: Path) -> TestClient:
    pytest.importorskip("email_validator")
    backend_root = str(Path(__file__).resolve().parents[1])
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test.db"
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["ALLOWED_ORIGINS"] = '["http://localhost"]'
    os.environ["ENVIRONMENT"] = "test"
    import app.core.config as config

    importlib.reload(config)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_health_endpoint(tmp_path: Path) -> None:
    client = create_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_routes_exist(tmp_path: Path) -> None:
    client = create_client(tmp_path)

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

    response = client.post(
        "/api/v1/interview/chat",
        json={"interview_id": "int-1", "messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 401
