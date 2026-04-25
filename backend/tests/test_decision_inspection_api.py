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
    "shortlist_position",
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


def _load_modules(*, inspection_enabled: bool):
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    database_url = _require_postgres_test_database()
    prepare_test_environment()
    import os

    os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_DECISION_INSPECTION_API_ENABLED"] = "true" if inspection_enabled else "false"
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
    evidence_summary: str = "Observed behavioural evidence.",
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


def _assert_behavioural_only_response(payload: Any) -> None:
    keys, string_values = _collect_keys_and_string_values(payload)
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(keys)
    assert FORBIDDEN_RESPONSE_STRING_VALUES.isdisjoint(set(string_values))


def _seed_inspection_fixture(session, models, security, decision_layer, decision_persistence, skills_service):
    admin_user = _create_user(
        session,
        models,
        security,
        email="decision-admin@example.com",
        full_name="Decision Admin",
    )
    member_user = _create_user(
        session,
        models,
        security,
        email="decision-member@example.com",
        full_name="Decision Member",
    )
    other_admin_user = _create_user(
        session,
        models,
        security,
        email="decision-other-admin@example.com",
        full_name="Decision Other Admin",
    )
    candidate_user = _create_user(
        session,
        models,
        security,
        email="decision-candidate@example.com",
        full_name="Decision Candidate",
    )

    organisation = models.Organisation(name="Talenti Inspection Org")
    other_organisation = models.Organisation(name="Talenti Other Org")
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
        first_name="Taylor",
        last_name="Inspector",
        email="decision-candidate@example.com",
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
        description="Own expansion outcomes.",
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

    decision_persistence.create_decision_audit_event(
        session,
        decision_id=second_decision.id,
        event_type="shadow_inspected",
        actor_type="system",
        actor_user_id=admin_user.id,
        rule_version=second_decision.rule_version,
        policy_version=second_decision.policy_version,
        event_payload={"inspection_mode": "internal_shadow"},
        event_at=datetime.utcnow() - timedelta(seconds=30),
    )

    interview_score = models.InterviewScore(
        interview_id=interview.id,
        culture_fit_score=82,
        skills_score=99,
        skills_outcome="PASS",
        overall_alignment="strong_fit",
        overall_risk_level="low",
        recommendation="proceed",
        summary="PASS REVIEW FAIL must stay out of decision inspection responses.",
        service2_raw=json.dumps({"match_score": 99, "ranking": 1, "skills_outcome": "PASS"}),
        created_at=datetime.utcnow() - timedelta(minutes=15),
    )
    session.add(interview_score)

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
        human_readable_summary="PASS REVIEW FAIL skills summary stays separate from behavioural decisions.",
        requires_human_review=True,
        model_version="skills-ms2-v1",
    )

    session.commit()

    return {
        "organisation_id": organisation.id,
        "other_organisation_id": other_organisation.id,
        "candidate_id": candidate.id,
        "role_id": role.id,
        "other_role_id": other_role.id,
        "interview_id": interview.id,
        "other_interview_id": other_interview.id,
        "first_decision_id": first_decision.id,
        "second_decision_id": second_decision.id,
        "second_decision_state": second_decision.decision_state,
        "third_decision_id": third_decision.id,
        "interview_score_id": interview_score.id,
        "skills_summary_id": skills_summary.id,
        "admin_token": security.create_access_token(admin_user.id),
        "member_token": security.create_access_token(member_user.id),
        "other_admin_token": security.create_access_token(other_admin_user.id),
    }


def test_inspection_api_returns_404_when_feature_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=False
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/decisions/interviews/{seeded['interview_id']}/latest",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Decision inspection API is not available."


def test_inspection_api_requires_authentication() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(f"/api/v1/internal/decisions/{seeded['second_decision_id']}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing token"


@pytest.mark.parametrize("token_key", ["member_token", "other_admin_token"])
def test_inspection_api_rejects_non_admin_or_wrong_org_access(token_key: str) -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/decisions/{seeded['second_decision_id']}",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only organisation admins can access this resource."


def test_latest_decision_by_interview_returns_latest_created_decision() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/decisions/interviews/{seeded['interview_id']}/latest",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision_id"] == seeded["second_decision_id"]
    assert payload["decision_mode"] == "shadow"
    assert payload["interview_id"] == seeded["interview_id"]
    assert payload["rule_version"] == "tds-phase5-shadow-v1"
    assert isinstance(payload["dimension_evaluations"], list)
    assert isinstance(payload["risk_stack"], list)
    assert isinstance(payload["audit_trace"], list)
    assert payload["audit_trail_summary"]["event_count"] == 2
    _assert_behavioural_only_response(payload)


