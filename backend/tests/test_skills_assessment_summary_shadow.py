import asyncio
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest
from conftest import backend_root, clear_app_modules, prepare_test_environment
from sqlalchemy import select


def _load_modules(
    database_url: str | None = None,
    *,
    decision_shadow_enabled: bool = False,
    skills_summary_shadow_enabled: bool = False,
):
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    if database_url is not None:
        os.environ["DATABASE_URL"] = database_url
    os.environ["TDS_DECISION_SHADOW_WRITE_ENABLED"] = "true" if decision_shadow_enabled else "false"
    os.environ["TDS_SKILLS_SUMMARY_SHADOW_WRITE_ENABLED"] = (
        "true" if skills_summary_shadow_enabled else "false"
    )
    clear_app_modules()

    import app.db as db
    import app.models as models
    import app.services.decision_persistence as decision_persistence
    import app.services.interview_scoring as interview_scoring
    import app.services.skills_assessment_mapper as skills_assessment_mapper
    import app.services.skills_assessment_summary as skills_assessment_summary

    _create_shadow_test_schema(db, models)
    return (
        db,
        models,
        interview_scoring,
        decision_persistence,
        skills_assessment_mapper,
        skills_assessment_summary,
    )


def _sqlite_test_database_url() -> str:
    fd, path = tempfile.mkstemp(prefix="tds-skills-summary-shadow-", suffix=".sqlite3")
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
            models.SkillsAssessmentSummary.__table__,
        ],
    )


def _seed_interview_context(db_session, models):
    candidate_user = models.User(
        email="skills-shadow-candidate@example.com",
        password_hash="hashed-password",
        full_name="Skills Shadow Candidate",
    )
    organisation = models.Organisation(
        name="Talenti Skills Shadow Org",
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
        first_name="Skills",
        last_name="Candidate",
        email="skills-shadow-candidate@example.com",
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


def _fake_predictions(
    *,
    model_version: str = "service2-shadow-v1",
    outcome: str = "PASS",
    summary: str = "Role-specific skills evidence captured separately from TDS decisions.",
):
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
                "outcome": outcome,
                "model_version": model_version,
                "scores": {
                    "crm": {
                        "score": 0.8,
                        "confidence": 0.7,
                        "rationale": "Good CRM evidence.",
                        "matched_keywords": ["salesforce", "pipeline"],
                    },
                    "forecasting": {
                        "score": 0.76,
                        "confidence": 0.68,
                        "rationale": "Solid forecasting.",
                        "years_detected": 2.5,
                        "matched_keywords": ["forecast", "commit"],
                    },
                },
                "must_haves_passed": ["crm"],
                "must_haves_failed": ["meddic"],
                "gaps": ["enterprise_procurement"],
                "summary": summary,
            },
        )

    return fake_predictions


def _base_model2_result(
    *,
    overall_score: int = 78,
    outcome: str = "REVIEW",
    model_version: str = "skills-ms2-v1",
) -> dict[str, object]:
    return {
        "overall_score": overall_score,
        "outcome": outcome,
        "model_version": model_version,
        "scores": {
            "crm": {
                "score": 0.8,
                "confidence": 0.72,
                "rationale": "Strong CRM evidence.",
                "matched_keywords": ["salesforce"],
            },
            "forecasting": {
                "score": 0.43,
                "confidence": 0.54,
                "rationale": "Some forecasting evidence.",
                "years_detected": 1.5,
                "matched_keywords": ["forecast"],
            },
        },
        "must_haves_passed": ["crm"],
        "must_haves_failed": ["meddic"],
        "gaps": ["enterprise_procurement"],
        "summary": "Role-specific evidence only.",
    }


def _result_shape(result: dict[str, object]) -> set[str]:
    return set(result.keys())


def test_mapper_translates_legacy_model_service_2_output_into_non_decisional_summary_payload() -> None:
    _, _, _, _, mapper, _ = _load_modules()

    payload = mapper.map_model_service_2_output_to_skills_assessment_summary(
        _base_model2_result(overall_score=78, outcome="FAIL")
    )

    assert payload["observed_competencies"]["crm"]["evidence_score"] == 80
    assert payload["observed_competencies"]["forecasting"]["years_detected"] == 1.5
    assert payload["competency_coverage"]["required_competencies_observed"] == ["crm"]
    assert payload["competency_coverage"]["required_competencies_missing"] == ["meddic"]
    assert payload["skill_gaps"] == ["enterprise_procurement"]
    assert payload["human_readable_summary"] == "Role-specific evidence only."
    assert payload["model_version"] == "skills-ms2-v1"
    assert payload["evidence_strength"] == "High"
    assert payload["confidence"] == "Medium"
    assert payload["requires_human_review"] is True
    assert payload["excluded_from_tds_decisioning"] is True
    assert "outcome" not in payload
    assert "overall_score" not in payload
    assert "FAIL" not in json.dumps(payload)


