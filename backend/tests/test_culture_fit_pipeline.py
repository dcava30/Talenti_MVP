import importlib
import json
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
    from app.db import Base, engine
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    return TestClient(main.app)


def _create_user_and_token(db):
    from datetime import datetime

    from app.core.security import create_access_token, hash_password
    from app.db import Base, engine
    from app.models import User

    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
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


def test_requires_org_environment_for_fit_scoring(tmp_path: Path) -> None:
    client = create_client(tmp_path)
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


def test_taxonomy_loaded_from_org_context(tmp_path: Path) -> None:
    create_client(tmp_path)
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


def test_org_creation_seeds_default_values_framework(tmp_path: Path) -> None:
    client = create_client(tmp_path)
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