def test_decision_by_id_returns_structured_behavioural_only_detail() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/decisions/{seeded['first_decision_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision_id"] == seeded["first_decision_id"]
    assert isinstance(payload["environment_profile"], dict)
    assert isinstance(payload["critical_dimensions"], list)
    assert isinstance(payload["execution_floor_result"], dict)
    assert isinstance(payload["conditions"], list)
    assert payload["invalid_signals"] == ["feedback_invalid_signal"]
    assert payload["conflict_flags"] == ["feedback_conflict_flag"]
    assert payload["audit_trail_summary"]["event_types"] == ["decision_created"]
    _assert_behavioural_only_response(payload)


def test_decision_audit_trace_endpoint_returns_decoded_audit_events() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/decisions/{seeded['second_decision_id']}/audit-trace",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["event_type"] for item in payload] == ["decision_created", "shadow_inspected"]
    assert payload[0]["event_payload"]["decision_state"] == seeded["second_decision_state"]
    assert payload[1]["event_payload"]["inspection_mode"] == "internal_shadow"
    _assert_behavioural_only_response(payload)


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
        f"/api/v1/internal/decisions/roles/{seeded['role_id']}?limit=10&offset=0",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )
    candidate_response = client.get(
        f"/api/v1/internal/decisions/candidates/{seeded['candidate_id']}?limit=10&offset=0",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert role_response.status_code == 200
    assert candidate_response.status_code == 200

    role_payload = role_response.json()
    candidate_payload = candidate_response.json()

    assert [item["decision_id"] for item in role_payload] == [
        seeded["second_decision_id"],
        seeded["first_decision_id"],
    ]
    assert [item["decision_id"] for item in candidate_payload] == [
        seeded["second_decision_id"],
        seeded["first_decision_id"],
    ]
    assert seeded["third_decision_id"] not in [item["decision_id"] for item in candidate_payload]
    assert "dimension_evaluations" not in role_payload[0]
    assert "risk_stack" not in role_payload[0]
    _assert_behavioural_only_response(role_payload)
    _assert_behavioural_only_response(candidate_payload)


def test_inspection_api_handles_null_and_malformed_json_without_crashing() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        decision = session.get(models.DecisionOutcome, seeded["second_decision_id"])
        assert decision is not None
        decision.environment_profile_json = ""
        decision.critical_dimensions_json = "{not-json"
        decision.minimum_dimensions_json = ""
        decision.priority_dimensions_json = "{not-json"
        decision.evidence_gaps_json = "{not-json"
        decision.invalid_signals_json = ""
        decision.conflict_flags_json = "{not-json"
        decision.execution_floor_result_json = "{not-json"
        decision.conditions_json = ""
        decision.audit_trace_json = "{not-json"
        decision.dimension_evaluations[0].evidence_summary_json = "{not-json"
        decision.risk_flags[0].context_json = "{not-json"
        decision.audit_trail_entries[0].event_payload_json = "{not-json"
        session.commit()

    detail_response = client.get(
        f"/api/v1/internal/decisions/{seeded['second_decision_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )
    audit_response = client.get(
        f"/api/v1/internal/decisions/{seeded['second_decision_id']}/audit-trace",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert detail_response.status_code == 200
    assert audit_response.status_code == 200

    detail_payload = detail_response.json()
    audit_payload = audit_response.json()

    assert detail_payload["environment_profile"] == {}
    assert detail_payload["critical_dimensions"] == []
    assert detail_payload["minimum_dimensions"] == []
    assert detail_payload["priority_dimensions"] == []
    assert detail_payload["evidence_gaps"] == []
    assert detail_payload["invalid_signals"] == []
    assert detail_payload["conflict_flags"] == []
    assert detail_payload["execution_floor_result"] == {}
    assert detail_payload["conditions"] == []
    assert detail_payload["audit_trace"] == []
    assert detail_payload["dimension_evaluations"][0]["evidence_summary"] is None
    assert detail_payload["risk_stack"][0]["context"] is None
    assert audit_payload[0]["event_payload"] == {}
    _assert_behavioural_only_response(detail_payload)
    _assert_behavioural_only_response(audit_payload)


def test_inspection_endpoints_are_read_only_with_no_side_effects() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = _load_modules(
        inspection_enabled=True
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_inspection_fixture(
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
        before_skills_summary_ids = [
            item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()
        ]
        before_decision_updated_at = session.get(models.DecisionOutcome, seeded["second_decision_id"]).updated_at

    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}
    responses = [
        client.get(f"/api/v1/internal/decisions/{seeded['second_decision_id']}", headers=headers),
        client.get(
            f"/api/v1/internal/decisions/interviews/{seeded['interview_id']}/latest",
            headers=headers,
        ),
        client.get(f"/api/v1/internal/decisions/{seeded['second_decision_id']}/audit-trace", headers=headers),
        client.get(f"/api/v1/internal/decisions/roles/{seeded['role_id']}", headers=headers),
        client.get(f"/api/v1/internal/decisions/candidates/{seeded['candidate_id']}", headers=headers),
    ]

    assert all(response.status_code == 200 for response in responses)

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
        after_skills_summary_ids = [
            item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()
        ]
        after_decision_updated_at = session.get(models.DecisionOutcome, seeded["second_decision_id"]).updated_at

    assert after_decision_ids == before_decision_ids
    assert after_interview_score_ids == before_interview_score_ids
    assert after_skills_summary_ids == before_skills_summary_ids
    assert after_decision_updated_at == before_decision_updated_at
