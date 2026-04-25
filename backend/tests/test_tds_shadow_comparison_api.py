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

FORBIDDEN_RESPONSE_KEYS = {
    "match_score",
    "ranking",
    "shortlist_position",
    "best_candidate",
    "best_candidate_id",
    "worst_candidate",
    "worst_candidate_id",
    "hiring_outcome",
}
FORBIDDEN_STRING_VALUES = {"PASS", "REVIEW", "FAIL"}


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


def _load_modules(*, comparison_enabled: bool):
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    database_url = _require_postgres_test_database()
    prepare_test_environment()
    import os

    os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_SHADOW_COMPARISON_API_ENABLED"] = "true" if comparison_enabled else "false"
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
    import app.services.tds_shadow_comparison as tds_shadow_comparison

    importlib.reload(config)
    importlib.reload(security)
    importlib.reload(db)
    importlib.reload(models)
    importlib.reload(decision_layer)
    importlib.reload(decision_persistence)
    importlib.reload(skills_assessment_summary)
    importlib.reload(tds_shadow_comparison)
    importlib.reload(main)

    return (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_assessment_summary,
        tds_shadow_comparison,
    )


def _dimension(
    score: int = 1,
    confidence: str = "HIGH",
    *,
    valid_signals: list[str] | None = None,
) -> dict[str, object]:
    return {
        "score_internal": score,
        "confidence": confidence,
        "evidence_summary": "Observed behavioural evidence.",
        "rationale": "Deterministic behavioural rationale.",
        "valid_signals": list(["repeatable_signal"] if valid_signals is None else valid_signals),
        "invalid_signals": [],
        "conflict_flags": [],
    }


def _decision_payload(
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    dimensions: dict[str, dict[str, object] | None] | None = None,
) -> dict[str, object]:
    evidence = {
        "ownership": _dimension(),
        "execution": _dimension(),
        "challenge": _dimension(),
        "ambiguity": _dimension(),
        "feedback": _dimension(),
    }
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
            {"dimension": dimension, **payload}
            for dimension, payload in evidence.items()
        ],
        "critical_dimensions": ["ownership", "execution"],
        "minimum_dimensions": ["ownership", "execution", "challenge", "ambiguity", "feedback"],
        "priority_dimensions": ["challenge"],
        "rule_version": "tds-phase7-shadow-v1",
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


