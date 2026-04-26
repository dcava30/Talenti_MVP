from __future__ import annotations

import importlib
import json
import socket
import sys
from datetime import datetime, timedelta
from typing import Any

import pytest
from conftest import (
    backend_root,
    clear_app_modules,
    get_test_database_url,
    prepare_test_environment,
    reset_database_with_migrations,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import make_url


CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]
FORBIDDEN_RESPONSE_KEYS = {
    "skills_score",
    "skills_outcome",
    "skills_summary_id",
    "skills_assessment_summary",
    "match_score",
    "ranking",
    "rank",
    "shortlist_position",
    "best_candidate",
    "overall_score",
    "override_score",
    "override_ai",
    "override_recommendation",
    "final_decision_override",
}
FORBIDDEN_RESPONSE_STRINGS = {
    "override_score",
    "override_ai",
    "override_recommendation",
    "final_decision_override",
}


def _require_postgres_test_database() -> str:
    database_url = get_test_database_url()
    parsed = make_url(database_url)
    host = parsed.host or "localhost"
    port = parsed.port or 5432

    try:
        with socket.create_connection((host, port), timeout=1):
            return database_url
    except OSError:
        pytest.skip(f"Postgres test database is unavailable at {host}:{port}")


def _load_modules(*, human_review_api_enabled: bool):
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    database_url = _require_postgres_test_database()
    prepare_test_environment()
    import os

    os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_HUMAN_REVIEW_API_ENABLED"] = "true" if human_review_api_enabled else "false"
    reset_database_with_migrations(database_url)
    clear_app_modules()

    import app.core.config as config
    import app.core.security as security
    import app.db as db
    import app.main as main
    import app.models as models
    import app.services.decision_layer as decision_layer
    import app.services.decision_persistence as decision_persistence
    import app.services.ml_client as ml_client
    import app.services.skills_assessment_summary as skills_assessment_summary

    importlib.reload(config)
    importlib.reload(security)
    importlib.reload(db)
    importlib.reload(models)
    importlib.reload(decision_layer)
    importlib.reload(decision_persistence)
    importlib.reload(ml_client)
    importlib.reload(skills_assessment_summary)
    importlib.reload(main)

    return db, models, main, security, decision_layer, decision_persistence, skills_assessment_summary, ml_client


def _dimension(
    score: int = 1,
    confidence: str = "HIGH",
    *,
    valid_signals: list[str] | None = None,
    invalid_signals: list[str] | None = None,
    conflict_flags: list[str] | None = None,
) -> dict[str, object]:
    return {
        "score_internal": score,
        "confidence": confidence,
        "evidence_summary": "Observed behavioural evidence.",
        "rationale": "Deterministic behavioural rationale.",
        "valid_signals": list(["repeatable_signal"] if valid_signals is None else valid_signals),
        "invalid_signals": list([] if invalid_signals is None else invalid_signals),
        "conflict_flags": list([] if conflict_flags is None else conflict_flags),
    }


def _decision_payload(
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    dimensions: dict[str, dict[str, object] | None] | None = None,
) -> dict[str, object]:
    evidence = {dimension: _dimension() for dimension in CANONICAL_DIMENSIONS}
    for dimension, override in (dimensions or {}).items():
        if override is None:
            evidence.pop(dimension, None)
            continue
        merged = dict(evidence.get(dimension, _dimension()))
        merged.update(override)
        evidence[dimension] = merged

    return {
        "interview_id": interview_id,
        "candidate_id": candidate_id,
        "role_id": role_id,
        "organisation_id": organisation_id,
        "environment_profile": {
            "control_vs_autonomy": "full_ownership",
            "outcome_vs_process": "results_first",
        },
        "environment_confidence": "HIGH",
        "behavioural_dimension_evidence": [
            {"dimension": dimension, **evidence[dimension]}
            for dimension in CANONICAL_DIMENSIONS
            if dimension in evidence
        ],
        "critical_dimensions": ["ownership", "execution"],
        "minimum_dimensions": list(CANONICAL_DIMENSIONS),
        "priority_dimensions": ["challenge"],
        "rule_version": "tds-phase11-human-review-v1",
        "policy_version": "mvp1-behaviour-decides-v1",
    }


