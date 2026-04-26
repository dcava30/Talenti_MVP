import json
import os
import socket
import sys
from datetime import datetime

import pytest
from conftest import (
    backend_root,
    clear_app_modules,
    get_test_database_url,
    prepare_test_environment,
    reset_database_with_migrations,
)
from sqlalchemy import inspect
from sqlalchemy.engine import make_url


def _load_backend_modules(database_url: str | None = None):
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    if database_url is not None:
        os.environ["DATABASE_URL"] = database_url
    clear_app_modules()

    import app.db as db
    import app.models as models

    return db, models


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


def _seed_interview_context(db_session, models):
    reviewer = models.User(
        email="decision-reviewer@example.com",
        password_hash="hashed-password",
        full_name="Decision Reviewer",
    )
    candidate_user = models.User(
        email="decision-candidate@example.com",
        password_hash="hashed-password",
        full_name="Decision Candidate",
    )
    organisation = models.Organisation(name="Talenti Test Org")
    db_session.add_all([reviewer, candidate_user, organisation])
    db_session.flush()

    candidate = models.CandidateProfile(
        user_id=candidate_user.id,
        first_name="Test",
        last_name="Candidate",
        email="decision-candidate@example.com",
    )
    role = models.JobRole(
        organisation_id=organisation.id,
        title="Account Executive",
        status="active",
    )
    db_session.add_all([candidate, role])
    db_session.flush()

    application = models.Application(
        job_role_id=role.id,
        candidate_profile_id=candidate.id,
        status="submitted",
    )
    db_session.add(application)
    db_session.flush()

    interview = models.Interview(
        application_id=application.id,
        status="completed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    environment_input = models.OrgEnvironmentInput(
        organisation_id=organisation.id,
        raw_answers=json.dumps({"q1_direction_style": "we_set_direction_and_people_own_it"}),
        signals_json=json.dumps([{"variable": "control_vs_autonomy", "value": "full_ownership"}]),
        derived_environment=json.dumps({"control_vs_autonomy": "full_ownership"}),
        submitted_by=reviewer.id,
    )
    db_session.add_all([interview, environment_input])
    db_session.flush()

    return {
        "reviewer": reviewer,
        "organisation": organisation,
        "candidate": candidate,
        "role": role,
        "application": application,
        "interview": interview,
        "environment_input": environment_input,
    }


def test_decision_models_are_importable() -> None:
    _, models = _load_backend_modules()

    assert models.DecisionOutcome.__tablename__ == "decision_outcomes"
    assert models.DecisionDimensionEvaluation.__tablename__ == "decision_dimension_evaluations"
    assert models.DecisionSignalEvidence.__tablename__ == "decision_signal_evidence"
    assert models.DecisionRiskFlag.__tablename__ == "decision_risk_flags"
    assert models.DecisionAuditTrail.__tablename__ == "decision_audit_trail"
    assert models.DecisionPolicyVersion.__tablename__ == "decision_policy_versions"
    assert models.HumanReviewAction.__tablename__ == "human_review_actions"
    assert models.SkillsAssessmentSummary.__tablename__ == "skills_assessment_summaries"

    decision_columns = set(models.DecisionOutcome.__table__.columns.keys())
    assert "skills_score" not in decision_columns
    assert "skills_outcome" not in decision_columns
    assert "skills_summary_id" not in decision_columns
    assert "pass_fail" not in decision_columns
    assert "model_service_2_payload" not in decision_columns

    excluded_default = models.SkillsAssessmentSummary.__table__.c.excluded_from_tds_decisioning.default
    assert excluded_default is not None
    assert excluded_default.arg is True


def test_decision_schema_migration_creates_additive_tables() -> None:
    database_url = _require_postgres_test_database()
    reset_database_with_migrations(database_url)
    db, models = _load_backend_modules(database_url)
    inspector = inspect(db.engine)

    table_names = set(inspector.get_table_names())
    assert "interview_scores" in table_names
    assert "score_dimensions" in table_names
    assert "decision_outcomes" in table_names
    assert "decision_dimension_evaluations" in table_names
    assert "decision_signal_evidence" in table_names
    assert "decision_risk_flags" in table_names
    assert "decision_audit_trail" in table_names
    assert "decision_policy_versions" in table_names
    assert "human_review_actions" in table_names
    assert "skills_assessment_summaries" in table_names

    decision_columns = {column["name"] for column in inspector.get_columns("decision_outcomes")}
    assert "skills_score" not in decision_columns
    assert "skills_outcome" not in decision_columns
    assert "skills_summary_id" not in decision_columns
    assert "pass_fail" not in decision_columns
    assert "model_service_2_payload" not in decision_columns

    decision_indexes = {index["name"] for index in inspector.get_indexes("decision_outcomes")}
    assert "ix_decision_outcomes_decision_state" in decision_indexes
    assert "ix_decision_outcomes_created_at" in decision_indexes

    assert not hasattr(models.DecisionOutcome, "skills_score")
    assert not hasattr(models.DecisionOutcome, "skills_outcome")
    assert not hasattr(models.DecisionOutcome, "skills_summary_id")
    assert not hasattr(models.DecisionOutcome, "pass_fail")


