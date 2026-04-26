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
FORBIDDEN_TOP_LEVEL_KEYS = {
    "decision_id",
    "decision_mode",
    "decision_state",
    "decision_valid",
    "confidence_gate_passed",
    "integrity_status",
    "risk_stack",
    "rationale",
    "audit_trace",
    "audit_trail_summary",
    "match_score",
    "ranking",
    "shortlist_position",
    "skills_outcome",
    "recommendation",
    "hiring_outcome",
}
FORBIDDEN_TOP_LEVEL_STRING_VALUES = {"PASS", "REVIEW", "FAIL"}


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


def _load_modules(*, inspection_enabled: bool):
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    database_url = _require_postgres_test_database()
    prepare_test_environment()
    import os

    os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_SKILLS_SUMMARY_INSPECTION_API_ENABLED"] = "true" if inspection_enabled else "false"
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
        "rule_version": "tds-phase5-shadow-v1",
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


def _assert_non_decisional_response(payload: Any) -> None:
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        assert isinstance(item, dict)
        assert FORBIDDEN_TOP_LEVEL_KEYS.isdisjoint(item.keys())
        top_level_string_values = {value for value in item.values() if isinstance(value, str)}
        assert FORBIDDEN_TOP_LEVEL_STRING_VALUES.isdisjoint(top_level_string_values)
        assert item["excluded_from_tds_decisioning"] is True


