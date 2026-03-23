import importlib
import json
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


def _create_user_and_token(db):
    from datetime import datetime

    from app.core.security import create_access_token, hash_password
    from app.models import User

    user = User(
        email="tester@example.com",
        password_hash=hash_password("password"),
        full_name="Test User",
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return user, token


def test_requires_org_environment_for_fit_scoring() -> None:
    client = create_client()
    client.get("/health")
    from app.db import SessionLocal

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    response = client.post(
        "/api/v1/scoring/analyze",
        json={
            "interview_id": "int-1",
            "transcript": [{"speaker": "candidate", "content": "Test response."}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "organisation" in response.json().get("detail", "").lower()


def test_taxonomy_loaded_from_org_context() -> None:
    create_client()
    from app.models import Organisation
    from app.services.culture_fit import load_org_culture_context

    values_framework = {
        "operating_environment": {
            "control_vs_autonomy": "full_ownership",
            "outcome_vs_process": "results_first",
            "conflict_style": "healthy_debate",
            "decision_reality": "speed_led",
            "ambiguity_load": "ambiguous",
            "high_performance_archetype": "strong_owner",
            "dimension_weights": {"autonomy": 0.7, "decision_style": 0.3},
            "fatal_risks": [],
            "coachable_risks": [],
        },
        "taxonomy": {
            "taxonomy_id": "org_taxonomy_v1",
            "version": "2026.02",
            "signals": [
                {
                    "signal_id": "bias_to_action",
                    "dimension": "decision_style",
                    "description": "Acts quickly with trade-offs.",
                    "score_map": {
                        "strong": 3,
                        "moderate": 2,
                        "weak": 0,
                        "not_observed": 0,
                    },
                    "evidence_hints": ["decide", "trade-off"],
                }
            ],
        },
    }

    org = Organisation(
        name="Test Org",
        values_framework=json.dumps(values_framework),
    )

    env, taxonomy = load_org_culture_context(org)
    assert taxonomy["taxonomy_id"] == "org_taxonomy_v1"
    assert env["control_vs_autonomy"] == "full_ownership"


def test_org_creation_seeds_default_values_framework() -> None:
    client = create_client()
    from app.db import SessionLocal
    from app.models import Organisation

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    response = client.post(
        "/api/orgs",
        json={"name": "Default Values Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    org_id = response.json()["id"]

    with SessionLocal() as db:
        org = db.get(Organisation, org_id)
        assert org is not None
        assert org.values_framework is not None
        values = json.loads(org.values_framework)
        assert "operating_environment" in values
        assert "taxonomy" in values


def test_scoring_normalizes_model_score_ranges(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_client()
    from app.api import scoring as scoring_api
    from app.db import SessionLocal

    async def fake_predictions(*args, **kwargs):
        return (
            {
                "scores": {
                    "autonomy": {
                        "score": 80,
                        "rationale": "Culture model score.",
                    }
                },
                "summary": "Culture model summary.",
            },
            {
                "scores": {
                    "autonomy": {
                        "score": 0.82,
                        "rationale": "Skillset model normalized score.",
                    }
                },
                "summary": "Skillset model summary.",
            },
        )

    monkeypatch.setattr(scoring_api.ml_client, "get_combined_predictions", fake_predictions)

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    payload = {
        "interview_id": "int-2",
        "transcript": [{"speaker": "candidate", "content": "I take ownership and drive decisions."}],
        "operating_environment": {
            "control_vs_autonomy": "full_ownership",
            "outcome_vs_process": "results_first",
            "conflict_style": "healthy_debate",
            "decision_reality": "speed_led",
            "ambiguity_load": "ambiguous",
            "high_performance_archetype": "strong_owner",
            "dimension_weights": {"autonomy": 1.0},
            "fatal_risks": [],
            "coachable_risks": [],
        },
        "taxonomy": {
            "taxonomy_id": "test_taxonomy",
            "version": "1.0.0",
            "signals": [
                {
                    "signal_id": "ownership_signal",
                    "dimension": "autonomy",
                    "description": "Ownership behavior in responses.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 0, "not_observed": 0},
                    "evidence_hints": ["ownership", "own"],
                }
            ],
        },
    }

    response = client.post(
        "/api/v1/scoring/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    dimensions = {dim["name"]: dim["score"] for dim in data["dimensions"]}
    assert dimensions["autonomy"] == 81


def test_scoring_disabled_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_SCORING", "false")
    client = create_client()
    client.get("/health")
    from app.db import SessionLocal

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    response = client.post(
        "/api/v1/scoring/analyze",
        json={
            "interview_id": "int-1",
            "transcript": [{"speaker": "candidate", "content": "Test response."}],
            "operating_environment": {
                "control_vs_autonomy": "full_ownership",
                "outcome_vs_process": "results_first",
                "conflict_style": "healthy_debate",
                "decision_reality": "speed_led",
                "ambiguity_load": "ambiguous",
                "high_performance_archetype": "strong_owner",
                "dimension_weights": {"autonomy": 1.0},
                "fatal_risks": [],
                "coachable_risks": [],
            },
            "taxonomy": {
                "taxonomy_id": "test_taxonomy",
                "version": "1.0.0",
                "signals": [],
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "disabled" in response.json().get("detail", "").lower()
