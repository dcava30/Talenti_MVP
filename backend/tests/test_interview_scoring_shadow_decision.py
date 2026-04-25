import asyncio
import json
import logging
import os
import sys
import tempfile
from datetime import datetime

import pytest
from conftest import (
    backend_root,
    clear_app_modules,
    prepare_test_environment,
)
from sqlalchemy import select


def _load_modules(database_url: str | None = None, *, shadow_enabled: bool):
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    if database_url is not None:
        os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_DECISION_SHADOW_WRITE_ENABLED"] = "true" if shadow_enabled else "false"
    clear_app_modules()

    import app.db as db

    import app.models as models
    import app.services.decision_persistence as decision_persistence
    import app.services.interview_scoring as interview_scoring

    _create_shadow_test_schema(db, models)
    return db, models, interview_scoring, decision_persistence


def _sqlite_test_database_url() -> str:
    fd, path = tempfile.mkstemp(prefix="tds-shadow-", suffix=".sqlite3")
    os.close(fd)
    return f"sqlite:///{path}"


def _create_shadow_test_schema(db, models) -> None:
    db.Base.metadata.create_all(
        bind=db.engine,
        tables=[
            models.User.__table__,
            models.Organisation.__table__,
            models.CandidateProfile.__table__,
            models.JobRole.__table__,
            models.Application.__table__,
            models.Interview.__table__,
            models.OrgEnvironmentInput.__table__,
            models.TranscriptSegment.__table__,
            models.InterviewScore.__table__,
            models.ScoreDimension.__table__,
            models.DecisionOutcome.__table__,
            models.DecisionDimensionEvaluation.__table__,
            models.DecisionSignalEvidence.__table__,
            models.DecisionRiskFlag.__table__,
            models.DecisionAuditTrail.__table__,
        ],
    )


def _seed_interview_context(db_session, models):
    candidate_user = models.User(
        email="shadow-candidate@example.com",
        password_hash="hashed-password",
        full_name="Shadow Candidate",
    )
    organisation = models.Organisation(
        name="Talenti Shadow Org",
        values_framework=json.dumps(
            {
                "operating_environment": {
                    "control_vs_autonomy": "full_ownership",
                    "outcome_vs_process": "results_first",
                    "pace_and_change": "fast",
                    "risk_posture": "take_intelligent_risks",
                    "collaboration_style": "debate_then_align",
                    "decision_reality": "evidence_led",
                    "environment_confidence": "high",
                    "high_performance_archetype": "generalist",
                },
                "taxonomy": {
                    "taxonomy_id": "talenti-taxonomy",
                    "version": "2026-04",
                    "signals": [],
                },
            }
        ),
    )
    db_session.add_all([candidate_user, organisation])
    db_session.flush()

    candidate = models.CandidateProfile(
        user_id=candidate_user.id,
        first_name="Shadow",
        last_name="Candidate",
        email="shadow-candidate@example.com",
    )
    role = models.JobRole(
        organisation_id=organisation.id,
        title="Account Executive",
        description="Own revenue outcomes.",
        status="active",
        scoring_rubric=json.dumps(
            {
                "ownership": {"weight": 1.0, "tier": "Critical"},
                "execution": {"weight": 1.0, "tier": "Critical"},
                "challenge": {"weight": 1.0, "tier": "Important"},
                "ambiguity": {"weight": 1.0, "tier": "Important"},
                "feedback": {"weight": 1.0, "tier": "Important"},
            }
        ),
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
        derived_environment=json.dumps(
            {
                "control_vs_autonomy": "full_ownership",
                "outcome_vs_process": "results_first",
                "environment_confidence": "high",
            }
        ),
    )
    db_session.add_all([interview, environment_input])
    db_session.flush()

    db_session.add_all(
        [
            models.TranscriptSegment(
                interview_id=interview.id,
                sequence=1,
                speaker="interviewer",
                content="Tell me about a time you drove a hard outcome.",
            ),
            models.TranscriptSegment(
                interview_id=interview.id,
                sequence=2,
                speaker="candidate",
                content="I owned the plan, challenged assumptions, and delivered.",
            ),
        ]
    )
    db_session.flush()

    return {
        "organisation": organisation,
        "candidate": candidate,
        "role": role,
        "application": application,
        "interview": interview,
        "environment_input": environment_input,
    }


def _fake_predictions():
    async def fake_predictions(*args, **kwargs):
        return (
            {
                "scores": {
                    "ownership": {
                        "score": 85,
                        "rationale": "Strong ownership evidence.",
                        "confidence": 0.92,
                        "matched_keywords": ["owned_outcome", "self_direction"],
                    },
                    "execution": {
                        "score": 82,
                        "rationale": "Execution evidence present.",
                        "confidence": 0.9,
                        "matched_keywords": ["delivery", "follow_through"],
                    },
                    "challenge": {
                        "score": 74,
                        "rationale": "Constructive challenge.",
                        "confidence": 0.81,
                        "matched_keywords": ["pushed_back"],
                    },
                    "ambiguity": {
                        "score": 70,
                        "rationale": "Handled ambiguity.",
                        "confidence": 0.78,
                        "matched_keywords": ["navigated_ambiguity"],
                    },
                    "feedback": {
                        "score": 68,
                        "rationale": "Feedback responsiveness.",
                        "confidence": 0.76,
                        "matched_keywords": ["feedback_loop"],
                    },
                },
                "summary": "Strong behavioural fit.",
                "overall_alignment": "strong_fit",
                "overall_risk_level": "low",
                "model_version": "service1-shadow-test",
            },
            {
                "overall_score": 78,
                "outcome": "PASS",
                "scores": {
                    "crm": {"score": 0.8, "confidence": 0.7, "rationale": "Good CRM evidence."},
                    "forecasting": {"score": 0.76, "confidence": 0.68, "rationale": "Solid forecasting."},
                },
                "must_haves_passed": ["crm"],
                "must_haves_failed": [],
                "gaps": ["enterprise_procurement"],
                "summary": "Useful skills signal, but separate from TDS decisions.",
            },
        )

    return fake_predictions


