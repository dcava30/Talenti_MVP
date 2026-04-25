from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator

import pytest
from conftest import backend_root, clear_app_modules, prepare_test_environment
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_shortlist_app(*, quarantine_enabled: bool):
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    prepare_test_environment()
    import os

    os.environ["TDS_RANKING_AND_SHORTLIST_QUARANTINE_ENABLED"] = "true" if quarantine_enabled else "false"
    clear_app_modules()

    import app.api.deps as deps
    import app.api.shortlist as shortlist
    import app.core.config as config

    importlib.reload(config)
    importlib.reload(deps)
    importlib.reload(shortlist)

    app = FastAPI()
    app.include_router(shortlist.router)

    def _fake_db() -> Iterator[None]:
        yield None

    app.dependency_overrides[deps.get_db] = _fake_db
    app.dependency_overrides[deps.get_current_user] = lambda: object()
    return app, shortlist


def test_shortlist_generation_preserves_legacy_ranked_response_by_default() -> None:
    app, _ = _load_shortlist_app(quarantine_enabled=False)
    client = TestClient(app)

    response = client.post(
        "/api/v1/shortlist/generate",
        json={
            "job_role_id": "role-123",
            "candidates": [
                {"application_id": "app-low", "score": 12.0},
                {"application_id": "app-high", "score": 88.5},
                {"application_id": "app-mid", "score": 40.0},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_role_id": "role-123",
        "ranked": [
            {"application_id": "app-high", "score": 88.5},
            {"application_id": "app-mid", "score": 40.0},
            {"application_id": "app-low", "score": 12.0},
        ],
    }


def test_shortlist_generation_is_disabled_when_quarantine_enabled() -> None:
    app, _ = _load_shortlist_app(quarantine_enabled=True)
    client = TestClient(app)

    response = client.post(
        "/api/v1/shortlist/generate",
        json={
            "job_role_id": "role-123",
            "candidates": [
                {"application_id": "app-1", "score": 80.0},
                {"application_id": "app-2", "score": 20.0},
            ],
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Shortlist generation is disabled under the TDS decisioning model."
    }


def test_shortlist_quarantine_returns_no_ranked_fields() -> None:
    app, _ = _load_shortlist_app(quarantine_enabled=True)
    client = TestClient(app)

    response = client.post(
        "/api/v1/shortlist/generate",
        json={
            "job_role_id": "role-123",
            "candidates": [
                {"application_id": "app-1", "score": 80.0},
            ],
        },
    )

    assert response.status_code == 403
    payload = response.json()

    for forbidden_key in ("rank", "match_score", "score", "best_candidate", "shortlist_position"):
        assert forbidden_key not in payload


def test_shortlist_quarantine_does_not_call_ranking_logic(monkeypatch: pytest.MonkeyPatch) -> None:
    app, shortlist = _load_shortlist_app(quarantine_enabled=True)
    client = TestClient(app)

    def _fail_if_called(_payload):
        raise AssertionError("ranking should not run while quarantine is enabled")

    monkeypatch.setattr(shortlist, "_rank_candidates", _fail_if_called)

    response = client.post(
        "/api/v1/shortlist/generate",
        json={
            "job_role_id": "role-123",
            "candidates": [
                {"application_id": "app-low", "score": 10.0},
                {"application_id": "app-high", "score": 90.0},
            ],
        },
    )

    assert response.status_code == 403