def _seed_interview(
    session,
    models,
    *,
    role_id: str,
    candidate_id: str,
    created_at: datetime,
):
    application = models.Application(
        job_role_id=role_id,
        candidate_profile_id=candidate_id,
        status="submitted",
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(application)
    session.flush()
    interview = models.Interview(
        application_id=application.id,
        status="completed",
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(interview)
    session.flush()
    return application, interview


def _seed_legacy_score(
    session,
    models,
    *,
    interview_id: str,
    created_at: datetime,
    recommendation: str,
    skills_outcome: str = "PASS",
):
    score = models.InterviewScore(
        interview_id=interview_id,
        culture_fit_score=80,
        skills_score=92,
        skills_outcome=skills_outcome,
        overall_alignment="strong_fit" if recommendation == "proceed" else "weak_fit",
        overall_risk_level="low" if recommendation == "proceed" else "high",
        recommendation=recommendation,
        summary="Legacy recommendation context only.",
        service2_raw=json.dumps({"match_score": 92, "ranking": 1, "skills_outcome": skills_outcome}),
        created_at=created_at,
    )
    session.add(score)
    session.flush()
    return score


def _seed_decision(
    session,
    decision_layer,
    decision_persistence,
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    actor_user_id: str,
    created_at: datetime,
    dimensions: dict[str, dict[str, object] | None] | None = None,
):
    result = decision_layer.evaluate_behavioural_decision(
        _decision_payload(
            interview_id=interview_id,
            candidate_id=candidate_id,
            role_id=role_id,
            organisation_id=organisation_id,
            dimensions=dimensions,
        )
    )
    decision = decision_persistence.create_decision_outcome_from_result(
        session,
        decision_result=result,
        interview_id=interview_id,
        candidate_id=candidate_id,
        role_id=role_id,
        organisation_id=organisation_id,
        environment_profile={"control_vs_autonomy": "full_ownership"},
        actor_user_id=actor_user_id,
    )
    decision.created_at = created_at
    decision.updated_at = created_at
    session.flush()
    return decision


def _seed_skills_summary(
    session,
    skills_service,
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    created_at: datetime,
):
    summary = skills_service.create_skills_assessment_summary(
        session,
        interview_id=interview_id,
        candidate_id=candidate_id,
        role_id=role_id,
        organisation_id=organisation_id,
        observed_competencies=["discovery"],
        competency_coverage={"required": 5, "observed": 2},
        skill_gaps=["forecasting"],
        evidence_strength="MEDIUM",
        confidence="MEDIUM",
        source_references=[{"source": "legacy-ms2", "skills_outcome": "PASS", "ranking": 1}],
        human_readable_summary="Skills evidence remains informational only.",
        requires_human_review=True,
        excluded_from_tds_decisioning=True,
        model_version="skills-ms2-v1",
    )
    summary.created_at = created_at
    summary.updated_at = created_at
    session.flush()
    return summary


def _collect_keys_and_strings(value: Any) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    strings: list[str] = []

    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            nested_keys, nested_strings = _collect_keys_and_strings(nested)
            keys.update(nested_keys)
            strings.extend(nested_strings)
        return keys, strings

    if isinstance(value, list):
        for nested in value:
            nested_keys, nested_strings = _collect_keys_and_strings(nested)
            keys.update(nested_keys)
            strings.extend(nested_strings)
        return keys, strings

    if isinstance(value, str):
        strings.append(value)

    return keys, strings


def _assert_non_ranking_response(payload: Any) -> None:
    keys, strings = _collect_keys_and_strings(payload)
    assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(keys)
    assert FORBIDDEN_STRING_VALUES.isdisjoint(set(strings))


def _seed_comparison_fixture(
    session,
    models,
    security,
    decision_layer,
    decision_persistence,
    skills_service,
):
    admin_user = _create_user(
        session, models, security, email="comparison-admin@example.com", full_name="Comparison Admin"
    )
    owner_user = _create_user(
        session, models, security, email="comparison-owner@example.com", full_name="Comparison Owner"
    )
    member_user = _create_user(
        session, models, security, email="comparison-member@example.com", full_name="Comparison Member"
    )
    other_admin_user = _create_user(
        session,
        models,
        security,
        email="comparison-other-admin@example.com",
        full_name="Comparison Other Admin",
    )
    candidate_user = _create_user(
        session,
        models,
        security,
        email="comparison-candidate@example.com",
        full_name="Comparison Candidate",
    )

    organisation = models.Organisation(name="Talenti Comparison Org")
    other_organisation = models.Organisation(name="Talenti Comparison Other Org")
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
        first_name="Morgan",
        last_name="Comparator",
        email="comparison-candidate@example.com",
    )
    session.add(candidate)
    session.flush()

    role = models.JobRole(
        organisation_id=organisation.id,
        title="Enterprise AE",
        description="Own revenue outcomes.",
        status="active",
    )
    other_role = models.JobRole(
        organisation_id=other_organisation.id,
        title="CS Lead",
        description="Own customer outcomes.",
        status="active",
    )
    session.add_all([role, other_role])
    session.flush()

    base_time = datetime.utcnow()
    created_times = [base_time - timedelta(minutes=index) for index in range(1, 9)]

    aligned_application, aligned_interview = _seed_interview(
        session,
        models,
        role_id=role.id,
        candidate_id=candidate.id,
        created_at=created_times[0],
    )
    more_cautious_application, more_cautious_interview = _seed_interview(
        session,
        models,
        role_id=role.id,
        candidate_id=candidate.id,
        created_at=created_times[1],
    )
    less_cautious_application, less_cautious_interview = _seed_interview(
        session,
        models,
        role_id=role.id,
        candidate_id=candidate.id,
        created_at=created_times[2],
    )
    insufficient_application, insufficient_interview = _seed_interview(
        session,
        models,
        role_id=role.id,
        candidate_id=candidate.id,
        created_at=created_times[3],
    )
    legacy_only_application, legacy_only_interview = _seed_interview(
        session,
        models,
        role_id=role.id,
        candidate_id=candidate.id,
        created_at=created_times[4],
    )
    tds_only_application, tds_only_interview = _seed_interview(
        session,
        models,
        role_id=role.id,
        candidate_id=candidate.id,
        created_at=created_times[5],
    )
    missing_application, missing_interview = _seed_interview(
        session,
        models,
        role_id=role.id,
        candidate_id=candidate.id,
        created_at=created_times[6],
    )
    other_application, other_interview = _seed_interview(
        session,
        models,
        role_id=other_role.id,
        candidate_id=candidate.id,
        created_at=created_times[7],
    )

    _seed_legacy_score(
        session,
        models,
        interview_id=aligned_interview.id,
        created_at=created_times[0] + timedelta(seconds=10),
        recommendation="proceed",
        skills_outcome="PASS",
    )
    aligned_decision = _seed_decision(
        session,
        decision_layer,
        decision_persistence,
        interview_id=aligned_interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        actor_user_id=admin_user.id,
        created_at=created_times[0] + timedelta(seconds=20),
    )
    aligned_skills = _seed_skills_summary(
        session,
        skills_service,
        interview_id=aligned_interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        created_at=created_times[0] + timedelta(seconds=30),
    )

    _seed_legacy_score(
        session,
        models,
        interview_id=more_cautious_interview.id,
        created_at=created_times[1] + timedelta(seconds=10),
        recommendation="proceed",
        skills_outcome="REVIEW",
    )
    more_cautious_decision = _seed_decision(
        session,
        decision_layer,
        decision_persistence,
        interview_id=more_cautious_interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        actor_user_id=admin_user.id,
        created_at=created_times[1] + timedelta(seconds=20),
        dimensions={"feedback": _dimension(score=-1, confidence="MEDIUM")},
    )

    _seed_legacy_score(
        session,
        models,
        interview_id=less_cautious_interview.id,
        created_at=created_times[2] + timedelta(seconds=10),
        recommendation="reject",
        skills_outcome="FAIL",
    )
    less_cautious_decision = _seed_decision(
        session,
        decision_layer,
        decision_persistence,
        interview_id=less_cautious_interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        actor_user_id=admin_user.id,
        created_at=created_times[2] + timedelta(seconds=20),
    )

    _seed_legacy_score(
        session,
        models,
        interview_id=insufficient_interview.id,
        created_at=created_times[3] + timedelta(seconds=10),
        recommendation="proceed",
        skills_outcome="PASS",
    )
    insufficient_decision = _seed_decision(
        session,
        decision_layer,
        decision_persistence,
        interview_id=insufficient_interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        actor_user_id=admin_user.id,
        created_at=created_times[3] + timedelta(seconds=20),
        dimensions={"ownership": None},
    )

    legacy_only_score = _seed_legacy_score(
        session,
        models,
        interview_id=legacy_only_interview.id,
        created_at=created_times[4] + timedelta(seconds=10),
        recommendation="caution",
        skills_outcome="PASS",
    )

    tds_only_decision = _seed_decision(
        session,
        decision_layer,
        decision_persistence,
        interview_id=tds_only_interview.id,
        candidate_id=candidate.id,
        role_id=role.id,
        organisation_id=organisation.id,
        actor_user_id=admin_user.id,
        created_at=created_times[5] + timedelta(seconds=20),
        dimensions={"ownership": _dimension(score=-2, confidence="MEDIUM")},
    )

    other_org_decision = _seed_decision(
        session,
        decision_layer,
        decision_persistence,
        interview_id=other_interview.id,
        candidate_id=candidate.id,
        role_id=other_role.id,
        organisation_id=other_organisation.id,
        actor_user_id=other_admin_user.id,
        created_at=created_times[7] + timedelta(seconds=20),
    )

    session.commit()

    return {
        "organisation_id": organisation.id,
        "other_organisation_id": other_organisation.id,
        "role_id": role.id,
        "other_role_id": other_role.id,
        "aligned_interview_id": aligned_interview.id,
        "more_cautious_interview_id": more_cautious_interview.id,
        "less_cautious_interview_id": less_cautious_interview.id,
        "insufficient_interview_id": insufficient_interview.id,
        "legacy_only_interview_id": legacy_only_interview.id,
        "tds_only_interview_id": tds_only_interview.id,
        "missing_interview_id": missing_interview.id,
        "other_interview_id": other_interview.id,
        "aligned_decision_id": aligned_decision.id,
        "aligned_skills_summary_id": aligned_skills.id,
        "more_cautious_decision_id": more_cautious_decision.id,
        "less_cautious_decision_id": less_cautious_decision.id,
        "insufficient_decision_id": insufficient_decision.id,
        "legacy_only_score_id": legacy_only_score.id,
        "tds_only_decision_id": tds_only_decision.id,
        "other_org_decision_id": other_org_decision.id,
        "admin_token": security.create_access_token(admin_user.id),
        "owner_token": security.create_access_token(owner_user.id),
        "member_token": security.create_access_token(member_user.id),
        "other_admin_token": security.create_access_token(other_admin_user.id),
    }


def test_shadow_comparison_api_returns_404_when_feature_flag_disabled() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=False)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "TDS shadow comparison API is not available."