def _create_user(session, models, security, *, email: str, full_name: str):
    user = models.User(
        email=email,
        password_hash=security.hash_password("password"),
        full_name=full_name,
        created_at=datetime.utcnow(),
    )
    session.add(user)
    session.flush()
    return user


def _collect_keys_and_strings(value: Any) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    string_values: list[str] = []

    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            nested_keys, nested_values = _collect_keys_and_strings(nested)
            keys.update(nested_keys)
            string_values.extend(nested_values)
        return keys, string_values

    if isinstance(value, list):
        for nested in value:
            nested_keys, nested_values = _collect_keys_and_strings(nested)
            keys.update(nested_keys)
            string_values.extend(nested_values)
        return keys, string_values

    if isinstance(value, str):
        string_values.append(value)

    return keys, string_values


def _assert_safe_human_review_response(payload: Any) -> None:
    keys, string_values = _collect_keys_and_strings(payload)
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(keys)
    assert FORBIDDEN_RESPONSE_STRINGS.isdisjoint(set(string_values))


def _seed_human_review_fixture(session, models, security, decision_layer, decision_persistence, skills_service):
    admin_user = _create_user(
        session, models, security, email="human-review-admin@example.com", full_name="Human Review Admin"
    )
    owner_user = _create_user(
        session, models, security, email="human-review-owner@example.com", full_name="Human Review Owner"
    )
    member_user = _create_user(
        session, models, security, email="human-review-member@example.com", full_name="Human Review Member"
    )
    other_admin_user = _create_user(
        session,
        models,
        security,
        email="human-review-other-admin@example.com",
        full_name="Human Review Other Admin",
    )
    candidate_user = _create_user(
        session, models, security, email="human-review-candidate@example.com", full_name="Human Review Candidate"
    )

    organisation = models.Organisation(name="Talenti Human Review Org")
    other_organisation = models.Organisation(name="Talenti Human Review Other Org")
    session.add_all([organisation, other_organisation])
    session.flush()

    session.add_all(
        [
            models.OrgUser(organisation_id=organisation.id, user_id=admin_user.id, role="admin"),
            models.OrgUser(organisation_id=organisation.id, user_id=owner_user.id, role="owner"),
            models.OrgUser(organisation_id=organisation.id, user_id=member_user.id, role="member"),
            models.OrgUser(organisation_id=other_organisation.id, user_id=other_admin_user.id, role="admin"),
        ]
    )

    candidate = models.CandidateProfile(
        user_id=candidate_user.id,
        first_name="Jamie",
        last_name="Candidate",
        email="human-review-candidate@example.com",
    )
    session.add(candidate)
    session.flush()

    role = models.JobRole(
        organisation_id=organisation.id,
        title="Account Executive",
        description="Own revenue outcomes.",
        status="active",
    )
    other_role = models.JobRole(
        organisation_id=other_organisation.id,
        title="Customer Success Manager",
        description="Own customer outcomes.",
        status="active",
    )
    session.add_all([role, other_role])
    session.flush()

    application = models.Application(
        job_role_id=role.id,
        candidate_profile_id=candidate.id,
        status="submitted",
    )
    other_application = models.Application(
        job_role_id=other_role.id,
        candidate_profile_id=candidate.id,
        status="submitted",
    )
    session.add_all([application, other_application])
    session.flush()

    interview = models.Interview(
        application_id=application.id,
        status="completed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    other_interview = models.Interview(
        application_id=other_application.id,
        status="completed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    environment_input = models.OrgEnvironmentInput(
        organisation_id=organisation.id,
        raw_answers='{"q1_direction_style":"we_set_direction_and_people_own_it"}',
        signals_json='[{"variable":"control_vs_autonomy","value":"full_ownership"}]',
        derived_environment='{"control_vs_autonomy":"full_ownership","outcome_vs_process":"results_first"}',
        submitted_by=admin_user.id,
    )
    session.add_all([interview, other_interview, environment_input])
    session.flush()

    primary_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=interview.id,
            candidate_id=candidate.id,
            role_id=role.id,
            organisation_id=organisation.id,
            dimensions={"execution": _dimension(score=-2, confidence="MEDIUM")},
        )
    )
    other_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=other_interview.id,
            candidate_id=candidate.id,
            role_id=other_role.id,
            organisation_id=other_organisation.id,
        )
    )

    decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=primary_result,
        interview_id=interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        org_environment_input_id=environment_input.id,
        environment_profile={"control_vs_autonomy": "full_ownership"},
        actor_user_id=admin_user.id,
    )
    decision.created_at = datetime.utcnow() - timedelta(minutes=10)
    decision.updated_at = decision.created_at
    assert decision.decision_state == "DO_NOT_PROCEED"

    other_decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=other_result,
        interview_id=other_interview.id,
        candidate_id=candidate.id,
        role_id=other_role.id,
        organisation_id=other_organisation.id,
        environment_profile={"control_vs_autonomy": "execution_led"},
        actor_user_id=other_admin_user.id,
    )
    other_decision.created_at = datetime.utcnow() - timedelta(minutes=5)
    other_decision.updated_at = other_decision.created_at
    session.flush()

    interview_score = models.InterviewScore(
        interview_id=interview.id,
        culture_fit_score=48,
        skills_score=91,
        skills_outcome="PASS",
        overall_alignment="mixed_fit",
        overall_risk_level="medium",
        recommendation="review",
        summary="Legacy scoring response retained for non-regression checks.",
        service1_raw=json.dumps({"overall_score": 48}),
        service2_raw=json.dumps({"match_score": 91, "ranking": 2, "skills_outcome": "PASS"}),
        created_at=datetime.utcnow() - timedelta(minutes=20),
    )
    score_dimension = models.ScoreDimension(
        interview_id=interview.id,
        name="ownership",
        score=72,
        confidence=0.74,
        outcome="watch",
        required_pass=75,
        required_watch=60,
        gap=-3,
        matched_signals='["ownership_signal"]',
        source="service1",
        rationale="Legacy score dimension retained for regression checks.",
    )
    session.add_all([interview_score, score_dimension])

    skills_summary = skills_service.create_skills_assessment_summary(
        session,
        interview_id=interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        observed_competencies=["forecasting", "discovery"],
        competency_coverage={"required": 4, "observed": 2},
        skill_gaps=["meddic"],
        evidence_strength="MEDIUM",
        confidence="MEDIUM",
        source_references=[{"service": "model-service-2", "match_score": 91}],
        human_readable_summary="Skills evidence remains separate from behavioural decisions.",
        requires_human_review=True,
        model_version="skills-ms2-v1",
    )

    session.commit()

    return {
        "organisation_id": organisation.id,
        "other_organisation_id": other_organisation.id,
        "role_id": role.id,
        "candidate_id": candidate.id,
        "interview_id": interview.id,
        "decision_id": decision.id,
        "other_decision_id": other_decision.id,
        "decision_state": decision.decision_state,
        "decision_rationale": decision.rationale,
        "interview_score_id": interview_score.id,
        "score_dimension_id": score_dimension.id,
        "skills_summary_id": skills_summary.id,
        "admin_user_id": admin_user.id,
        "owner_user_id": owner_user.id,
        "admin_token": security.create_access_token(admin_user.id),
        "owner_token": security.create_access_token(owner_user.id),
        "member_token": security.create_access_token(member_user.id),
        "other_admin_token": security.create_access_token(other_admin_user.id),
    }


