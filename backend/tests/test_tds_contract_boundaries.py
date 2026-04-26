from __future__ import annotations

import sys

from fastapi.testclient import TestClient

import test_decision_human_review_api as human_review_tests
import test_decision_inspection_api as decision_inspection_tests
import test_recruiter_decision_api as recruiter_decision_tests
import test_recruiter_skills_assessment_summary_api as recruiter_skills_tests
import test_shortlist_quarantine as shortlist_quarantine_tests
import test_skills_assessment_inspection_api as skills_inspection_tests
import test_tds_shadow_comparison_api as shadow_comparison_tests
from conftest import backend_root, prepare_test_environment

from tds_contract_helpers import (
    DECISION_LEAKAGE_FIELDS,
    LEGACY_HIRING_OUTCOME_LANGUAGE,
    OVERRIDE_LANGUAGE,
    RANKING_LEAKAGE_FIELDS,
    SKILLS_LEAKAGE_FIELDS,
    TDS_FLAG_NAMES,
    assert_payload_excludes_keys,
    assert_payload_excludes_serialized_terms,
    assert_payload_excludes_strings,
)


def test_tds_flag_defaults_are_false_and_docs_are_consistent() -> None:
    prepare_test_environment()
    if str(backend_root()) not in sys.path:
        sys.path.insert(0, str(backend_root()))
    import app.core.config as config

    config_defaults = {
        flag_name: config.Settings.model_fields[flag_name.lower()].default
        for flag_name in TDS_FLAG_NAMES
    }
    assert config_defaults == {flag_name: False for flag_name in TDS_FLAG_NAMES}

    env_example = (backend_root().parent / ".env.example").read_text(encoding="utf-8")
    backend_readme = (backend_root() / "README.md").read_text(encoding="utf-8")

    for flag_name in TDS_FLAG_NAMES:
        assert f"{flag_name}=false" in env_example
        assert flag_name in backend_readme


def test_recruiter_decision_route_returns_404_when_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        recruiter_decision_tests._load_modules(recruiter_api_enabled=False)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = recruiter_decision_tests._seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recruiter decision API is not available."


def test_recruiter_skills_summary_route_returns_404_when_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        recruiter_skills_tests._load_modules(recruiter_skills_api_enabled=False)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = recruiter_skills_tests._seed_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recruiter skills assessment summary API is not available."


def test_internal_decision_inspection_route_returns_404_when_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        decision_inspection_tests._load_modules(inspection_enabled=False)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = decision_inspection_tests._seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/decisions/interviews/{seeded['interview_id']}/latest",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Decision inspection API is not available."


def test_internal_skills_inspection_route_returns_404_when_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        skills_inspection_tests._load_modules(inspection_enabled=False)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = skills_inspection_tests._seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/interviews/{seeded['interview_id']}/latest",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Skills assessment summary inspection API is not available."


