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

FORBIDDEN_TOP_LEVEL_KEYS = {
    "audit_trace",
    "audit_trail_summary",
    "best_candidate",
    "confidence_gate_passed",
    "decision_id",
    "decision_state",
    "decision_valid",
    "hiring_outcome",
    "integrity_status",
    "match_score",
    "ranking",
    "rank",
    "recommendation",
    "risk_stack",
    "shortlist_position",
    "skills_outcome",
}
FORBIDDEN_SERIALIZED_TERMS = ("PASS", "REVIEW", "FAIL")


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


def _load_modules(*, recruiter_skills_api_enabled: bool):
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    database_url = _require_postgres_test_database()
    prepare_test_environment()
    import os

    os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_RECRUITER_SKILLS_SUMMARY_API_ENABLED"] = (
        "true" if recruiter_skills_api_enabled else "false"
    )
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


def _dimension(score: int = 1, confidence: str = "HIGH") -> dict[str, object]:
    return {
        "score_internal": score,
        "confidence": confidence,
        "evidence_summary": "Observed behavioural evidence.",
        "rationale": "Deterministic behavioural rationale.",
        "valid_signals": ["repeatable_signal"],
        "invalid_signals": [],
        "conflict_flags": [],
    }


def _decision_payload(
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
) -> dict[str, object]:
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
            {"dimension": dimension, **_dimension()}
            for dimension in ["ownership", "execution", "challenge", "ambiguity", "feedback"]
        ],
        "critical_dimensions": ["ownership", "execution"],
        "minimum_dimensions": ["ownership", "execution", "challenge", "ambiguity", "feedback"],
        "priority_dimensions": ["challenge"],
        "rule_version": "tds-phase10-recruiter-skills-summary-v1",
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


def _assert_recruiter_safe_response(payload: dict[str, Any]) -> None:
    assert FORBIDDEN_TOP_LEVEL_KEYS.isdisjoint(payload.keys())
    assert payload["excluded_from_tds_decisioning"] is True
    assert payload["decisioning_boundary_note"] == (
        "This summary is not used in the behavioural TDS decision outcome."
    )
    assert "decision_state" not in payload
    assert "match_score" not in payload
    assert "rank" not in payload
    assert "best_candidate" not in payload
    assert "skills_outcome" not in payload
    serialized = json.dumps(payload)
    for term in FORBIDDEN_SERIALIZED_TERMS:
        assert term not in serialized