def _seed_inspection_fixture(session, models, security, decision_layer, decision_persistence, skills_service):
    admin_user = _create_user(
        session,
        models,
        security,
        email="skills-admin@example.com",
        full_name="Skills Admin",
    )
    owner_user = _create_user(
        session,
        models,
        security,
        email="skills-owner@example.com",
        full_name="Skills Owner",
    )
    member_user = _create_user(
        session,
        models,
        security,
        email="skills-member@example.com",
        full_name="Skills Member",
    )
    other_admin_user = _create_user(
        session,
        models,
        security,
        email="skills-other-admin@example.com",
        full_name="Skills Other Admin",
    )
    candidate_user = _create_user(
        session,
        models,
        security,
        email="skills-candidate@example.com",
        full_name="Skills Candidate",
    )

    organisation = models.Organisation(name="Talenti Skills Inspection Org")
    other_organisation = models.Organisation(name="Talenti Skills Other Org")
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
        first_name="Jordan",
        last_name="Signals",
        email="skills-candidate@example.com",
    )
    session.add(candidate)
    session.flush()

    role = models.JobRole(
        organisation_id=organisation.id,
        title="Enterprise AE",
        description="Own complex sales cycles.",
        status="active",
    )
    other_role = models.JobRole(
        organisation_id=other_organisation.id,
        title="Customer Success Lead",
        description="Own renewals and expansion.",
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
    other_environment_input = models.OrgEnvironmentInput(
        organisation_id=other_organisation.id,
        raw_answers='{"q1_direction_style":"we_tell_people_exactly_what_to_do"}',
        signals_json='[{"variable":"control_vs_autonomy","value":"execution_led"}]',
        derived_environment='{"control_vs_autonomy":"execution_led","outcome_vs_process":"process_led"}',
        submitted_by=other_admin_user.id,
    )
    session.add_all([interview, other_interview, environment_input, other_environment_input])
    session.flush()

    decision_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=interview.id,
            candidate_id=candidate.id,
            role_id=role.id,
            organisation_id=organisation.id,
            dimensions={"feedback": _dimension(score=-1, confidence="MEDIUM")},
        )
    )
    decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=decision_result,
        interview_id=interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        org_environment_input_id=environment_input.id,
        environment_profile={"control_vs_autonomy": "full_ownership"},
        actor_user_id=admin_user.id,
    )
    decision.created_at = datetime.utcnow() - timedelta(minutes=4)
    decision.updated_at = decision.created_at

    other_org_decision_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=other_interview.id,
            candidate_id=candidate.id,
            role_id=other_role.id,
            organisation_id=other_organisation.id,
            dimensions={"execution": _dimension(score=-1, confidence="LOW")},
        )
    )
    other_org_decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=other_org_decision_result,
        interview_id=other_interview.id,
        candidate_id=candidate.id,
        role_id=other_role.id,
        organisation_id=other_organisation.id,
        org_environment_input_id=other_environment_input.id,
        environment_profile={"control_vs_autonomy": "execution_led"},
        actor_user_id=other_admin_user.id,
    )
    other_org_decision.created_at = datetime.utcnow() - timedelta(minutes=3)
    other_org_decision.updated_at = other_org_decision.created_at

    first_summary = skills_service.create_skills_assessment_summary(
        session,
        interview_id=interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        observed_competencies=["discovery"],
        competency_coverage={"required": 5, "observed": 1},
        skill_gaps=["forecasting", "meddic"],
        evidence_strength="LOW",
        confidence="LOW",
        source_references=[
            {
                "source": "legacy-ms2",
                "raw_hiring_label": "PASS",
                "raw_review_marker": "REVIEW",
                "raw_fail_marker": "FAIL",
                "ranking": 1,
                "skills_outcome": "PASS",
            }
        ],
        human_readable_summary="Initial organisational skills evidence snapshot.",
        requires_human_review=True,
        model_version="skills-ms2-v1",
    )
    first_summary.created_at = datetime.utcnow() - timedelta(minutes=10)
    first_summary.updated_at = first_summary.created_at

    latest_summary = skills_service.create_skills_assessment_summary(
        session,
        interview_id=interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        observed_competencies=[
            {"competency": "discovery", "evidence_count": 3},
            {"competency": "objection_handling", "evidence_count": 2},
        ],
        competency_coverage={"required": 5, "observed": 3, "coverage_band": "partial"},
        skill_gaps=["forecasting"],
        evidence_strength="MEDIUM",
        confidence="MEDIUM",
        source_references=[
            {
                "source": "legacy-ms2",
                "raw_hiring_label": "PASS",
                "raw_review_marker": "REVIEW",
                "raw_fail_marker": "FAIL",
                "ranking": 2,
                "skills_outcome": "REVIEW",
            }
        ],
        human_readable_summary="Observed skills evidence remains informational for internal review.",
        requires_human_review=True,
        model_version="skills-ms2-v2",
    )
    latest_summary.created_at = datetime.utcnow() - timedelta(minutes=1)
    latest_summary.updated_at = latest_summary.created_at

    other_org_summary = skills_service.create_skills_assessment_summary(
        session,
        interview_id=other_interview.id,
        candidate_id=candidate.id,
        role_id=other_role.id,
        organisation_id=other_organisation.id,
        observed_competencies=["renewals"],
        competency_coverage={"required": 4, "observed": 2},
        skill_gaps=["expansion"],
        evidence_strength="HIGH",
        confidence="HIGH",
        source_references=[{"source": "legacy-ms2", "raw_hiring_label": "PASS"}],
        human_readable_summary="Other organisation summary.",
        requires_human_review=False,
        model_version="skills-ms2-v3",
    )
    other_org_summary.created_at = datetime.utcnow() - timedelta(minutes=2)
    other_org_summary.updated_at = other_org_summary.created_at

    interview_score = models.InterviewScore(
        interview_id=interview.id,
        culture_fit_score=81,
        skills_score=98,
        skills_outcome="PASS",
        overall_alignment="strong_fit",
        overall_risk_level="low",
        recommendation="proceed",
        summary="Legacy scoring artefacts must remain out of the inspection response shape.",
        service2_raw=json.dumps({"match_score": 98, "ranking": 1, "skills_outcome": "PASS"}),
        created_at=datetime.utcnow() - timedelta(minutes=15),
    )
    session.add(interview_score)
    session.commit()

    return {
        "organisation_id": organisation.id,
        "other_organisation_id": other_organisation.id,
        "candidate_id": candidate.id,
        "role_id": role.id,
        "other_role_id": other_role.id,
        "interview_id": interview.id,
        "other_interview_id": other_interview.id,
        "decision_id": decision.id,
        "decision_state": decision.decision_state,
        "other_org_decision_id": other_org_decision.id,
        "first_summary_id": first_summary.id,
        "latest_summary_id": latest_summary.id,
        "other_org_summary_id": other_org_summary.id,
        "interview_score_id": interview_score.id,
        "admin_token": security.create_access_token(admin_user.id),
        "owner_token": security.create_access_token(owner_user.id),
        "member_token": security.create_access_token(member_user.id),
        "other_admin_token": security.create_access_token(other_admin_user.id),
    }


