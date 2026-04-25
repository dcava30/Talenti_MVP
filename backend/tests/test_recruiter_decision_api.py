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
    "audit_trace",
}
FORBIDDEN_RESPONSE_STRING_VALUES = {"PASS", "REVIEW", "FAIL"}


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


def _load_modules(*, recruiter_api_enabled: bool):
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    database_url = _require_postgres_test_database()
    prepare_test_environment()
    import os

    os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_RECRUITER_DECISION_API_ENABLED"] = "true" if recruiter_api_enabled else "false"
    reset_database_with_migrations(database_url)
    clear_app_modules()

    import app.core.config as config
    import app.core.security as security
    import app.db as db
    import app.main as main
    import app.models as models
    import app.services.decision_layer as decision_layer
    import app.services.decision_persistence as decision_persistence
    import app.services.skills_assessment_summary as skills_assessment_summary

    importlib.reload(config)
    importlib.reload(security)
    importlib.reload(db)
    importlib.reload(models)
    importlib.reload(decision_layer)
    importlib.reload(decision_persistence)
    importlib.reload(skills_assessment_summary)
    importlib.reload(main)

    return db, models, main, security, decision_layer, decision_persistence, skills_assessment_summary


def _dimension(
    score: int = 1,
    confidence: str = "HIGH",
    *,
    valid_signals: list[str] | None = None,
    invalid_signals: list[str] | None = None,
    conflict_flags: list[str] | None = None,
    evidence_summary: str | dict[str, object] | list[object] = "Observed behavioural evidence.",
) -> dict[str, object]:
    return {
        "score_internal": score,
        "confidence": confidence,
        "evidence_summary": evidence_summary,
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
        "rule_version": "tds-phase9-read-model-v1",
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


def _collect_keys_and_string_values(value: Any) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    string_values: list[str] = []

    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            nested_keys, nested_values = _collect_keys_and_string_values(nested)
            keys.update(nested_keys)
            string_values.extend(nested_values)
        return keys, string_values

    if isinstance(value, list):
        for nested in value:
            nested_keys, nested_values = _collect_keys_and_string_values(nested)
            keys.update(nested_keys)
            string_values.extend(nested_values)
        return keys, string_values

    if isinstance(value, str):
        string_values.append(value)

    return keys, string_values


def _assert_recruiter_safe_response(payload: Any) -> None:
    keys, string_values = _collect_keys_and_string_values(payload)
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(keys)
    assert FORBIDDEN_RESPONSE_STRING_VALUES.isdisjoint(set(string_values))


def _seed_recruiter_fixture(session, models, security, decision_layer, decision_persistence, skills_service):
    admin_user = _create_user(
        session,
        models,
        security,
        email="recruiter-admin@example.com",
        full_name="Recruiter Admin",
    )
    member_user = _create_user(
        session,
        models,
        security,
        email="recruiter-member@example.com",
        full_name="Recruiter Member",
    )
    other_admin_user = _create_user(
        session,
        models,
        security,
        email="recruiter-other-admin@example.com",
        full_name="Recruiter Other Admin",
    )
    candidate_user = _create_user(
        session,
        models,
        security,
        email="recruiter-candidate@example.com",
        full_name="Recruiter Candidate",
    )

    organisation = models.Organisation(name="Talenti Recruiter Org")
    other_organisation = models.Organisation(name="Talenti Recruiter Other Org")
    session.add_all([organisation, other_organisation])
    session.flush()

    session.add_all(
        [
            models.OrgUser(organisation_id=organisation.id, user_id=admin_user.id, role="admin"),
            models.OrgUser(organisation_id=organisation.id, user_id=member_user.id, role="member"),
            models.OrgUser(organisation_id=other_organisation.id, user_id=other_admin_user.id, role="admin"),
        ]
    )

    candidate = models.CandidateProfile(
        user_id=candidate_user.id,
        first_name="Jamie",
        last_name="Candidate",
        email="recruiter-candidate@example.com",
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
    no_decision_interview = models.Interview(
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
    other_environment_input = models.OrgEnvironmentInput(
        organisation_id=other_organisation.id,
        raw_answers='{"q1_direction_style":"we_tell_people_exactly_what_to_do"}',
        signals_json='[{"variable":"control_vs_autonomy","value":"execution_led"}]',
        derived_environment='{"control_vs_autonomy":"execution_led","outcome_vs_process":"process_led"}',
        submitted_by=other_admin_user.id,
    )
    session.add_all([interview, no_decision_interview, other_interview, environment_input, other_environment_input])
    session.flush()

    first_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=interview.id,
            candidate_id=candidate.id,
            role_id=role.id,
            organisation_id=organisation.id,
            dimensions={
                "feedback": _dimension(
                    score=-1,
                    confidence="MEDIUM",
                    valid_signals=["feedback_valid_signal"],
                    invalid_signals=["feedback_invalid_signal"],
                    conflict_flags=["feedback_conflict_flag"],
                    evidence_summary="Candidate accepted direct feedback and adjusted quickly.",
                )
            },
        )
    )
    second_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=interview.id,
            candidate_id=candidate.id,
            role_id=role.id,
            organisation_id=organisation.id,
            dimensions={
                "ownership": _dimension(
                    score=2,
                    confidence="HIGH",
                    evidence_summary="Set direction independently and closed execution gaps quickly.",
                ),
                "feedback": _dimension(score=-1, confidence="MEDIUM"),
            },
        )
    )
    other_org_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=other_interview.id,
            candidate_id=candidate.id,
            role_id=other_role.id,
            organisation_id=other_organisation.id,
            dimensions={"execution": _dimension(score=-1, confidence="LOW")},
        )
    )

    first_decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=first_result,
        interview_id=interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        org_environment_input_id=environment_input.id,
        environment_profile={"control_vs_autonomy": "full_ownership"},
        actor_user_id=admin_user.id,
    )
    first_decision.created_at = datetime.utcnow() - timedelta(minutes=10)
    first_decision.updated_at = first_decision.created_at
    session.flush()

    second_decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=second_result,
        interview_id=interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        org_environment_input_id=environment_input.id,
        environment_profile={"control_vs_autonomy": "full_ownership"},
        actor_user_id=admin_user.id,
    )
    second_decision.created_at = datetime.utcnow() - timedelta(minutes=1)
    second_decision.updated_at = second_decision.created_at
    for row in second_decision.dimension_evaluations:
        if row.dimension == "ownership":
            row.evidence_summary_json = json.dumps(
                [
                    "Set direction independently",
                    "Closed execution gaps quickly",
                ]
            )
        elif row.dimension == "feedback":
            row.evidence_summary_json = json.dumps(
                {
                    "summary": "Candidate accepted direct feedback and adjusted quickly.",
                    "moments": ["Handled coaching well"],
                }
            )
    session.flush()

    third_decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=other_org_result,
        interview_id=other_interview.id,
        candidate_id=candidate.id,
        role_id=other_role.id,
        organisation_id=other_organisation.id,
        org_environment_input_id=other_environment_input.id,
        environment_profile={"control_vs_autonomy": "execution_led"},
        actor_user_id=other_admin_user.id,
    )
    third_decision.created_at = datetime.utcnow() - timedelta(minutes=2)
    third_decision.updated_at = third_decision.created_at
    session.flush()

    interview_score = models.InterviewScore(
        interview_id=interview.id,
        culture_fit_score=82,
        skills_score=99,
        skills_outcome="PASS",
        overall_alignment="strong_fit",
        overall_risk_level="low",
        recommendation="proceed",
        summary="PASS REVIEW FAIL must stay out of recruiter decision responses.",
        service1_raw=json.dumps({"overall_score": 82}),
        service2_raw=json.dumps({"match_score": 99, "ranking": 1, "skills_outcome": "PASS"}),
        created_at=datetime.utcnow() - timedelta(minutes=15),
    )
    session.add(interview_score)
    session.flush()

    session.add(
        models.ScoreDimension(
            interview_id=interview.id,
            name="ownership",
            score=91,
            confidence=0.93,
            outcome="pass",
            required_pass=75,
            required_watch=60,
            gap=16,
            matched_signals='["ownership_signal"]',
            source="service1",
            rationale="Legacy score dimension retained for regression checks.",
        )
    )

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
        source_references=[{"service": "model-service-2", "match_score": 99}],
        human_readable_summary="PASS REVIEW FAIL skills evidence remains separate from behavioural decisions.",
        requires_human_review=True,
        model_version="skills-ms2-v1",
    )

    session.commit()

    return {
        "organisation_id": organisation.id,
        "other_organisation_id": other_organisation.id,
        "candidate_id": candidate.id,
        "role_id": role.id,
        "interview_id": interview.id,
        "no_decision_interview_id": no_decision_interview.id,
        "other_interview_id": other_interview.id,
        "first_decision_id": first_decision.id,
        "second_decision_id": second_decision.id,
        "third_decision_id": third_decision.id,
        "interview_score_id": interview_score.id,
        "skills_summary_id": skills_summary.id,
        "admin_token": security.create_access_token(admin_user.id),
        "member_token": security.create_access_token(member_user.id),
        "other_admin_token": security.create_access_token(other_admin_user.id),
    }