def _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service):
    admin_user = _create_user(
        session,
        models,
        security,
        email="recruiter-skills-admin@example.com",
        full_name="Recruiter Skills Admin",
    )
    member_user = _create_user(
        session,
        models,
        security,
        email="recruiter-skills-member@example.com",
        full_name="Recruiter Skills Member",
    )
    other_admin_user = _create_user(
        session,
        models,
        security,
        email="recruiter-skills-other@example.com",
        full_name="Recruiter Skills Other",
    )
    candidate_user = _create_user(
        session,
        models,
        security,
        email="recruiter-skills-candidate@example.com",
        full_name="Recruiter Skills Candidate",
    )

    organisation = models.Organisation(name="Talenti Recruiter Skills Org")
    other_organisation = models.Organisation(name="Talenti Recruiter Skills Other Org")
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
        first_name="Riley",
        last_name="Evidence",
        email="recruiter-skills-candidate@example.com",
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
        title="Support Lead",
        description="Own support operations.",
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
    no_summary_interview = models.Interview(
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
    session.add_all([interview, no_summary_interview, other_interview, environment_input, other_environment_input])
    session.flush()

    decision_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=interview.id,
            candidate_id=candidate.id,
            role_id=role.id,
            organisation_id=organisation.id,
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
    decision.created_at = datetime.utcnow() - timedelta(minutes=5)
    decision.updated_at = decision.created_at

    other_decision_result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=other_interview.id,
            candidate_id=candidate.id,
            role_id=other_role.id,
            organisation_id=other_organisation.id,
        )
    )
    other_decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=other_decision_result,
        interview_id=other_interview.id,
        candidate_id=candidate.id,
        role_id=other_role.id,
        organisation_id=other_organisation.id,
        org_environment_input_id=other_environment_input.id,
        environment_profile={"control_vs_autonomy": "execution_led"},
        actor_user_id=other_admin_user.id,
    )
    other_decision.created_at = datetime.utcnow() - timedelta(minutes=4)
    other_decision.updated_at = other_decision.created_at

    interview_score = models.InterviewScore(
        interview_id=interview.id,
        culture_fit_score=84,
        skills_score=97,
        skills_outcome="PASS",
        overall_alignment="strong_fit",
        overall_risk_level="low",
        recommendation="proceed",
        summary="Legacy scoring artifacts must stay out of recruiter-facing skills summaries.",
        service2_raw=json.dumps({"match_score": 97, "ranking": 1, "skills_outcome": "PASS"}),
        created_at=datetime.utcnow() - timedelta(minutes=15),
    )
    session.add(interview_score)
    session.flush()

    session.add(
        models.ScoreDimension(
            interview_id=interview.id,
            name="execution",
            score=88,
            confidence=0.91,
            outcome="pass",
            required_pass=75,
            required_watch=60,
            gap=13,
            matched_signals='["execution_signal"]',
            source="service1",
            rationale="Legacy dimension retained for regression checks.",
        )
    )

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
                "source": "model-service-2",
                "artifact_type": "skills_summary",
                "ranking": 5,
                "skills_outcome": "FAIL",
                "reference_id": "skills-ref-old",
            }
        ],
        human_readable_summary="PASS legacy wording should never reach recruiter responses.",
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
                "service": "model-service-2",
                "artifact_type": "skills_assessment_summary",
                "legacy_contract_adapter": "ms2-skills-summary-shadow-v1",
                "reference_id": "skills-ref-new",
                "ranking": 2,
                "match_score": 97,
                "raw_hiring_label": "PASS",
                "skills_outcome": "REVIEW",
            }
        ],
        human_readable_summary="REVIEW evidence says the candidate has strong discovery depth.",
        requires_human_review=True,
        model_version="skills-ms2-v2",
    )
    latest_summary.created_at = datetime.utcnow() - timedelta(minutes=1)
    latest_summary.updated_at = latest_summary.created_at

    other_summary = skills_service.create_skills_assessment_summary(
        session,
        interview_id=other_interview.id,
        candidate_id=candidate.id,
        role_id=other_role.id,
        organisation_id=other_organisation.id,
        observed_competencies=["ticket_triage"],
        competency_coverage={"required": 4, "observed": 2},
        skill_gaps=["incident_command"],
        evidence_strength="HIGH",
        confidence="HIGH",
        source_references=[{"source": "model-service-2", "reference_id": "other-org-ref"}],
        human_readable_summary="Other org summary.",
        requires_human_review=False,
        model_version="skills-ms2-v3",
    )
    other_summary.created_at = datetime.utcnow() - timedelta(minutes=2)
    other_summary.updated_at = other_summary.created_at

    session.commit()

    return {
        "interview_id": interview.id,
        "no_summary_interview_id": no_summary_interview.id,
        "other_interview_id": other_interview.id,
        "latest_summary_id": latest_summary.id,
        "first_summary_id": first_summary.id,
        "decision_id": decision.id,
        "interview_score_id": interview_score.id,
        "admin_token": security.create_access_token(admin_user.id),
        "member_token": security.create_access_token(member_user.id),
        "other_admin_token": security.create_access_token(other_admin_user.id),
    }


def test_recruiter_skills_summary_api_returns_404_when_feature_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=False
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recruiter skills assessment summary API is not available."