def test_shadow_comparison_api_requires_authentication() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing token"


@pytest.mark.parametrize("token_key", ["member_token", "other_admin_token"])
def test_shadow_comparison_api_rejects_non_admin_or_wrong_org_access(token_key: str) -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only organisation admins can access this resource."


@pytest.mark.parametrize("token_key", ["admin_token", "owner_token"])
def test_shadow_comparison_api_allows_admin_and_owner_reads(token_key: str) -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}",
        headers={"Authorization": f"Bearer {seeded[token_key]}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparison_result"]["comparison_status"] == "aligned"
    _assert_non_ranking_response(payload)


@pytest.mark.parametrize(
    ("seed_key", "expected_status"),
    [
        ("aligned_interview_id", "aligned"),
        ("more_cautious_interview_id", "shifted_more_cautious"),
        ("less_cautious_interview_id", "shifted_less_cautious"),
        ("legacy_only_interview_id", "legacy_only"),
        ("tds_only_interview_id", "tds_only"),
        ("missing_interview_id", "insufficient_data"),
    ],
)
def test_interview_shadow_comparison_statuses(seed_key: str, expected_status: str) -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded[seed_key]}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparison_result"]["comparison_status"] == expected_status
    _assert_non_ranking_response(payload)


def test_tds_insufficient_evidence_is_not_treated_as_reject() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['insufficient_interview_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tds_decision_summary"]["decision_state"] == "INSUFFICIENT_EVIDENCE"
    assert payload["comparison_result"]["comparison_status"] == "insufficient_evidence"
    assert "reject" not in " ".join(payload["comparison_result"]["comparison_notes"]).lower()


def test_skills_summary_stays_separate_from_behavioural_comparison() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skills_summary_status"]["status"] == "present"
    assert payload["skills_summary_status"]["requires_human_review"] is True
    assert payload["skills_summary_status"]["excluded_from_tds_decisioning"] is True
    assert payload["comparison_result"]["comparison_status"] == "aligned"
    assert payload["legacy_score_summary"]["legacy_skills_outcome_status"] == "observed"
    assert "skills_summary_status" in payload
    assert "PASS" not in json.dumps(payload)
    assert "REVIEW" not in json.dumps(payload)
    assert "FAIL" not in json.dumps(payload)


def test_role_shadow_comparison_list_returns_compact_rows_with_pagination_and_created_order() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    first_page = client.get(
        f"/api/v1/internal/tds-shadow-comparison/roles/{seeded['role_id']}?limit=2&offset=0",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )
    second_page = client.get(
        f"/api/v1/internal/tds-shadow-comparison/roles/{seeded['role_id']}?limit=2&offset=2",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    first_payload = first_page.json()
    second_payload = second_page.json()
    assert len(first_payload) == 2
    assert len(second_payload) == 2
    assert first_payload[0]["interview_id"] == seeded["aligned_interview_id"]
    assert first_payload[1]["interview_id"] == seeded["more_cautious_interview_id"]
    assert second_payload[0]["interview_id"] == seeded["less_cautious_interview_id"]
    assert second_payload[1]["interview_id"] == seeded["insufficient_interview_id"]
    _assert_non_ranking_response(first_payload)
    _assert_non_ranking_response(second_payload)


def test_role_shadow_comparison_summary_counts_expected_buckets() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/roles/{seeded['role_id']}/summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "role_id": seeded["role_id"],
        "organisation_id": seeded["organisation_id"],
        "total_interviews": 7,
        "with_legacy_score": 5,
        "with_tds_decision": 5,
        "with_skills_summary": 1,
        "aligned": 1,
        "shifted_more_cautious": 1,
        "shifted_less_cautious": 1,
        "insufficient_evidence": 1,
        "legacy_only": 1,
        "tds_only": 1,
        "missing_both": 1,
    }
    _assert_non_ranking_response(payload)


def test_org_shadow_comparison_summary_is_scoped_to_org() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/orgs/{seeded['organisation_id']}/summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["organisation_id"] == seeded["organisation_id"]
    assert payload["total_interviews"] == 7


def test_shadow_comparison_endpoints_have_no_write_side_effects() -> None:
    (
        db,
        models,
        main,
        security,
        decision_layer,
        decision_persistence,
        skills_service,
        _comparison_service,
    ) = _load_modules(comparison_enabled=True)
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = _seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        before_decision_ids = [item.id for item in session.execute(select(models.DecisionOutcome)).scalars()]
        before_skills_ids = [
            item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()
        ]
        before_score_ids = [item.id for item in session.execute(select(models.InterviewScore)).scalars()]

    response_one = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )
    response_two = client.get(
        f"/api/v1/internal/tds-shadow-comparison/roles/{seeded['role_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )
    response_three = client.get(
        f"/api/v1/internal/tds-shadow-comparison/roles/{seeded['role_id']}/summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    assert response_three.status_code == 200

    with db.SessionLocal() as session:
        after_decision_ids = [item.id for item in session.execute(select(models.DecisionOutcome)).scalars()]
        after_skills_ids = [item.id for item in session.execute(select(models.SkillsAssessmentSummary)).scalars()]
        after_score_ids = [item.id for item in session.execute(select(models.InterviewScore)).scalars()]

    assert after_decision_ids == before_decision_ids
    assert after_skills_ids == before_skills_ids
    assert after_score_ids == before_score_ids
