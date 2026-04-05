"""
Tests for P0 org environment setup:
- Answer-to-variable translation engine (org_environment.py)
- POST /api/orgs/{org_id}/environment endpoint
- Production path: _resolve_values_framework always returns a default
- Archetype-driven fatal risks (talenti_dimensions.py)
"""
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
        email="env-tester@example.com",
        password_hash=hash_password("password"),
        full_name="Env Tester",
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id)


# ── Full answer sets ──────────────────────────────────────────────────────────

FULL_OWNERSHIP_ANSWERS = {
    "q1_direction_style": "we_set_direction_and_people_own_it",
    "q2_success_archetype": "sets_direction_challenges_status_quo_drives_change",
    "q3_what_matters_most": "hitting_the_numbers_outcomes_above_all",
    "q4_decision_style": "we_move_fast_decide_with_70pct_info",
    "q5_conflict_tolerance": "we_expect_people_to_challenge_directly",
    "q6_bad_decision_response": "push_back_hard_and_change_the_outcome",
    "q7_role_clarity": "people_define_their_own_scope",
    "q8_handles_change": "we_thrive_in_chaos_and_figure_it_out",
    "q9_feedback_culture": "feedback_is_continuous_and_expected",
    "q10_growth_expectation": "managers_coach_and_people_are_expected_to_improve",
}

PROCESS_LED_ANSWERS = {
    "q1_direction_style": "we_tell_people_exactly_what_to_do",
    "q2_success_archetype": "reliable_follows_process_delivers_consistently",
    "q3_what_matters_most": "following_the_right_process_consistently",
    "q4_decision_style": "we_weigh_evidence_before_deciding",
    "q5_conflict_tolerance": "we_align_first_avoid_open_conflict",
    "q6_bad_decision_response": "raise_concern_privately_then_align",
    "q7_role_clarity": "roles_are_clearly_defined_with_process",
    "q8_handles_change": "we_plan_carefully_and_follow_the_plan",
    "q9_feedback_culture": "feedback_is_formal_review_cycle_only",
    "q10_growth_expectation": "people_are_expected_to_grow_on_their_own",
}

COACHABILITY_HARD_ANSWERS = {
    **PROCESS_LED_ANSWERS,
    "q10_growth_expectation": "coachability_is_a_hard_requirement_not_optional",
}


# ── Translation engine unit tests ─────────────────────────────────────────────

def _get_translator():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    clear_app_modules()
    from app.services.org_environment import translate_answers_to_environment
    return translate_answers_to_environment


def test_full_ownership_answers_produce_correct_variables():
    translate = _get_translator()
    result = translate(FULL_OWNERSHIP_ANSWERS)
    env = result.environment

    assert env["control_vs_autonomy"] == "full_ownership"
    assert env["high_performance_archetype"] == "directional_driver"
    assert env["outcome_vs_process"] == "results_first"
    assert env["decision_reality"] == "speed_led"
    assert env["conflict_style"] == "challenge_expected"
    assert env["ambiguity_load"] == "ambiguous"


def test_process_led_answers_produce_correct_variables():
    translate = _get_translator()
    result = translate(PROCESS_LED_ANSWERS)
    env = result.environment

    assert env["control_vs_autonomy"] == "execution_led"
    assert env["high_performance_archetype"] == "reliable_executor"
    assert env["outcome_vs_process"] == "process_led"
    assert env["decision_reality"] == "evidence_led"
    assert env["conflict_style"] == "alignment_focused"
    assert env["ambiguity_load"] == "well_defined"


def test_all_six_variables_always_resolved():
    translate = _get_translator()
    result = translate(FULL_OWNERSHIP_ANSWERS)
    required = {
        "control_vs_autonomy", "outcome_vs_process", "conflict_style",
        "decision_reality", "ambiguity_load", "high_performance_archetype",
    }
    assert set(result.environment.keys()) == required


def test_missing_questions_fall_back_to_defaults():
    translate = _get_translator()
    # Empty answers — all variables should default
    result = translate({})
    assert len(result.defaulted_variables) == 6
    # Default values are the balanced/guided set
    assert result.environment["control_vs_autonomy"] == "guided_ownership"
    assert result.environment["ambiguity_load"] == "evolving"


def test_unknown_question_id_is_ignored():
    translate = _get_translator()
    answers = {
        **FULL_OWNERSHIP_ANSWERS,
        "q99_nonexistent_question": "some_answer",
    }
    result = translate(answers)
    # Should produce same result as without the unknown question
    expected = translate(FULL_OWNERSHIP_ANSWERS)
    assert result.environment == expected.environment


def test_invalid_answer_value_treated_as_null():
    translate = _get_translator()
    answers = dict(FULL_OWNERSHIP_ANSWERS)
    answers["q1_direction_style"] = "not_a_valid_choice"
    result = translate(answers)
    # q1 should fall back to default
    assert "control_vs_autonomy" in result.defaulted_variables
    assert result.environment["control_vs_autonomy"] == "guided_ownership"