def test_recruiter_skills_summary_api_requires_authentication() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)

    response = client.get(f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing token"


@pytest.mark.parametrize("token_key", ["admin_token", "member_token"])
def test_recruiter_skills_summary_api_allows_org_members(token_key: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert response.status_code == 200
    assert response.json()["skills_summary_id"] == seeded["latest_summary_id"]


def test_recruiter_skills_summary_api_rejects_users_outside_the_org() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded['other_admin_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not an org member"


def test_recruiter_skills_summary_api_returns_404_for_missing_interview_or_missing_summary() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)

    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}
    missing_interview_response = client.get(
        "/api/v1/interviews/does-not-exist/skills-assessment-summary",
        headers=headers,
    )
    missing_summary_response = client.get(
        f"/api/v1/interviews/{seeded['no_summary_interview_id']}/skills-assessment-summary",
        headers=headers,
    )

    assert missing_interview_response.status_code == 404
    assert missing_interview_response.json()["detail"] == "Interview not found"
    assert missing_summary_response.status_code == 404
    assert missing_summary_response.json()["detail"] == "Skills assessment summary not found"


def test_recruiter_skills_summary_api_returns_latest_recruiter_safe_shape() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["skills_summary_id"] == seeded["latest_summary_id"]
    assert payload["interview_id"] == seeded["interview_id"]
    assert payload["observed_competencies"][0]["competency"] == "discovery"
    assert payload["competency_coverage"]["coverage_band"] == "partial"
    assert payload["skill_gaps"] == ["forecasting"]
    assert payload["evidence_strength"] == "MEDIUM"
    assert payload["confidence"] == "MEDIUM"
    assert payload["human_readable_summary"] == "Skills evidence summary available for recruiter review."
    assert payload["requires_human_review"] is True
    assert payload["excluded_from_tds_decisioning"] is True
    assert payload["source_references"] == [
        {
            "source": "model-service-2",
            "artifact_type": "skills_assessment_summary",
            "legacy_contract_adapter": "ms2-skills-summary-shadow-v1",
            "reference_id": "skills-ref-new",
        }
    ]
    _assert_recruiter_safe_response(payload)


def test_recruiter_skills_summary_api_handles_null_and_malformed_json_without_crashing() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)
        summary = session.get(models.SkillsAssessmentSummary, seeded["latest_summary_id"])
        assert summary is not None
        summary.observed_competencies_json = ""
        summary.competency_coverage_json = "{not-json"
        summary.skill_gaps_json = ""
        summary.source_references_json = "{not-json"
        summary.human_readable_summary = None
        session.commit()

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["observed_competencies"] == []
    assert payload["competency_coverage"] == {}
    assert payload["skill_gaps"] == []
    assert payload["source_references"] == []
    assert payload["human_readable_summary"] is None
    _assert_recruiter_safe_response(payload)


def test_recruiter_skills_summary_endpoint_is_read_only_with_no_side_effects() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        recruiter_skills_api_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_fixture(session, models, security, decision_layer, decision_persistence, skills_service)
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
        before_interview_score_ids = [
            item.id for item in session.execute(select(models.InterviewScore)).scalars()
        ]
        before_score_dimension_ids = [
            item.id for item in session.execute(select(models.ScoreDimension)).scalars()
        ]
        before_summary_updated_at = session.get(
            models.SkillsAssessmentSummary,
            seeded["latest_summary_id"],
        ).updated_at
        before_decision_updated_at = session.get(models.DecisionOutcome, seeded["decision_id"]).updated_at

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200

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
        after_interview_score_ids = [
            item.id for item in session.execute(select(models.InterviewScore)).scalars()
        ]
        after_score_dimension_ids = [
            item.id for item in session.execute(select(models.ScoreDimension)).scalars()
        ]
        after_summary_updated_at = session.get(
            models.SkillsAssessmentSummary,
            seeded["latest_summary_id"],
        ).updated_at
        after_decision_updated_at = session.get(models.DecisionOutcome, seeded["decision_id"]).updated_at

    assert after_summary_ids == before_summary_ids
    assert after_decision_ids == before_decision_ids
    assert after_interview_score_ids == before_interview_score_ids
    assert after_score_dimension_ids == before_score_dimension_ids
    assert after_summary_updated_at == before_summary_updated_at
    assert after_decision_updated_at == before_decision_updated_at