def test_recruiter_decision_api_returns_404_when_feature_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=False
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recruiter decision API is not available."


def test_recruiter_decision_api_requires_authentication() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(f"/api/v1/interviews/{seeded['interview_id']}/decision")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing token"


@pytest.mark.parametrize("token_key", ["admin_token", "member_token"])
def test_recruiter_decision_api_allows_org_members(token_key: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert response.status_code == 200
    assert response.json()["decision_id"] == seeded["second_decision_id"]


def test_recruiter_decision_api_rejects_users_outside_the_org() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['other_admin_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not an org member"


def test_recruiter_decision_api_returns_404_for_missing_interview_or_missing_decision() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}
    missing_interview_response = client.get("/api/v1/interviews/does-not-exist/decision", headers=headers)
    missing_decision_response = client.get(
        f"/api/v1/interviews/{seeded['no_decision_interview_id']}/decision",
        headers=headers,
    )

    assert missing_interview_response.status_code == 404
    assert missing_interview_response.json()["detail"] == "Interview not found"
    assert missing_decision_response.status_code == 404
    assert missing_decision_response.json()["detail"] == "Decision not found"


def test_recruiter_decision_api_returns_latest_recruiter_safe_decision_shape() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["decision_id"] == seeded["second_decision_id"]
    assert payload["interview_id"] == seeded["interview_id"]
    assert payload["decision_state"] in {
        "PROCEED",
        "PROCEED_WITH_CONDITIONS",
        "DO_NOT_PROCEED",
        "INSUFFICIENT_EVIDENCE",
    }
    assert isinstance(payload["decision_valid"], bool)
    assert isinstance(payload["confidence_gate_passed"], bool)
    assert isinstance(payload["integrity_status"], str)
    assert isinstance(payload["decision_summary"], str)
    assert isinstance(payload["risk_summary"], list)
    assert isinstance(payload["evidence_summary"], list)
    assert isinstance(payload["evidence_gaps"], list)
    assert isinstance(payload["conditions"], list)
    assert isinstance(payload["conflict_flags"], list)
    assert "trade_off_statement" in payload
    assert "rule_version" in payload
    assert "policy_version" in payload
    assert "audit_trace" not in payload
    ownership_summary = next(item for item in payload["evidence_summary"] if item["dimension"] == "ownership")
    assert ownership_summary["evidence_summary"] == [
        "Set direction independently",
        "Closed execution gaps quickly",
    ]
    _assert_recruiter_safe_response(payload)


def test_recruiter_decision_api_excludes_skills_and_ranking_artifacts_even_when_present_elsewhere() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['member_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()

    for key in [
        "skills_score",
        "skills_outcome",
        "skills_summary_id",
        "skills_assessment_summary",
        "match_score",
        "rank",
        "shortlist_position",
        "best_candidate",
        "overall_score",
    ]:
        assert key not in payload
    _assert_recruiter_safe_response(payload)


def test_recruiter_decision_api_handles_null_and_malformed_json_without_crashing() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        decision = session.get(models.DecisionOutcome, seeded["second_decision_id"])
        assert decision is not None
        decision.evidence_gaps_json = "{not-json"
        decision.conflict_flags_json = ""
        decision.conditions_json = "{not-json"
        decision.dimension_evaluations[0].evidence_summary_json = "{not-json"
        decision.dimension_evaluations[1].evidence_summary_json = ""
        session.commit()

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["evidence_gaps"] == []
    assert payload["conflict_flags"] == []
    assert payload["conditions"] == []
    evidence_summary_by_dimension = {
        item["dimension"]: item["evidence_summary"] for item in payload["evidence_summary"]
    }
    assert evidence_summary_by_dimension["ownership"] is None
    assert len([value for value in evidence_summary_by_dimension.values() if value is None]) >= 2
    _assert_recruiter_safe_response(payload)


def test_recruiter_decision_endpoint_is_read_only_with_no_side_effects() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        before_decision_ids = [
            item.id
            for item in session.execute(
                select(models.DecisionOutcome).order_by(models.DecisionOutcome.created_at.asc(), models.DecisionOutcome.id.asc())
            ).scalars()
        ]
        before_interview_score_ids = [
            item.id for item in session.execute(select(models.InterviewScore)).scalars()
        ]
        before_score_dimension_ids = [
            item.id for item in session.execute(select(models.ScoreDimension)).scalars()
        ]
        before_skills_summary_ids = [
            item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()
        ]
        before_decision_updated_at = session.get(models.DecisionOutcome, seeded["second_decision_id"]).updated_at

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200

    with db.SessionLocal() as session:
        after_decision_ids = [
            item.id
            for item in session.execute(
                select(models.DecisionOutcome).order_by(models.DecisionOutcome.created_at.asc(), models.DecisionOutcome.id.asc())
            ).scalars()
        ]
        after_interview_score_ids = [
            item.id for item in session.execute(select(models.InterviewScore)).scalars()
        ]
        after_score_dimension_ids = [
            item.id for item in session.execute(select(models.ScoreDimension)).scalars()
        ]
        after_skills_summary_ids = [
            item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()
        ]
        after_decision_updated_at = session.get(models.DecisionOutcome, seeded["second_decision_id"]).updated_at

    assert after_decision_ids == before_decision_ids
    assert after_interview_score_ids == before_interview_score_ids
    assert after_score_dimension_ids == before_score_dimension_ids
    assert after_skills_summary_ids == before_skills_summary_ids
    assert after_decision_updated_at == before_decision_updated_at