def test_shadow_comparison_route_returns_404_when_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = (
        shadow_comparison_tests._load_modules(comparison_enabled=False)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = shadow_comparison_tests._seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "TDS shadow comparison API is not available."


def test_human_review_routes_return_404_when_flag_disabled() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = (
        human_review_tests._load_modules(human_review_api_enabled=False)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = human_review_tests._seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    url = f"/api/v1/decisions/{seeded['decision_id']}/human-review"
    headers = {"Authorization": f"Bearer {seeded['admin_token']}"}

    get_response = client.get(url, headers=headers)
    post_response = client.post(
        url,
        headers=headers,
        json={
            "action_type": "HUMAN_REVIEW",
            "review_outcome": "ACKNOWLEDGED",
            "reason": "Human review recorded.",
        },
    )

    assert get_response.status_code == 404
    assert post_response.status_code == 404
    assert get_response.json()["detail"] == "Decision human review API is not available."
    assert post_response.json()["detail"] == "Decision human review API is not available."


def test_recruiter_decision_response_stays_behavioural_only() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        recruiter_decision_tests._load_modules(recruiter_api_enabled=True)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = recruiter_decision_tests._seed_recruiter_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/decision",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert_payload_excludes_keys(payload, SKILLS_LEAKAGE_FIELDS | RANKING_LEAKAGE_FIELDS)
    assert "audit_trace" not in payload
    assert_payload_excludes_strings(payload, LEGACY_HIRING_OUTCOME_LANGUAGE)


def test_recruiter_skills_summary_response_stays_non_decisional_and_forces_exclusion() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        recruiter_skills_tests._load_modules(recruiter_skills_api_enabled=True)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = recruiter_skills_tests._seed_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        summary = session.get(models.SkillsAssessmentSummary, seeded["latest_summary_id"])
        assert summary is not None
        summary.excluded_from_tds_decisioning = False
        session.commit()

    response = client.get(
        f"/api/v1/interviews/{seeded['interview_id']}/skills-assessment-summary",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["excluded_from_tds_decisioning"] is True
    assert_payload_excludes_keys(payload, DECISION_LEAKAGE_FIELDS | RANKING_LEAKAGE_FIELDS)
    assert_payload_excludes_serialized_terms(payload, LEGACY_HIRING_OUTCOME_LANGUAGE)


def test_internal_decision_inspection_response_excludes_skills_and_ranking_fields() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        decision_inspection_tests._load_modules(inspection_enabled=True)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = decision_inspection_tests._seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.get(
        f"/api/v1/internal/decisions/{seeded['second_decision_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert_payload_excludes_keys(payload, SKILLS_LEAKAGE_FIELDS | RANKING_LEAKAGE_FIELDS)
    assert_payload_excludes_strings(payload, LEGACY_HIRING_OUTCOME_LANGUAGE)


def test_internal_skills_inspection_response_excludes_decision_and_ranking_fields() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service = (
        skills_inspection_tests._load_modules(inspection_enabled=True)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = skills_inspection_tests._seed_inspection_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        summary = session.get(models.SkillsAssessmentSummary, seeded["latest_summary_id"])
        assert summary is not None
        summary.excluded_from_tds_decisioning = False
        session.commit()

    response = client.get(
        f"/api/v1/internal/skills-assessment-summaries/{seeded['latest_summary_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["excluded_from_tds_decisioning"] is True
    assert_payload_excludes_keys(payload, DECISION_LEAKAGE_FIELDS | RANKING_LEAKAGE_FIELDS)
    assert_payload_excludes_serialized_terms(payload, LEGACY_HIRING_OUTCOME_LANGUAGE)


def test_shadow_comparison_keeps_legacy_tds_and_skills_sections_separate() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = (
        shadow_comparison_tests._load_modules(comparison_enabled=True)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = shadow_comparison_tests._seed_comparison_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )
        summary = session.get(models.SkillsAssessmentSummary, seeded["aligned_skills_summary_id"])
        assert summary is not None
        summary.source_references_json = (
            '[{"source":"legacy-ms2","ranking":99,"decision_state":"DO_NOT_PROCEED","skills_outcome":"FAIL"}]'
        )
        summary.human_readable_summary = "PASS REVIEW FAIL should not affect comparison status."
        session.commit()

    response = client.get(
        f"/api/v1/internal/tds-shadow-comparison/interviews/{seeded['aligned_interview_id']}",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "interview_id",
        "candidate_id",
        "role_id",
        "organisation_id",
        "interview_created_at",
        "legacy_score_summary",
        "tds_decision_summary",
        "skills_summary_status",
        "comparison_result",
    }
    assert payload["comparison_result"]["comparison_status"] == "aligned"
    assert payload["skills_summary_status"]["excluded_from_tds_decisioning"] is True
    assert payload["tds_decision_summary"]["decision_state"] == "PROCEED"
    assert payload["legacy_score_summary"]["recommendation"] == "proceed"


def test_human_review_responses_avoid_override_language_and_preserve_system_decision() -> None:
    db, models, main, security, decision_layer, decision_persistence, skills_service, _ = (
        human_review_tests._load_modules(human_review_api_enabled=True)
    )
    client = TestClient(main.app)

    with db.SessionLocal() as session:
        seeded = human_review_tests._seed_human_review_fixture(
            session, models, security, decision_layer, decision_persistence, skills_service
        )

    response = client.post(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
        json={
            "action_type": "EXCEPTION_RECORDED",
            "review_outcome": "PROCEED_WITH_HUMAN_EXCEPTION",
            "reason": "Human exception recorded without replacing the system decision.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_decision_state"] == seeded["decision_state"]
    assert_payload_excludes_keys(payload, OVERRIDE_LANGUAGE)
    assert_payload_excludes_strings(payload, OVERRIDE_LANGUAGE)

    list_response = client.get(
        f"/api/v1/decisions/{seeded['decision_id']}/human-review",
        headers={"Authorization": f"Bearer {seeded['admin_token']}"},
    )

    assert list_response.status_code == 200
    assert_payload_excludes_keys(list_response.json(), OVERRIDE_LANGUAGE)
    assert_payload_excludes_strings(list_response.json(), OVERRIDE_LANGUAGE)

    with db.SessionLocal() as session:
        decision = session.get(models.DecisionOutcome, seeded["decision_id"])
        assert decision is not None
        assert decision.decision_state == seeded["decision_state"]


def test_shortlist_quarantine_response_has_no_ranking_payload_when_enabled() -> None:
    app, _ = shortlist_quarantine_tests._load_shortlist_app(quarantine_enabled=True)
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
    payload = response.json()
    assert_payload_excludes_keys(payload, RANKING_LEAKAGE_FIELDS | {"score"})