def test_mapper_always_marks_summary_excluded_from_tds_decisioning_and_does_not_require_outcome() -> None:
    _, _, _, _, mapper, _ = _load_modules()
    payload = mapper.map_model_service_2_output_to_skills_assessment_summary(
        _base_model2_result(outcome="PASS")
    )

    assert payload["excluded_from_tds_decisioning"] is True
    assert payload["requires_human_review"] is False
    assert payload["source_references"][0]["producer"] == "model-service-2"


def test_latest_summary_helpers_support_latest_lookup_and_model_version_lookup() -> None:
    database_url = _sqlite_test_database_url()
    db, models, _, _, _, skills_service = _load_modules(database_url)

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        first = skills_service.create_skills_assessment_summary(
            session,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            observed_competencies={"crm": {"evidence_score": 55}},
            competency_coverage={"required_competencies_observed": ["crm"]},
            skill_gaps=["forecasting"],
            evidence_strength="Medium",
            human_readable_summary="Earlier summary.",
            model_version="skills-ms2-v1",
        )
        first.created_at = datetime.utcnow() - timedelta(minutes=5)
        first.updated_at = first.created_at
        session.flush()

        second = skills_service.create_skills_assessment_summary(
            session,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            observed_competencies={"crm": {"evidence_score": 80}},
            competency_coverage={"required_competencies_observed": ["crm", "forecasting"]},
            skill_gaps=[],
            evidence_strength="High",
            human_readable_summary="Later summary.",
            model_version="skills-ms2-v2",
        )
        session.commit()

        latest = skills_service.get_latest_skills_assessment_summary_for_interview(
            session,
            interview_id=seeded["interview"].id,
        )
        by_version = skills_service.get_latest_skills_assessment_summary_for_interview_model_version(
            session,
            interview_id=seeded["interview"].id,
            model_version="skills-ms2-v1",
        )

        assert latest is not None
        assert latest.id == second.id
        assert by_version is not None
        assert by_version.id == first.id


def test_shadow_skills_summary_write_disabled_skips_persistence_attempt(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _, _, _ = _load_modules(
        database_url,
        skills_summary_shadow_enabled=False,
    )

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        def _unexpected_write(*args, **kwargs):
            raise AssertionError("Skills summary persistence should not be attempted when disabled.")

        monkeypatch.setattr(interview_scoring, "create_skills_assessment_summary", _unexpected_write)
        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")

        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        summaries = session.execute(select(models.SkillsAssessmentSummary)).scalars().all()

        assert summaries == []
        assert _result_shape(result) == {
            "interview_id",
            "culture_fit_score",
            "skills_score",
            "skills_outcome",
            "recommendation",
            "overall_alignment",
            "overall_risk_level",
            "dimension_count",
        }
        assert "TDS skills summary shadow write skipped because feature flag disabled" in caplog.text


def test_shadow_skills_summary_write_enabled_persists_non_decisional_summary_without_decision_outcome(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _, _, _ = _load_modules(
        database_url,
        decision_shadow_enabled=False,
        skills_summary_shadow_enabled=True,
    )

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(outcome="REVIEW"),
        )

        def _unexpected_decision_call(*args, **kwargs):
            raise AssertionError("Skills summary generation must not call the Decision Layer.")

        monkeypatch.setattr(interview_scoring, "evaluate_behavioural_decision", _unexpected_decision_call)
        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")

        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        summaries = session.execute(select(models.SkillsAssessmentSummary)).scalars().all()
        decisions = session.execute(select(models.DecisionOutcome)).scalars().all()

        assert len(summaries) == 1
        assert decisions == []
        assert summaries[0].excluded_from_tds_decisioning is True
        assert summaries[0].requires_human_review is True
        assert summaries[0].model_version == "service2-shadow-v1"
        assert json.loads(summaries[0].competency_coverage_json) == {
            "required_competencies_observed": ["crm"],
            "required_competencies_missing": ["meddic"],
        }
        assert json.loads(summaries[0].skill_gaps_json) == ["enterprise_procurement"]
        assert _result_shape(result) == {
            "interview_id",
            "culture_fit_score",
            "skills_score",
            "skills_outcome",
            "recommendation",
            "overall_alignment",
            "overall_risk_level",
            "dimension_count",
        }
        assert result["skills_score"] == 78
        assert result["skills_outcome"] == "REVIEW"
        assert "TDS skills summary shadow mapping started" in caplog.text
        assert "TDS skills summary shadow persisted" in caplog.text


def test_shadow_skills_summary_write_skips_duplicate_for_same_interview_and_model_version(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _, _, skills_service = _load_modules(
        database_url,
        skills_summary_shadow_enabled=True,
    )

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(model_version="service2-shadow-v1"),
        )
        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")

        asyncio.run(interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id))
        session.commit()
        asyncio.run(interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id))
        session.commit()

        summaries = session.execute(select(models.SkillsAssessmentSummary)).scalars().all()
        latest = skills_service.get_latest_skills_assessment_summary_for_interview(
            session,
            interview_id=seeded["interview"].id,
        )

        assert len(summaries) == 1
        assert latest is not None
        assert latest.model_version == "service2-shadow-v1"
        assert "TDS skills summary shadow duplicate skipped" in caplog.text


