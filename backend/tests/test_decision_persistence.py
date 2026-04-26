import importlib
import socket
import sys
from datetime import datetime, timedelta

import pytest
from conftest import (
    backend_root,
    clear_app_modules,
    get_test_database_url,
    prepare_test_environment,
    reset_database_with_migrations,
)
from sqlalchemy import select
from sqlalchemy.engine import make_url


CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]


def _load_modules(database_url: str | None = None):
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    if database_url is not None:
        import os

        os.environ["DATABASE_URL"] = database_url
    clear_app_modules()

    import app.db as db
    import app.models as models
    import app.services.decision_layer as decision_layer
    import app.services.decision_persistence as decision_persistence
    import app.services.json_text as json_text
    import app.services.skills_assessment_summary as skills_assessment_summary

    importlib.reload(db)
    importlib.reload(models)
    importlib.reload(decision_layer)
    importlib.reload(json_text)
    importlib.reload(decision_persistence)
    importlib.reload(skills_assessment_summary)
    return db, models, decision_layer, decision_persistence, skills_assessment_summary, json_text


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
        email="tds-reviewer@example.com",
        password_hash="hashed-password",
        full_name="TDS Reviewer",
    )
    candidate_user = models.User(
        email="tds-candidate@example.com",
        password_hash="hashed-password",
        full_name="TDS Candidate",
    )
    organisation = models.Organisation(name="Talenti TDS Test Org")
    db_session.add_all([reviewer, candidate_user, organisation])
    db_session.flush()

    candidate = models.CandidateProfile(
        user_id=candidate_user.id,
        first_name="Taylor",
        last_name="Decision",
        email="tds-candidate@example.com",
    )
    role = models.JobRole(
        organisation_id=organisation.id,
        title="Customer Success Manager",
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
        raw_answers='{"q1_direction_style":"we_set_direction_and_people_own_it"}',
        signals_json='[{"variable":"control_vs_autonomy","value":"full_ownership"}]',
        derived_environment='{"control_vs_autonomy":"full_ownership","outcome_vs_process":"results_first"}',
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


def _base_payload(
    *,
    dimensions: dict[str, dict[str, object] | None] | None = None,
    critical_dimensions: list[str] | None = None,
    minimum_dimensions: list[str] | None = None,
    priority_dimensions: list[str] | None = None,
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
        "interview_id": "shadow-int-1",
        "candidate_id": "shadow-cand-1",
        "role_id": "shadow-role-1",
        "organisation_id": "shadow-org-1",
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
        "critical_dimensions": critical_dimensions if critical_dimensions is not None else ["ownership", "execution"],
        "minimum_dimensions": minimum_dimensions if minimum_dimensions is not None else list(CANONICAL_DIMENSIONS),
        "priority_dimensions": priority_dimensions if priority_dimensions is not None else ["challenge"],
        "rule_version": "tds-phase2-shadow-v1",
        "policy_version": "mvp1-behaviour-decides-v1",
    }


def test_json_text_helpers_round_trip_deterministically_and_handle_none() -> None:
    _, _, _, _, _, json_text = _load_modules()

    first = {"b": [3, 2, 1], "a": {"z": "last", "m": "middle"}}
    second = {"a": {"m": "middle", "z": "last"}, "b": [3, 2, 1]}

    dumped_first = json_text.json_text_dumps(first)
    dumped_second = json_text.json_text_dumps(second)

    assert dumped_first == dumped_second
    assert json_text.json_text_loads(dumped_first, default={}) == second
    assert json_text.json_text_dumps(None) is None
    assert json_text.json_text_loads(None, default={"fallback": True}) == {"fallback": True}


def test_can_persist_behavioural_decision_output_without_skills_data() -> None:
    database_url = _require_postgres_test_database()
    reset_database_with_migrations(database_url)
    db, models, decision_layer, decision_persistence, _, json_text = _load_modules(database_url)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        payload = _base_payload(
            dimensions={
                "feedback": _dimension(
                    score=-1,
                    confidence="MEDIUM",
                    valid_signals=["feedback_valid_signal"],
                    invalid_signals=["feedback_invalid_signal"],
                    conflict_flags=["feedback_conflict"],
                )
            }
        )
        result = decision_layer.evaluate_behavioural_decision(payload)

        decision = decision_persistence.create_decision_outcome_from_result(
            session,
            decision_result=result,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            org_environment_input_id=seeded["environment_input"].id,
            environment_profile=payload["environment_profile"],
            actor_user_id=seeded["reviewer"].id,
        )
        session.commit()
        session.refresh(decision)

        assert decision.decision_state == "PROCEED_WITH_CONDITIONS"
        assert decision.decision_valid is True
        assert decision.confidence == "HIGH"
        assert not hasattr(decision, "skills_score")
        assert not hasattr(decision, "skills_outcome")
        assert not hasattr(decision, "skills_summary_id")
        assert not hasattr(decision, "pass_fail")
        assert not hasattr(decision, "model_service_2_payload")

        decision_columns = set(models.DecisionOutcome.__table__.columns.keys())
        assert "skills_score" not in decision_columns
        assert "skills_outcome" not in decision_columns
        assert "skills_summary_id" not in decision_columns
        assert "pass_fail" not in decision_columns
        assert "model_service_2_payload" not in decision_columns

        decoded = decision_persistence.decode_decision_outcome_payloads(decision)
        assert decoded["environment_profile"] == payload["environment_profile"]
        assert decoded["conditions"] == result.conditions
        assert decoded["audit_trace"] == result.model_dump(mode="json")["audit_trace"]

        assert len(decision.dimension_evaluations) == len(result.dimension_evaluations)
        assert len(decision.risk_flags) == len(result.risk_stack)
        assert len(decision.audit_trail_entries) == 1
        assert decision.audit_trail_entries[0].event_type == "decision_created"
        assert json_text.json_text_loads(
            decision.audit_trail_entries[0].event_payload_json,
            default={},
        )["decision_state"] == result.decision_state.value

        signal_rows = sorted(
            [(item.dimension, item.signal_code, item.signal_status) for item in decision.signal_evidence_items]
        )
        assert ("feedback", "feedback_invalid_signal", "INVALID") in signal_rows
        assert ("feedback", "feedback_valid_signal", "VALID") in signal_rows


def test_latest_decision_for_interview_decision_by_id_and_role_candidate_queries_work() -> None:
    database_url = _require_postgres_test_database()
    reset_database_with_migrations(database_url)
    db, models, decision_layer, decision_persistence, _, _ = _load_modules(database_url)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        first_result = decision_layer.evaluate_behavioural_decision(
            _base_payload(
                dimensions={"feedback": _dimension(score=-1, confidence="MEDIUM")},
            )
        )
        second_result = decision_layer.evaluate_behavioural_decision(_base_payload())

        first = decision_persistence.create_decision_outcome_from_result(
            session,
            decision_result=first_result,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            environment_profile={"control_vs_autonomy": "full_ownership"},
        )
        first.created_at = datetime.utcnow() - timedelta(minutes=5)
        first.updated_at = first.created_at
        session.flush()

        second = decision_persistence.create_decision_outcome_from_result(
            session,
            decision_result=second_result,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            environment_profile={"control_vs_autonomy": "full_ownership"},
        )
        session.commit()

        latest = decision_persistence.get_latest_decision_for_interview(
            session,
            interview_id=seeded["interview"].id,
        )
        fetched = decision_persistence.get_decision_by_id(session, decision_id=first.id)
        role_decisions = decision_persistence.list_decisions_for_role(session, role_id=seeded["role"].id)
        candidate_decisions = decision_persistence.list_decisions_for_candidate(
            session,
            candidate_id=seeded["candidate"].id,
        )
        audit_trail = decision_persistence.get_decision_audit_trail(session, decision_id=second.id)

        assert latest is not None
        assert latest.id == second.id
        assert fetched is not None
        assert fetched.id == first.id
        assert [item.id for item in role_decisions] == [second.id, first.id]
        assert [item.id for item in candidate_decisions] == [second.id, first.id]
        assert len(audit_trail) == 1
        assert audit_trail[0].event_type == "decision_created"


def test_human_review_action_preserves_original_system_decision_and_creates_audit_event() -> None:
    database_url = _require_postgres_test_database()
    reset_database_with_migrations(database_url)
    db, models, decision_layer, decision_persistence, _, json_text = _load_modules(database_url)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        result = decision_layer.evaluate_behavioural_decision(
            _base_payload(
                dimensions={"feedback": _dimension(score=-1, confidence="MEDIUM")},
            )
        )
        decision = decision_persistence.create_decision_outcome_from_result(
            session,
            decision_result=result,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            environment_profile={"control_vs_autonomy": "full_ownership"},
        )
        original_state = decision.decision_state

        review_action = decision_persistence.create_human_review_action(
            session,
            decision_id=decision.id,
            action_type="HUMAN_REVIEW",
            review_outcome="HOLD_FOR_FURTHER_REVIEW",
            reason="Need stronger behavioural evidence on feedback receptivity.",
            reviewed_by=seeded["reviewer"].id,
            notes={"note": "Preserve the system outcome."},
            display_delta={"badge": "Human review requested"},
        )
        session.commit()
        session.refresh(decision)

        assert review_action.decision_id == decision.id
        assert decision.decision_state == original_state

        review_event = (
            session.execute(
                select(models.DecisionAuditTrail)
                .where(models.DecisionAuditTrail.decision_id == decision.id)
                .order_by(models.DecisionAuditTrail.created_at.desc())
            )
            .scalars()
            .first()
        )
        assert review_event is not None
        assert review_event.event_type == "human_review_action_created"
        payload = json_text.json_text_loads(review_event.event_payload_json, default={})
        assert review_event.actor_type == "user"
        assert payload["original_decision_state"] == original_state
        assert payload["human_review_action_id"] == review_action.id


def test_human_review_requires_reason() -> None:
    database_url = _require_postgres_test_database()
    reset_database_with_migrations(database_url)
    db, models, decision_layer, decision_persistence, _, _ = _load_modules(database_url)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        result = decision_layer.evaluate_behavioural_decision(_base_payload())
        decision = decision_persistence.create_decision_outcome_from_result(
            session,
            decision_result=result,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            environment_profile={"control_vs_autonomy": "full_ownership"},
        )

        with pytest.raises(ValueError, match="reason is required"):
            decision_persistence.create_human_review_action(
                session,
                decision_id=decision.id,
                action_type="HUMAN_REVIEW",
                review_outcome="HOLD_FOR_FURTHER_REVIEW",
                reason="   ",
                reviewed_by=seeded["reviewer"].id,
            )


def test_skills_assessment_summary_persists_separately_and_is_excluded_from_tds_decisioning() -> None:
    database_url = _require_postgres_test_database()
    reset_database_with_migrations(database_url)
    db, models, _, decision_persistence, skills_service, json_text = _load_modules(database_url)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)

        before_count = session.execute(select(models.DecisionOutcome)).scalars().all()
        assert before_count == []

        summary = skills_service.create_skills_assessment_summary(
            session,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            observed_competencies=["discovery", "stakeholder_management"],
            competency_coverage={"required": 4, "observed": 2},
            skill_gaps=["forecasting", "meddic"],
            evidence_strength="MEDIUM",
            confidence="MEDIUM",
            source_references=[{"service": "model-service-2"}],
            human_readable_summary="Skills are informative but excluded from MVP1 TDS decisioning.",
            requires_human_review=True,
            model_version="skills-ms2-v1",
        )
        session.commit()

        latest = skills_service.get_latest_skills_assessment_summary_for_interview(
            session,
            interview_id=seeded["interview"].id,
        )
        decisions = session.execute(select(models.DecisionOutcome)).scalars().all()

        assert latest is not None
        assert latest.id == summary.id
        assert summary.excluded_from_tds_decisioning is True
        assert json_text.json_text_loads(summary.skill_gaps_json, default=[]) == ["forecasting", "meddic"]
        assert decisions == []
        assert not hasattr(models.DecisionOutcome, "skills_summary_id")
        assert decision_persistence.get_latest_decision_for_interview(
            session,
            interview_id=seeded["interview"].id,
        ) is None


def test_fake_skills_data_is_rejected_by_decision_persistence_helper() -> None:
    _, _, decision_layer, decision_persistence, _, _ = _load_modules()
    result = decision_layer.evaluate_behavioural_decision(_base_payload())
    dirty_result = result.model_dump(mode="python")
    dirty_result["skills_score"] = 100
    dirty_result["skills_assessment_summary"] = {"outcome": "FAIL"}

    with pytest.raises(ValueError, match="behavioural evidence only"):
        decision_persistence._coerce_behavioural_decision_result(dirty_result)