def test_decision_schema_records_persist_separately_from_skills_summaries() -> None:
    database_url = _require_postgres_test_database()
    reset_database_with_migrations(database_url)
    db, models = _load_backend_modules(database_url)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)

        policy = models.DecisionPolicyVersion(
            organisation_id=seeded["organisation"].id,
            role_id=seeded["role"].id,
            policy_version="mvp1-behaviour-decides-v1",
            status="active",
            effective_from=datetime.utcnow(),
            policy_definition_json=json.dumps({"governing_rule": "Behaviour decides. Skills informs."}),
            critical_dimensions_json=json.dumps(["ownership", "execution"]),
            minimum_dimensions_json=json.dumps(["ownership", "execution", "challenge"]),
            priority_dimensions_json=json.dumps(["feedback"]),
        )
        session.add(policy)
        session.flush()

        decision = models.DecisionOutcome(
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            org_environment_input_id=seeded["environment_input"].id,
            decision_state="PROCEED_WITH_CONDITIONS",
            decision_valid=True,
            confidence="MEDIUM",
            confidence_gate_passed=True,
            integrity_status="AT_RISK",
            environment_profile_json=json.dumps({"control_vs_autonomy": "full_ownership"}),
            critical_dimensions_json=json.dumps(["ownership", "execution"]),
            minimum_dimensions_json=json.dumps(["ownership", "execution", "challenge"]),
            priority_dimensions_json=json.dumps(["feedback"]),
            evidence_gaps_json=json.dumps([]),
            invalid_signals_json=json.dumps(["signal_invalid"]),
            conflict_flags_json=json.dumps(["feedback_conflict"]),
            execution_floor_result_json=json.dumps({"passed": True, "reason": "clear"}),
            trade_off_statement="Behavioural evidence is usable with conditions.",
            conditions_json=json.dumps(["Collect references focused on feedback receptivity."]),
            rationale="Behavioural-only evaluation supports progress with follow-up.",
            audit_trace_json=json.dumps([{"code": "tds_rule_slice_1_enforced"}]),
            rule_version="tds-phase2-shadow-v1",
            policy_version=policy.policy_version,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(decision)
        session.flush()

        session.add_all(
            [
                models.DecisionDimensionEvaluation(
                    decision_id=decision.id,
                    dimension="ownership",
                    score_internal=1,
                    confidence="HIGH",
                    required_level="critical",
                    threshold_status="met",
                    outcome="pass",
                    evidence_summary_json=json.dumps({"summary": "Strong ownership evidence"}),
                    rationale="Consistent behavioural examples were provided.",
                ),
                models.DecisionSignalEvidence(
                    decision_id=decision.id,
                    dimension="ownership",
                    signal_code="ownership_repeatable_signal",
                    signal_status="VALID",
                    source_type="transcript_segment",
                    source_reference_json=json.dumps({"segment_id": "seg-1"}),
                    raw_excerpt_json=json.dumps({"excerpt": "I took ownership of the rollout."}),
                ),
                models.DecisionRiskFlag(
                    decision_id=decision.id,
                    risk_code="minimum_dimension_risk",
                    severity="MEDIUM",
                    source_dimension="feedback",
                    trigger_rule="minimum_dimension_threshold",
                    context_json=json.dumps({"score_internal": -1}),
                ),
                models.DecisionAuditTrail(
                    decision_id=decision.id,
                    event_type="decision_created",
                    event_at=datetime.utcnow(),
                    actor_type="system",
                    actor_user_id=seeded["reviewer"].id,
                    rule_version="tds-phase2-shadow-v1",
                    policy_version=policy.policy_version,
                    event_payload_json=json.dumps({"decision_state": decision.decision_state}),
                ),
                models.HumanReviewAction(
                    decision_id=decision.id,
                    action_type="HUMAN_REVIEW",
                    review_outcome="HOLD_FOR_FURTHER_REVIEW",
                    reason="Human reviewer wants more behavioural evidence on feedback.",
                    reviewed_by=seeded["reviewer"].id,
                    notes_json=json.dumps({"note": "Preserve original system outcome."}),
                    display_delta_json=json.dumps({"badge": "Human review requested"}),
                ),
                models.SkillsAssessmentSummary(
                    interview_id=seeded["interview"].id,
                    candidate_id=seeded["candidate"].id,
                    role_id=seeded["role"].id,
                    organisation_id=seeded["organisation"].id,
                    observed_competencies_json=json.dumps(["discovery", "pipeline_management"]),
                    competency_coverage_json=json.dumps({"required": 4, "observed": 2}),
                    skill_gaps_json=json.dumps(["meddic", "forecasting"]),
                    evidence_strength="MEDIUM",
                    confidence="MEDIUM",
                    source_references_json=json.dumps([{"service": "model-service-2"}]),
                    human_readable_summary="Candidate shows partial evidence against role competencies.",
                    requires_human_review=True,
                    model_version="skills-ms2-v1",
                ),
            ]
        )
        session.commit()
        session.refresh(decision)

        persisted_decision = session.get(models.DecisionOutcome, decision.id)
        assert persisted_decision is not None
        assert persisted_decision.decision_state == "PROCEED_WITH_CONDITIONS"
        assert persisted_decision.decision_valid is True
        assert persisted_decision.policy_version == "mvp1-behaviour-decides-v1"
        assert len(persisted_decision.dimension_evaluations) == 1
        assert len(persisted_decision.signal_evidence_items) == 1
        assert len(persisted_decision.risk_flags) == 1
        assert len(persisted_decision.audit_trail_entries) == 1
        assert len(persisted_decision.human_review_actions) == 1

        persisted_policy = session.get(models.DecisionPolicyVersion, policy.id)
        assert persisted_policy is not None
        assert persisted_policy.policy_version == "mvp1-behaviour-decides-v1"

        skills_summary = session.query(models.SkillsAssessmentSummary).filter_by(interview_id=seeded["interview"].id).one()
        assert skills_summary.excluded_from_tds_decisioning is True
        assert skills_summary.requires_human_review is True

        decision_columns = set(models.DecisionOutcome.__table__.columns.keys())
        assert "skills_score" not in decision_columns
        assert "skills_outcome" not in decision_columns
        assert "skills_summary_id" not in decision_columns
        assert "pass_fail" not in decision_columns
        assert "model_service_2_payload" not in decision_columns