@pytest.mark.parametrize("method", ["get", "post"])
def test_human_review_api_returns_404_when_feature_flag_disabled(method: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = _load_modules(
        human_review_api_enabled=False
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    url = f"/api/v1/decisions/{seeded['decision_id']}/human-review"
    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}
    if method == "get":
        response = client.get(url, headers=headers)
    else:
        response = client.post(
            url,
            headers=headers,
            json={
                "action_type": "HUMAN_REVIEW",
                "review_outcome": "ACKNOWLEDGED",
                "reason": "Human review recorded.",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Decision human review API is not available."


def test_human_review_api_requires_authentication() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = _load_modules(
        human_review_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.post(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        json={
            "action_type": "HUMAN_REVIEW",
            "review_outcome": "ACKNOWLEDGED",
            "reason": "Human review recorded.",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing token"


@pytest.mark.parametrize("token_key", ["member_token", "other_admin_token"])
def test_human_review_api_rejects_non_admin_or_wrong_org_access(token_key: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = _load_modules(
        human_review_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.post(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
        json={
            "action_type": "HUMAN_REVIEW",
            "review_outcome": "ACKNOWLEDGED",
            "reason": "Human review recorded.",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only organisation admins can access this resource."


@pytest.mark.parametrize("token_key", ["admin_token", "owner_token"])
def test_human_review_api_allows_admin_and_owner_create_and_list(token_key: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = _load_modules(
        human_review_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    create_response = client.post(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
        json={
            "action_type": "EXCEPTION_RECORDED",
            "review_outcome": "PROCEED_WITH_HUMAN_EXCEPTION",
            "reason": "Recruiter recorded additional context without replacing the system decision.",
            "notes": "Candidate has verified context from a reference check.",
            "display_delta": {"badge": "Human exception recorded"},
        },
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()
    expected_reviewer_id = seeded["admin_user_id"] if token_key == "admin_token" else seeded["owner_user_id"]
    assert created_payload["decision_id"] == seeded["decision_id"]
    assert created_payload["original_decision_state"] == seeded["decision_state"]
    assert created_payload["action_type"] == "EXCEPTION_RECORDED"
    assert created_payload["review_outcome"] == "PROCEED_WITH_HUMAN_EXCEPTION"
    assert created_payload["notes"] == "Candidate has verified context from a reference check."
    assert created_payload["reviewed_by"] == expected_reviewer_id
    assert created_payload["audit_event_id"] is not None
    _assert_safe_human_review_response(created_payload)

    list_response = client.get(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload) == 1
    assert list_payload[0]["human_review_action_id"] == created_payload["human_review_action_id"]
    _assert_safe_human_review_response(list_payload)


def test_human_review_api_validates_reason_action_type_and_review_outcome() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = _load_modules(
        human_review_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}
    url = f"/api/v1/decisions/{seeded['decision_id']}/human-review"

    blank_reason = client.post(
        url,
        headers=headers,
        json={
            "action_type": "HUMAN_REVIEW",
            "review_outcome": "ACKNOWLEDGED",
            "reason": "   ",
        },
    )
    bad_action_type = client.post(
        url,
        headers=headers,
        json={
            "action_type": "REQUEST_FOLLOW_UP",
            "review_outcome": "ACKNOWLEDGED",
            "reason": "Human review recorded.",
        },
    )
    bad_review_outcome = client.post(
        url,
        headers=headers,
        json={
            "action_type": "HUMAN_REVIEW",
            "review_outcome": "FOLLOW_UP_REQUIRED",
            "reason": "Human review recorded.",
        },
    )

    assert blank_reason.status_code == 422
    assert bad_action_type.status_code == 422
    assert bad_review_outcome.status_code == 422


def test_human_review_api_preserves_original_decision_and_persists_audit_trail() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = _load_modules(
        human_review_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        decision = session.get(models.DecisionOutcome, seeded["decision_id"])
        assert decision is not None
        before_updated_at = decision.updated_at

    response = client.post(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
        json={
            "action_type": "DISAGREEMENT_RECORDED",
            "review_outcome": "PROCEED_WITH_HUMAN_EXCEPTION",
            "reason": "The recruiter wants to proceed with a human exception while preserving the system outcome.",
            "notes": "Commercial context supports a supervised next step.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_decision_state"] == seeded["decision_state"]

    with db.SessionLocal() as session:
        decision = session.get(models.DecisionOutcome, seeded["decision_id"])
        assert decision is not None
        assert decision.decision_state == seeded["decision_state"]
        assert decision.rationale == seeded["decision_rationale"]
        assert decision.updated_at == before_updated_at

        review_actions = list(
            session.execute(
                select(models.HumanReviewAction).where(models.HumanReviewAction.decision_id == seeded["decision_id"])
            ).scalars()
        )
        assert len(review_actions) == 1
        assert review_actions[0].action_type == "DISAGREEMENT_RECORDED"
        assert review_actions[0].review_outcome == "PROCEED_WITH_HUMAN_EXCEPTION"

        review_events = list(
            session.execute(
                select(models.DecisionAuditTrail)
                .where(models.DecisionAuditTrail.decision_id == seeded["decision_id"])
                .where(models.DecisionAuditTrail.event_type == "human_review_action_created")
            ).scalars()
        )
        assert len(review_events) == 1
        assert review_events[0].actor_type == "user"
        payload_json = json.loads(review_events[0].event_payload_json)
        assert payload_json["action_type"] == "DISAGREEMENT_RECORDED"
        assert payload_json["review_outcome"] == "PROCEED_WITH_HUMAN_EXCEPTION"
        assert payload_json["reason"] == (
            "The recruiter wants to proceed with a human exception while preserving the system outcome."
        )
        assert payload_json["original_decision_state"] == seeded["decision_state"]


def test_human_review_list_is_deterministic_and_excludes_skills_and_ranking_fields() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = _load_modules(
        human_review_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}
    url = f"/api/v1/decisions/{seeded['decision_id']}/human-review"
    first_response = client.post(
        url,
        headers=headers,
        json={
            "action_type": "HUMAN_REVIEW",
            "review_outcome": "HOLD_FOR_FURTHER_REVIEW",
            "reason": "Waiting for additional references.",
        },
    )
    second_response = client.post(
        url,
        headers=headers,
        json={
            "action_type": "ADDITIONAL_CONTEXT",
            "review_outcome": "ACKNOWLEDGED",
            "reason": "Added context from the hiring manager.",
            "display_delta": {"label": "Context added"},
        },
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_id = first_response.json()["human_review_action_id"]
    second_id = second_response.json()["human_review_action_id"]

    with db.SessionLocal() as session:
        first_action = session.get(models.HumanReviewAction, first_id)
        second_action = session.get(models.HumanReviewAction, second_id)
        assert first_action is not None
        assert second_action is not None
        first_action.created_at = datetime.utcnow() - timedelta(minutes=2)
        second_action.created_at = datetime.utcnow() - timedelta(minutes=1)
        session.commit()

    list_response = client.get(url, headers=headers)

    assert list_response.status_code == 200
    payload = list_response.json()
    assert [item["human_review_action_id"] for item in payload] == [first_id, second_id]
    assert all("skills_assessment_summary" not in item for item in payload)
    assert all("ranking" not in item for item in payload)
    _assert_safe_human_review_response(payload)


def test_human_review_create_has_no_side_effects_and_does_not_call_decision_layer_or_model_services(monkeypatch) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, ml_client = _load_modules(
        human_review_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        before_decision = session.get(models.DecisionOutcome, seeded["decision_id"])
        assert before_decision is not None
        before_decision_updated_at = before_decision.updated_at
        before_decision_state = before_decision.decision_state
        before_decision_rationale = before_decision.rationale
        before_interview_score_ids = [item.id for item in session.execute(select(models.InterviewScore)).scalars()]
        before_score_dimension_ids = [item.id for item in session.execute(select(models.ScoreDimension)).scalars()]
        before_skills_summary_ids = [item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()]

    def _unexpected_decision_layer_call(*args, **kwargs):
        raise AssertionError("Decision Layer should not be called by human review API")

    async def _unexpected_model_service_call(*args, **kwargs):
        raise AssertionError("Model services should not be called by human review API")

    monkeypatch.setattr(decision_layer, "evaluate_behavioural_decision", _unexpected_decision_layer_call)
    monkeypatch.setattr(ml_client.ml_client, "get_combined_predictions", _unexpected_model_service_call)

    response = client.post(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
        json={
            "action_type": "EXCEPTION_RECORDED",
            "review_outcome": "NO_ACTION_TAKEN",
            "reason": "Recorded and acknowledged without changing the system decision.",
        },
    )

    assert response.status_code == 201

    with db.SessionLocal() as session:
        after_decision = session.get(models.DecisionOutcome, seeded["decision_id"])
        assert after_decision is not None
        assert after_decision.decision_state == before_decision_state
        assert after_decision.rationale == before_decision_rationale
        assert after_decision.updated_at == before_decision_updated_at
        after_interview_score_ids = [item.id for item in session.execute(select(models.InterviewScore)).scalars()]
        after_score_dimension_ids = [item.id for item in session.execute(select(models.ScoreDimension)).scalars()]
        after_skills_summary_ids = [item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()]

    assert after_interview_score_ids == before_interview_score_ids
    assert after_score_dimension_ids == before_score_dimension_ids
    assert after_skills_summary_ids == before_skills_summary_ids