def test_shadow_skills_summary_write_mapper_failure_is_non_fatal(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _, _, _ = _load_modules(
        database_url,
        skills_summary_shadow_enabled=True,
    )

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        def _boom(*args, **kwargs):
            raise ValueError("mapper exploded")

        monkeypatch.setattr(
            interview_scoring,
            "map_model_service_2_output_to_skills_assessment_summary",
            _boom,
        )
        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")

        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        summaries = session.execute(select(models.SkillsAssessmentSummary)).scalars().all()
        legacy_score = session.execute(select(models.InterviewScore)).scalar_one()

        assert summaries == []
        assert legacy_score.interview_id == seeded["interview"].id
        assert _result_shape(result) == {
            "interview_id",
            "culture_fit_score",
            "skills_score",
            "skills_outcome",
            "recommendation",
            "overall_alignment",
            "overall_risk_level",
            "dimension_count",
        }
        assert "TDS skills summary shadow write failed non-fatally" in caplog.text


def test_shadow_skills_summary_write_persistence_failure_is_non_fatal(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, _, _, _ = _load_modules(
        database_url,
        skills_summary_shadow_enabled=True,
    )

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(),
        )

        def _boom(*args, **kwargs):
            raise RuntimeError("skills summary persistence exploded")

        monkeypatch.setattr(interview_scoring, "create_skills_assessment_summary", _boom)
        caplog.set_level(logging.INFO, logger="app.services.interview_scoring")

        result = asyncio.run(
            interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id)
        )
        session.commit()

        summaries = session.execute(select(models.SkillsAssessmentSummary)).scalars().all()
        legacy_score = session.execute(select(models.InterviewScore)).scalar_one()

        assert summaries == []
        assert legacy_score.interview_id == seeded["interview"].id
        assert result["skills_outcome"] == "PASS"
        assert "TDS skills summary shadow write failed non-fatally" in caplog.text


def test_shadow_skills_summary_write_does_not_modify_existing_decision_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _sqlite_test_database_url()
    db, models, interview_scoring, decision_persistence, _, _ = _load_modules(
        database_url,
        decision_shadow_enabled=False,
        skills_summary_shadow_enabled=True,
    )

    with db.SessionLocal() as session:
        seeded = _seed_interview_context(session, models)
        decision_input = interview_scoring.build_shadow_behavioural_decision_input(
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            operating_environment={
                "control_vs_autonomy": "full_ownership",
                "outcome_vs_process": "results_first",
                "environment_confidence": "high",
                "high_performance_archetype": "generalist",
            },
            culture_fit=interview_scoring.CultureFitResult(
                overall_score=82,
                overall_alignment="strong_fit",
                overall_risk_level="low",
                recommendation="proceed",
                dimensions=[
                    interview_scoring.BehaviouralDimension(
                        name="ownership",
                        score=85,
                        confidence=0.91,
                        confidence_band="High",
                        rationale="Strong ownership evidence.",
                        matched_signals=["owned_outcome"],
                        source="service1",
                    ),
                    interview_scoring.BehaviouralDimension(
                        name="execution",
                        score=82,
                        confidence=0.89,
                        confidence_band="High",
                        rationale="Strong execution evidence.",
                        matched_signals=["follow_through"],
                        source="service1",
                    ),
                ],
                summary="Behavioural path only.",
            ),
            dimension_tiers={"ownership": "Critical", "execution": "Critical"},
        )
        decision_result = interview_scoring.evaluate_behavioural_decision(decision_input)
        existing_decision = decision_persistence.create_decision_outcome_from_result(
            session,
            decision_result=decision_result,
            interview_id=seeded["interview"].id,
            candidate_id=seeded["candidate"].id,
            role_id=seeded["role"].id,
            organisation_id=seeded["organisation"].id,
            org_environment_input_id=seeded["environment_input"].id,
            environment_profile=decision_input.environment_profile,
        )
        session.commit()
        existing_id = existing_decision.id
        existing_state = existing_decision.decision_state
        existing_updated_at = existing_decision.updated_at

        monkeypatch.setattr(
            interview_scoring.ml_client,
            "get_combined_predictions",
            _fake_predictions(model_version="service2-shadow-v2"),
        )

        asyncio.run(interview_scoring.run_auto_scoring_for_interview(session, seeded["interview"].id))
        session.commit()

        persisted_decision = session.get(models.DecisionOutcome, existing_id)
        summaries = session.execute(select(models.SkillsAssessmentSummary)).scalars().all()

        assert persisted_decision is not None
        assert persisted_decision.decision_state == existing_state
        assert persisted_decision.updated_at == existing_updated_at
        assert len(summaries) == 1
        assert not hasattr(models.DecisionOutcome, "skills_summary_id")