def test_skills_summary_inspection_api_returns_404_when_feature_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=False
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/interviews/{seeded['interview_id']}/latest",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Skills assessment summary inspection API is not available."


def test_skills_summary_inspection_api_requires_authentication() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(f"/api/v1/internal/skills-assessment-summaries/{seeded['latest_summary_id']}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing token"


@pytest.mark.parametrize("token_key", ["member_token", "other_admin_token"])
def test_skills_summary_inspection_api_rejects_non_admin_or_wrong_org_access(token_key: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/{seeded['latest_summary_id']}",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only organisation admins can access this resource."


@pytest.mark.parametrize("token_key", ["admin_token", "owner_token"])
def test_skills_summary_inspection_api_allows_admin_and_owner_reads(token_key: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/{seeded['latest_summary_id']}",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skills_summary_id"] == seeded["latest_summary_id"]
    _assert_non_decisional_response(payload)


def test_latest_skills_summary_by_interview_returns_latest_created_summary() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/interviews/{seeded['interview_id']}/latest",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skills_summary_id"] == seeded["latest_summary_id"]
    assert payload["interview_id"] == seeded["interview_id"]
    assert payload["observed_competencies"][0]["competency"] == "discovery"
    assert payload["competency_coverage"]["coverage_band"] == "partial"
    assert payload["skill_gaps"] == ["forecasting"]
    assert payload["source_references"] == [{"source": "legacy-ms2"}]
    _assert_non_decisional_response(payload)


def test_skills_summary_by_id_returns_expected_detail_without_joining_decision_outcome() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/{seeded['first_summary_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skills_summary_id"] == seeded["first_summary_id"]
    assert payload["source_references"] == [{"source": "legacy-ms2"}]
    assert payload["requires_human_review"] is True
    assert "decision_id" not in payload
    assert "decision_state" not in payload
    assert "risk_stack" not in payload
    assert "rationale" not in payload
    assert seeded["decision_id"] not in json.dumps(payload)
    _assert_non_decisional_response(payload)


def test_role_and_candidate_list_routes_return_compact_desc_order_and_filter_org_scope() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    role_response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/roles/{seeded['role_id']}?limit=10&offset=0",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )
    candidate_response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/candidates/{seeded['candidate_id']}?limit=10&offset=0",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert role_response.status_code == 200
    assert candidate_response.status_code == 200

    role_payload = role_response.json()
    candidate_payload = candidate_response.json()

    assert [item["skills_summary_id"] for item in role_payload] == [
        seeded["latest_summary_id"],
        seeded["first_summary_id"],
    ]
    assert [item["skills_summary_id"] for item in candidate_payload] == [
        seeded["latest_summary_id"],
        seeded["first_summary_id"],
    ]
    assert seeded["other_org_summary_id"] not in [item["skills_summary_id"] for item in candidate_payload]
    assert "observed_competencies" not in role_payload[0]
    assert "competency_coverage" not in role_payload[0]
    assert seeded["decision_id"] not in json.dumps(candidate_payload)
    _assert_non_decisional_response(role_payload)
    _assert_non_decisional_response(candidate_payload)


def test_candidate_list_is_scoped_to_admin_orgs() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/candidates/{seeded['candidate_id']}?limit=10&offset=0",
        headers={"Authorization": f"Bearer {seeded['other_admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["skills_summary_id"] for item in payload] == [seeded["other_org_summary_id"]]
    _assert_non_decisional_response(payload)


def test_skills_summary_inspection_decodes_json_text_fields_and_handles_nulls_safely() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        summary = session.get(models.SkillsAssessmentSummary, seeded["latest_summary_id"])
        assert summary is not None
        summary.observed_competencies_json = ""
        summary.competency_coverage_json = "{not-json"
        summary.skill_gaps_json = ""
        summary.source_references_json = "{not-json"
        session.commit()

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/{seeded['latest_summary_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["observed_competencies"] == []
    assert payload["competency_coverage"] == {}
    assert payload["skill_gaps"] == []
    assert payload["source_references"] == []
    _assert_non_decisional_response(payload)


def test_skills_summary_inspection_does_not_surface_behavioural_or_ranking_fields() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/{seeded['latest_summary_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "decision_state" not in payload
    assert "decision_valid" not in payload
    assert "risk_stack" not in payload
    assert "rationale" not in payload
    assert "ranking" not in payload
    assert "match_score" not in payload
    assert "shortlist_position" not in payload
    assert "ranking" not in payload["source_references"][0]
    assert "skills_outcome" not in payload["source_references"][0]
    assert "raw_hiring_label" not in payload["source_references"][0]
    assert "raw_review_marker" not in payload["source_references"][0]
    assert "raw_fail_marker" not in payload["source_references"][0]
    assert payload["excluded_from_tds_decisioning"] is True
    assert payload["source_references"] == [{"source": "legacy-ms2"}]
    _assert_non_decisional_response(payload)


def test_skills_summary_inspection_endpoints_are_read_only_with_no_side_effects() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        before_summary_ids = [
            item.id
            for item in session.execute(
                select(models.SkillsAssessmentSummary).order_by(
                    models.SkillsAssessmentSummary.created_at.asc(),
                    models.SkillsAssessmentSummary.id.asc(),
                )
            ).scalars()
        ]
        before_decision_ids = [
            item.id
            for item in session.execute(
                select(models.DecisionOutcome).order_by(
                    models.DecisionOutcome.created_at.asc(),
                    models.DecisionOutcome.id.asc(),
                )
            ).scalars()
        ]
        before_interview_score_ids = [item.id for item in session.execute(select(models.InterviewScore)).scalars()]
        before_summary_updated_at = session.get(
            models.SkillsAssessmentSummary,
            seeded["latest_summary_id"],
        ).updated_at
        before_decision_updated_at = session.get(models.DecisionOutcome, seeded["decision_id"]).updated_at

    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}
    responses = [
        client.get(
            f"/api/v1/internal/skills-assessment-summaries/{seeded['latest_summary_id']}",
            headers=headers,
        ),
        client.get(
            f"/api/v1/internal/skills-assessment-summaries/interviews/{seeded['interview_id']}/latest",
            headers=headers,
        ),
        client.get(
            f"/api/v1/internal/skills-assessment-summaries/roles/{seeded['role_id']}?limit=10&offset=0",
            headers=headers,
        ),
        client.get(
            f"/api/v1/internal/skills-assessment-summaries/candidates/{seeded['candidate_id']}?limit=10&offset=0",
            headers=headers,
        ),
    ]

    assert all(response.status_code == 200 for response in responses)

    with db.SessionLocal() as session:
        after_summary_ids = [
            item.id
            for item in session.execute(
                select(models.SkillsAssessmentSummary).order_by(
                    models.SkillsAssessmentSummary.created_at.asc(),
                    models.SkillsAssessmentSummary.id.asc(),
                )
            ).scalars()
        ]
        after_decision_ids = [
            item.id
            for item in session.execute(
                select(models.DecisionOutcome).order_by(
                    models.DecisionOutcome.created_at.asc(),
                    models.DecisionOutcome.id.asc(),
                )
            ).scalars()
        ]
        after_interview_score_ids = [item.id for item in session.execute(select(models.InterviewScore)).scalars()]
        after_summary_updated_at = session.get(
            models.SkillsAssessmentSummary,
            seeded["latest_summary_id"],
        ).updated_at
        after_decision_updated_at = session.get(models.DecisionOutcome, seeded["decision_id"]).updated_at

    assert after_summary_ids == before_summary_ids
    assert after_decision_ids == before_decision_ids
    assert after_interview_score_ids == before_interview_score_ids
    assert after_summary_updated_at == before_summary_updated_at
    assert after_decision_updated_at == before_decision_updated_at