def test_shadow_write_disabled_skips_decision_evaluation_and_persistence(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _ = _load_modules(database_url, shadow_enabled=False)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        def _unexpected_decision_call(*args, **kwargs):
            raise AssertionError("Shadow decision evaluation should not be attempted when disabled.")

        monkeypatch.setattr(interview_scoring, "evaluate_behavioural_decision", _unexpected_decision_call)
        monkeypatch.setattr(
            interview_scoring,
            "create_decision_outcome_from_result",
            _unexpected_decision_call,
        )

        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")
        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        decisions = session.execute(select(models.DecisionOutcome)).scalars().all()
        legacy_scores = session.execute(select(models.InterviewScore)).scalars().all()

        assert decisions == []
        assert len(legacy_scores) == 1
        assert set(result.keys()) == {
            "interview_id",
            "culture_fit_score",
            "skills_score",
            "skills_outcome",
            "recommendation",
            "overall_alignment",
            "overall_risk_level",
            "dimension_count",
        }
        assert "decision_state" not in result
        assert result["skills_score"] == 78
        assert "TDS shadow decision skipped because feature flag disabled" in caplog.text


def test_shadow_write_enabled_persists_behavioural_decision_and_shadow_audit_event(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, decision_persistence = _load_modules(
        database_url,
        shadow_enabled=True,
    )

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")
        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        decision = decision_persistence.get_latest_decision_for_interview(
            session,
            interview_id=seeded["interview"].id,
        )
        legacy_score = session.execute(select(models.InterviewScore)).scalar_one()

        assert decision is not None
        assert decision.org_environment_input_id == seeded["environment_input"].id
        assert not hasattr(decision, "skills_score")
        assert not hasattr(decision, "skills_outcome")
        assert legacy_score.skills_score == 78
        assert legacy_score.skills_outcome == "PASS"
        assert result["interview_id"] == seeded["interview"].id
        assert "decision_state" not in result

        decoded = decision_persistence.decode_decision_outcome_payloads(decision)
        assert "skills_score" not in decoded
        assert "skills_outcome" not in decoded
        assert "skills_assessment_summary" not in decoded
        assert decoded["environment_profile"]["control_vs_autonomy"] == "full_ownership"

        audit_entries = decision_persistence.get_decision_audit_trail(session, decision_id=decision.id)
        assert [entry.event_type for entry in audit_entries] == [
            "decision_created",
            "shadow_decision_evaluated",
        ]
        assert decision_persistence.get_latest_decision_for_interview(
            session,
            interview_id=seeded["interview"].id,
        ).id == decision.id
        assert "TDS shadow decision evaluation started" in caplog.text
        assert "TDS shadow decision persisted" in caplog.text


def test_shadow_write_enabled_skips_duplicate_same_rule_and_policy_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _ = _load_modules(database_url, shadow_enabled=True)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        first = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        second = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        decisions = session.execute(select(models.DecisionOutcome)).scalars().all()
        legacy_score = session.execute(select(models.InterviewScore)).scalar_one()

        assert len(decisions) == 1
        assert first.keys() == second.keys()
        assert legacy_score.skills_outcome == "PASS"


def test_shadow_decision_layer_failure_is_non_fatal_and_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _ = _load_modules(database_url, shadow_enabled=True)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        def _boom(*args, **kwargs):
            raise RuntimeError("decision layer exploded")

        monkeypatch.setattr(interview_scoring, "evaluate_behavioural_decision", _boom)
        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")

        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        decisions = session.execute(select(models.DecisionOutcome)).scalars().all()
        legacy_score = session.execute(select(models.InterviewScore)).scalar_one()

        assert decisions == []
        assert legacy_score.interview_id == seeded["interview"].id
        assert result["skills_outcome"] == "PASS"
        assert "TDS shadow decision failed non-fatally" in caplog.text


def test_shadow_decision_persistence_failure_is_non_fatal_and_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _ = _load_modules(database_url, shadow_enabled=True)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        def _boom(*args, **kwargs):
            raise RuntimeError("decision persistence exploded")

        monkeypatch.setattr(interview_scoring, "create_decision_outcome_from_result", _boom)
        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")

        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        decisions = session.execute(select(models.DecisionOutcome)).scalars().all()
        legacy_score = session.execute(select(models.InterviewScore)).scalar_one()

        assert decisions == []
        assert legacy_score.interview_id == seeded["interview"].id
        assert result["culture_fit_score"] > 0
        assert "TDS shadow decision failed non-fatally" in caplog.text