def test_secondary_signal_loses_to_primary():
    translate = _get_translator()
    # q5 (primary, weight=1.0) says challenge_expected
    # q6 (secondary, weight=0.5) says alignment_focused
    # Primary should win
    answers = dict(FULL_OWNERSHIP_ANSWERS)
    answers["q5_conflict_tolerance"] = "we_expect_people_to_challenge_directly"
    answers["q6_bad_decision_response"] = "raise_concern_privately_then_align"
    result = translate(answers)
    assert result.environment["conflict_style"] == "challenge_expected"


def test_both_signals_same_variable_primary_wins():
    translate = _get_translator()
    # q5=healthy_debate (primary), q6=challenge_expected (secondary)
    answers = dict(FULL_OWNERSHIP_ANSWERS)
    answers["q5_conflict_tolerance"] = "we_debate_ideas_respectfully"
    answers["q6_bad_decision_response"] = "push_back_hard_and_change_the_outcome"
    result = translate(answers)
    assert result.environment["conflict_style"] == "healthy_debate"


def test_lineage_signals_recorded():
    translate = _get_translator()
    result = translate(FULL_OWNERSHIP_ANSWERS)
    assert len(result.signals) > 0
    signal_variables = {s.variable for s in result.signals}
    # At minimum all 6 variables should appear in signal lineage
    assert "control_vs_autonomy" in signal_variables
    assert "high_performance_archetype" in signal_variables


def test_coachability_hard_requirement_adds_fatal_risk():
    translate = _get_translator()
    result = translate(COACHABILITY_HARD_ANSWERS)
    assert "feedback_defensive_or_dismissive" in result.extra_fatal_risks


def test_standard_coachability_no_fatal_risk():
    translate = _get_translator()
    result = translate(PROCESS_LED_ANSWERS)
    assert "feedback_defensive_or_dismissive" not in result.extra_fatal_risks


def test_raw_answers_preserved_in_result():
    translate = _get_translator()
    result = translate(FULL_OWNERSHIP_ANSWERS)
    for q_id, answer in FULL_OWNERSHIP_ANSWERS.items():
        assert result.raw_answers[q_id] == answer


# ── Archetype fatal risks (talenti_dimensions.py) ────────────────────────────

def test_archetype_fatal_risks_defined_for_all_archetypes():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from app.talenti_canonical import ARCHETYPE_FATAL_RISKS, get_archetype_fatal_risks
    for archetype in ["reliable_executor", "strong_owner", "directional_driver"]:
        risks = get_archetype_fatal_risks(archetype)
        assert isinstance(risks, list)
        assert len(risks) > 0, f"{archetype} has no fatal risks defined"


def test_unknown_archetype_returns_empty_list():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from app.talenti_canonical import get_archetype_fatal_risks
    assert get_archetype_fatal_risks("nonexistent_archetype") == []


def test_directional_driver_fatal_risks_include_conflict_avoidance():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from app.talenti_canonical import get_archetype_fatal_risks
    risks = get_archetype_fatal_risks("directional_driver")
    assert "challenge_conflict_avoidance" in risks
    assert "ambiguity_needs_clarity_to_proceed" in risks


def test_reliable_executor_fatal_risks_include_procrastination():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from app.talenti_canonical import get_archetype_fatal_risks
    risks = get_archetype_fatal_risks("reliable_executor")
    assert "execution_procrastination_or_drift" in risks


# ── high_performance_archetype ENV rule (talenti_dimensions.py) ───────────────

def test_archetype_rules_affect_dimension_thresholds():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from app.talenti_canonical import compute_dimension_requirements

    base_env = {
        "control_vs_autonomy": "guided_ownership",
        "outcome_vs_process": "balanced",
        "conflict_style": "healthy_debate",
        "decision_reality": "evidence_led",
        "ambiguity_load": "evolving",
    }

    executor_env = {**base_env, "high_performance_archetype": "reliable_executor"}
    driver_env = {**base_env, "high_performance_archetype": "directional_driver"}

    executor_reqs = compute_dimension_requirements(executor_env)
    driver_reqs = compute_dimension_requirements(driver_env)

    # Directional driver should require higher challenge than reliable executor
    assert driver_reqs["challenge"].pass_threshold > executor_reqs["challenge"].pass_threshold
    # Reliable executor should require higher execution than directional driver
    assert executor_reqs["execution"].pass_threshold >= driver_reqs["execution"].pass_threshold


# ── Production path: _resolve_values_framework always seeds default ───────────

def test_resolve_values_framework_returns_default_in_production():
    client = create_client()
    from app.api.orgs import _resolve_values_framework
    result = _resolve_values_framework(None)
    assert result is not None
    parsed = json.loads(result)
    assert "operating_environment" in parsed
    assert "taxonomy" in parsed
    assert parsed["taxonomy"]["taxonomy_id"] == "talenti_canonical_v2"


