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


# ── Canonical taxonomy payload used in tests ─────────────────────────────────

CANONICAL_TAXONOMY = {
    "taxonomy_id": "talenti_canonical_v2",
    "version": "2026.2",
    "signals": [
        {
            "signal_id": "ownership_accountability",
            "dimension": "ownership",
            "description": "Takes clear personal accountability for outcomes.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ownership"],
            "evidence_hints": ["I owned", "my decision", "I led"],
        },
        {
            "signal_id": "ownership_proactivity",
            "dimension": "ownership",
            "description": "Acts without being asked.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ownership"],
            "evidence_hints": ["without being asked", "I proposed"],
        },
        {
            "signal_id": "ownership_follow_through",
            "dimension": "ownership",
            "description": "Follows through to resolution.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ownership"],
            "evidence_hints": ["I fixed it", "I resolved"],
        },
        {
            "signal_id": "execution_delivery",
            "dimension": "execution",
            "description": "Delivers reliably.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["execution"],
            "evidence_hints": ["I delivered", "shipped", "launched"],
        },
        {
            "signal_id": "execution_pace_focus",
            "dimension": "execution",
            "description": "Maintains pace under pressure.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["execution"],
            "evidence_hints": ["prioritised", "cut scope"],
        },
        {
            "signal_id": "execution_measurable_outcome",
            "dimension": "execution",
            "description": "Cites measurable outcomes.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["execution"],
            "evidence_hints": ["measured", "improved by"],
        },
        {
            "signal_id": "challenge_constructive_pushback",
            "dimension": "challenge",
            "description": "Names disagreement constructively.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["challenge"],
            "evidence_hints": ["I pushed back", "I challenged", "I flagged"],
        },
        {
            "signal_id": "challenge_stakeholder_navigation",
            "dimension": "challenge",
            "description": "Navigates competing interests.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["challenge"],
            "evidence_hints": ["competing priorities", "I aligned"],
        },
        {
            "signal_id": "challenge_problem_naming",
            "dimension": "challenge",
            "description": "Names the real problem.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["challenge"],
            "evidence_hints": ["root cause", "the real issue"],
        },
        {
            "signal_id": "ambiguity_operates_without_direction",
            "dimension": "ambiguity",
            "description": "Creates structure without a brief.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ambiguity"],
            "evidence_hints": ["no clear brief", "figured it out"],
        },
        {
            "signal_id": "ambiguity_iterates_under_change",
            "dimension": "ambiguity",
            "description": "Adapts when requirements shift.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ambiguity"],
            "evidence_hints": ["pivoted", "requirements changed"],
        },
        {
            "signal_id": "ambiguity_tests_assumptions",
            "dimension": "ambiguity",
            "description": "Validates via experiments.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ambiguity"],
            "evidence_hints": ["hypothesis", "tested assumption"],
        },
        {
            "signal_id": "feedback_seeks_feedback",
            "dimension": "feedback",
            "description": "Actively seeks feedback.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["feedback"],
            "evidence_hints": ["I asked for feedback", "I sought input"],
        },
        {
            "signal_id": "feedback_acts_on_feedback",
            "dimension": "feedback",
            "description": "Applies feedback and changes behaviour.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["feedback"],
            "evidence_hints": ["after the feedback", "I took that on board"],
        },
        {
            "signal_id": "feedback_reflective_learning",
            "dimension": "feedback",
            "description": "Reflects honestly on failures.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["feedback"],
            "evidence_hints": ["reflected on", "learned from"],
        },
    ],
}

CANONICAL_OPERATING_ENV = {
    "control_vs_autonomy": "full_ownership",
    "outcome_vs_process": "results_first",
    "conflict_style": "healthy_debate",
    "decision_reality": "speed_led",
    "ambiguity_load": "ambiguous",
    "high_performance_archetype": "strong_owner",
    "dimension_weights": {
        "ownership": 0.25,
        "execution": 0.25,
        "challenge": 0.20,
        "ambiguity": 0.15,
        "feedback": 0.15,
    },
    "fatal_risks": [],
    "coachable_risks": [],
}