def test_new_org_has_values_framework_in_production():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    response = client.post(
        "/api/orgs",
        json={"name": "Prod Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    org_id = response.json()["id"]

    from app.db import SessionLocal
    from app.models import Organisation
    with SessionLocal() as db:
        org = db.get(Organisation, org_id)
        assert org.values_framework is not None
        vf = json.loads(org.values_framework)
        assert "operating_environment" in vf
        assert "taxonomy" in vf


# ── POST /api/orgs/{org_id}/environment endpoint ─────────────────────────────

def test_environment_setup_endpoint_returns_derived_variables():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    # Create org
    org_resp = client.post(
        "/api/orgs",
        json={"name": "Env Setup Test Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert org_resp.status_code == 200
    org_id = org_resp.json()["id"]

    # Submit environment setup
    response = client.post(
        f"/api/orgs/{org_id}/environment",
        json=FULL_OWNERSHIP_ANSWERS,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["org_id"] == org_id
    assert data["values_framework_updated"] is True
    env = data["derived_environment"]
    assert env["control_vs_autonomy"] == "full_ownership"
    assert env["high_performance_archetype"] == "directional_driver"
    assert env["ambiguity_load"] == "ambiguous"


def test_environment_setup_persists_to_org_values_framework():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    org_resp = client.post(
        "/api/orgs",
        json={"name": "Persist Test Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_resp.json()["id"]

    client.post(
        f"/api/orgs/{org_id}/environment",
        json=PROCESS_LED_ANSWERS,
        headers={"Authorization": f"Bearer {token}"},
    )

    from app.db import SessionLocal
    from app.models import Organisation
    with SessionLocal() as db:
        org = db.get(Organisation, org_id)
        vf = json.loads(org.values_framework)
        env = vf["operating_environment"]
        assert env["control_vs_autonomy"] == "execution_led"
        assert env["ambiguity_load"] == "well_defined"


def test_environment_setup_persists_audit_record():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    org_resp = client.post(
        "/api/orgs",
        json={"name": "Audit Test Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_resp.json()["id"]

    resp = client.post(
        f"/api/orgs/{org_id}/environment",
        json=FULL_OWNERSHIP_ANSWERS,
        headers={"Authorization": f"Bearer {token}"},
    )
    input_id = resp.json()["input_id"]

    from app.db import SessionLocal
    from app.models import OrgEnvironmentInput
    with SessionLocal() as db:
        record = db.get(OrgEnvironmentInput, input_id)
        assert record is not None
        raw = json.loads(record.raw_answers)
        assert raw["q1_direction_style"] == "we_set_direction_and_people_own_it"
        derived = json.loads(record.derived_environment)
        assert derived["control_vs_autonomy"] == "full_ownership"


def test_environment_setup_coachability_hard_adds_fatal_risk_to_framework():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    org_resp = client.post(
        "/api/orgs",
        json={"name": "Fatal Risk Test Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_resp.json()["id"]

    resp = client.post(
        f"/api/orgs/{org_id}/environment",
        json=COACHABILITY_HARD_ANSWERS,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert "feedback_defensive_or_dismissive" in resp.json()["extra_fatal_risks"]

    from app.db import SessionLocal
    from app.models import Organisation
    with SessionLocal() as db:
        org = db.get(Organisation, org_id)
        vf = json.loads(org.values_framework)
        fatal_risks = vf["operating_environment"]["fatal_risks"]
        assert "feedback_defensive_or_dismissive" in fatal_risks


def test_environment_setup_returns_signal_lineage():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    org_resp = client.post(
        "/api/orgs",
        json={"name": "Lineage Test Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_resp.json()["id"]

    resp = client.post(
        f"/api/orgs/{org_id}/environment",
        json=FULL_OWNERSHIP_ANSWERS,
        headers={"Authorization": f"Bearer {token}"},
    )
    signals = resp.json()["signals"]
    assert len(signals) > 0
    signal_variables = {s["variable"] for s in signals}
    assert "control_vs_autonomy" in signal_variables
    assert "high_performance_archetype" in signal_variables
    # Each signal has lineage fields
    for s in signals:
        assert "question_id" in s
        assert "answer" in s
        assert "derived_value" in s
        assert "weight" in s


def test_environment_setup_invalid_answer_returns_422():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    org_resp = client.post(
        "/api/orgs",
        json={"name": "Invalid Answer Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_resp.json()["id"]

    invalid_answers = dict(FULL_OWNERSHIP_ANSWERS)
    invalid_answers["q1_direction_style"] = "this_is_not_a_valid_choice"

    resp = client.post(
        f"/api/orgs/{org_id}/environment",
        json=invalid_answers,
        headers={"Authorization": f"Bearer {token}"},
    )
    # Pydantic Literal validation should reject this
    assert resp.status_code == 422


def test_environment_setup_requires_auth():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    org_resp = client.post(
        "/api/orgs",
        json={"name": "Auth Test Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_resp.json()["id"]

    # No auth header
    resp = client.post(f"/api/orgs/{org_id}/environment", json=FULL_OWNERSHIP_ANSWERS)
    assert resp.status_code == 401


def test_environment_setup_org_not_found_returns_404():
    client = create_client()
    from app.db import SessionLocal
    with SessionLocal() as db:
        _, token = _create_user_and_token(db)

    resp = client.post(
        "/api/orgs/nonexistent-org-id/environment",
        json=FULL_OWNERSHIP_ANSWERS,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (403, 404)