# ── Existing tests (updated for canonical dimensions) ─────────────────────────

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
        "operating_environment": CANONICAL_OPERATING_ENV,
        "taxonomy": CANONICAL_TAXONOMY,
    }

    org = Organisation(
        name="Test Org",
        values_framework=json.dumps(values_framework),
    )

    env, taxonomy = load_org_culture_context(org)
    assert taxonomy["taxonomy_id"] == "talenti_canonical_v2"
    assert env["control_vs_autonomy"] == "full_ownership"
    # All 5 canonical dimensions present in signals
    dimensions_in_taxonomy = {s["dimension"] for s in taxonomy["signals"]}
    assert dimensions_in_taxonomy == {"ownership", "execution", "challenge", "ambiguity", "feedback"}


def test_org_creation_seeds_canonical_values_framework() -> None:
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
        # Default taxonomy must be the canonical 5-dimension version
        assert values["taxonomy"]["taxonomy_id"] == "talenti_canonical_v2"
        dimension_weights = values["operating_environment"]["dimension_weights"]
        assert set(dimension_weights.keys()) == {"ownership", "execution", "challenge", "ambiguity", "feedback"}
        # Weights must sum to ~1.0
        assert abs(sum(dimension_weights.values()) - 1.0) < 0.01


def test_scoring_normalizes_model_score_ranges(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_client()
    from app.api import scoring as scoring_api
    from app.db import SessionLocal

    async def fake_predictions(*args, **kwargs):
        return (
            {
                "scores": {
                    "ownership": {"score": 80, "rationale": "Strong ownership signals.", "confidence": 0.82},
                    "execution": {"score": 65, "rationale": "Good delivery.", "confidence": 0.70},
                    "challenge": {"score": 50, "rationale": "Some pushback.", "confidence": 0.55},
                    "ambiguity": {"score": 70, "rationale": "Navigates ambiguity.", "confidence": 0.72},
                    "feedback": {"score": 60, "rationale": "Seeks feedback.", "confidence": 0.65},
                },
                "summary": "Strong fit overall.",
                "overall_alignment": "strong_fit",
                "overall_risk_level": "low",
                "recommendation": "proceed",
                "dimension_outcomes": {
                    "ownership": {"outcome": "pass", "required_pass": 60, "required_watch": 45, "gap": 20},
                    "execution": {"outcome": "pass", "required_pass": 60, "required_watch": 45, "gap": 5},
                    "challenge": {"outcome": "watch", "required_pass": 55, "required_watch": 40, "gap": -5},
                    "ambiguity": {"outcome": "pass", "required_pass": 65, "required_watch": 50, "gap": 5},
                    "feedback": {"outcome": "pass", "required_pass": 55, "required_watch": 40, "gap": 5},
                },
            },
            {
                "scores": {
                    "ownership": {"score": 0.78, "rationale": "Ownership evidence strong.", "confidence": 0.80},
                    "execution": {"score": 0.70, "rationale": "Delivery evidence present.", "confidence": 0.75},
                    "challenge": {"score": 0.45, "rationale": "Some challenge signals.", "confidence": 0.50},
                    "ambiguity": {"score": 0.65, "rationale": "Ambiguity handling.", "confidence": 0.68},
                    "feedback": {"score": 0.55, "rationale": "Feedback seeking observed.", "confidence": 0.60},
                },
                "summary": "Behavioural evidence score.",
            },
        )

    monkeypatch.setattr(scoring_api.ml_client, "get_combined_predictions", fake_predictions)

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    payload = {
        "interview_id": "int-2",
        "transcript": [{"speaker": "candidate", "content": "I take ownership and drive decisions."}],
        "operating_environment": CANONICAL_OPERATING_ENV,
        "taxonomy": CANONICAL_TAXONOMY,
    }

    response = client.post(
        "/api/v1/scoring/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    dimensions = {dim["name"]: dim["score"] for dim in data["dimensions"]}
    # Scores are averaged: (80 + 78) / 2 = 79, (65 + 70) / 2 = 67 (rounded)
    assert dimensions["ownership"] == 79
    assert dimensions["execution"] == 68  # (65+70)/2=67.5 → 68

    # Decision-dominant fields must be present
    assert data["overall_alignment"] == "strong_fit"
    assert data["overall_risk_level"] == "low"
    assert data["recommendation"] == "proceed"
    assert data["dimension_outcomes"] is not None
    assert "ownership" in data["dimension_outcomes"]
    assert data["dimension_outcomes"]["ownership"]["outcome"] == "pass"


def test_scoring_response_includes_confidence_per_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    """Confidence must be evidence-derived and present in each dimension of the response."""
    client = create_client()
    from app.api import scoring as scoring_api
    from app.db import SessionLocal

    async def fake_predictions(*args, **kwargs):
        return (
            {
                "scores": {
                    "ownership": {"score": 75, "rationale": "Strong ownership.", "confidence": 0.85},
                },
                "summary": "Test.",
                "overall_alignment": "strong_fit",
                "overall_risk_level": "low",
                "recommendation": "proceed",
                "dimension_outcomes": {
                    "ownership": {"outcome": "pass", "required_pass": 60, "required_watch": 45, "gap": 15},
                },
            },
            {
                "scores": {
                    "ownership": {"score": 0.70, "rationale": "Ownership signals.", "confidence": 0.75},
                },
                "summary": "Test.",
            },
        )

    monkeypatch.setattr(scoring_api.ml_client, "get_combined_predictions", fake_predictions)

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    payload = {
        "interview_id": "int-3",
        "transcript": [{"speaker": "candidate", "content": "I own outcomes."}],
        "operating_environment": CANONICAL_OPERATING_ENV,
        "taxonomy": CANONICAL_TAXONOMY,
    }

    response = client.post(
        "/api/v1/scoring/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    ownership = next(d for d in data["dimensions"] if d["name"] == "ownership")
    # Confidence must be a real value (average of 0.85 and 0.75 = 0.80)
    assert ownership["confidence"] is not None
    assert 0.0 < ownership["confidence"] <= 1.0


def test_scoring_dimension_outcome_fields_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """dimension_outcomes must carry outcome, required_pass, required_watch, and gap."""
    client = create_client()
    from app.api import scoring as scoring_api
    from app.db import SessionLocal

    async def fake_predictions(*args, **kwargs):
        return (
            {
                "scores": {
                    "ownership": {"score": 40, "rationale": "Low ownership.", "confidence": 0.45},
                },
                "summary": "Weak evidence.",
                "overall_alignment": "weak_fit",
                "overall_risk_level": "high",
                "recommendation": "reject",
                "dimension_outcomes": {
                    "ownership": {"outcome": "risk", "required_pass": 60, "required_watch": 45, "gap": -20},
                },
            },
            {
                "scores": {
                    "ownership": {"score": 0.35, "rationale": "Weak signals.", "confidence": 0.40},
                },
                "summary": "Low evidence.",
            },
        )

    monkeypatch.setattr(scoring_api.ml_client, "get_combined_predictions", fake_predictions)

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    payload = {
        "interview_id": "int-4",
        "transcript": [{"speaker": "candidate", "content": "I just do what I am told."}],
        "operating_environment": CANONICAL_OPERATING_ENV,
        "taxonomy": CANONICAL_TAXONOMY,
    }

    response = client.post(
        "/api/v1/scoring/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "reject"
    assert data["overall_risk_level"] == "high"
    outcome = data["dimension_outcomes"]["ownership"]
    assert outcome["outcome"] == "risk"
    assert outcome["required_pass"] == 60
    assert outcome["gap"] == -20


def test_scoring_uses_model2_scores_when_model1_returns_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    When model-service-1 returns {error, fallback: True}, _merge_scores should
    still succeed using model-service-2 scores alone. The response must not be
    500 and must include dimensions from service2.
    """
    client = create_client()
    from app.api import scoring as scoring_api
    from app.db import SessionLocal

    async def fake_predictions(*args, **kwargs):
        return (
            # model-service-1 failed — returns fallback sentinel
            {"error": "model-service-1 timeout", "fallback": True},
            # model-service-2 returns normal scores
            {
                "scores": {
                    "ownership": {"score": 0.72, "rationale": "Strong ownership.", "confidence": 0.78},
                    "execution": {"score": 0.65, "rationale": "Delivery signals.", "confidence": 0.70},
                    "challenge": {"score": 0.55, "rationale": "Challenge evidence.", "confidence": 0.60},
                    "ambiguity": {"score": 0.60, "rationale": "Ambiguity handling.", "confidence": 0.65},
                    "feedback": {"score": 0.50, "rationale": "Feedback seeking.", "confidence": 0.55},
                },
                "summary": "Service2-only scoring.",
            },
        )

    monkeypatch.setattr(scoring_api.ml_client, "get_combined_predictions", fake_predictions)

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    payload = {
        "interview_id": "int-fallback-1",
        "transcript": [{"speaker": "candidate", "content": "I owned the outcome and delivered."}],
        "operating_environment": CANONICAL_OPERATING_ENV,
        "taxonomy": CANONICAL_TAXONOMY,
    }

    response = client.post(
        "/api/v1/scoring/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Must have dimensions from service2
    dim_names = {d["name"] for d in data["dimensions"]}
    assert "ownership" in dim_names
    assert "execution" in dim_names
    # overall_score must be a valid number
    assert isinstance(data["overall_score"], (int, float))
    assert data["overall_score"] > 0


def test_scoring_returns_500_when_both_services_return_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    When both model services fail, _merge_scores raises InterviewScoringError
    because no scores are returned. The API must return 500.
    """
    client = create_client()
    from app.api import scoring as scoring_api
    from app.db import SessionLocal

    async def fake_predictions(*args, **kwargs):
        return (
            {"error": "model-service-1 timeout", "fallback": True},
            {"error": "model-service-2 connection refused", "fallback": True},
        )

    monkeypatch.setattr(scoring_api.ml_client, "get_combined_predictions", fake_predictions)

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    payload = {
        "interview_id": "int-fallback-2",
        "transcript": [{"speaker": "candidate", "content": "I owned the outcome."}],
        "operating_environment": CANONICAL_OPERATING_ENV,
        "taxonomy": CANONICAL_TAXONOMY,
    }

    response = client.post(
        "/api/v1/scoring/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 500


def test_scoring_uses_model1_decision_fields_when_model2_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    When model-service-2 fails but model-service-1 succeeds, decision-dominant
    fields (recommendation, alignment, risk) must still be present in the response.
    """
    client = create_client()
    from app.api import scoring as scoring_api
    from app.db import SessionLocal

    async def fake_predictions(*args, **kwargs):
        return (
            {
                "scores": {
                    "ownership": {"score": 78, "rationale": "Ownership.", "confidence": 0.82},
                    "execution": {"score": 72, "rationale": "Execution.", "confidence": 0.75},
                    "challenge": {"score": 68, "rationale": "Challenge.", "confidence": 0.70},
                    "ambiguity": {"score": 65, "rationale": "Ambiguity.", "confidence": 0.68},
                    "feedback": {"score": 60, "rationale": "Feedback.", "confidence": 0.65},
                },
                "summary": "Service1 only.",
                "overall_alignment": "strong_fit",
                "overall_risk_level": "low",
                "recommendation": "proceed",
                "dimension_outcomes": {
                    dim: {"outcome": "pass", "required_pass": 55, "required_watch": 40, "gap": 10}
                    for dim in ["ownership", "execution", "challenge", "ambiguity", "feedback"]
                },
            },
            # model-service-2 failed
            {"error": "model-service-2 unavailable", "fallback": True},
        )

    monkeypatch.setattr(scoring_api.ml_client, "get_combined_predictions", fake_predictions)

    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    payload = {
        "interview_id": "int-fallback-3",
        "transcript": [{"speaker": "candidate", "content": "I drove the whole project."}],
        "operating_environment": CANONICAL_OPERATING_ENV,
        "taxonomy": CANONICAL_TAXONOMY,
    }

    response = client.post(
        "/api/v1/scoring/analyze",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Decision-dominant fields from service1 must pass through
    assert data["recommendation"] == "proceed"
    assert data["overall_alignment"] == "strong_fit"
    assert data["overall_risk_level"] == "low"
    assert data["dimension_outcomes"] is not None
