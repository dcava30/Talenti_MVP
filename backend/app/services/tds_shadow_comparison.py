from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, DecisionOutcome, Interview, InterviewScore, JobRole, SkillsAssessmentSummary
from app.schemas.tds_shadow_comparison import (
    ComparisonResultResponse,
    LegacyScoreSummaryResponse,
    OrganisationShadowComparisonSummaryResponse,
    RoleShadowComparisonSummaryResponse,
    SkillsSummaryStatusResponse,
    TdsDecisionSummaryResponse,
    TdsShadowComparisonResponse,
)
from app.services.decision_persistence import decode_decision_outcome_payloads
from app.services.skills_assessment_summary import get_latest_skills_assessment_summary_for_interview

LEGACY_RECOMMENDATION_ORDER = {
    "proceed": 0,
    "caution": 1,
    "reject": 2,
}
TDS_DECISION_ORDER = {
    "PROCEED": 0,
    "PROCEED_WITH_CONDITIONS": 1,
    "DO_NOT_PROCEED": 2,
}
LEGACY_SKILLS_OUTCOME_STATUS_MAP = {
    "PASS": "observed",
    "REVIEW": "needs_review",
    "FAIL": "missing",
}


def get_shadow_comparison_for_interview(
    db: Session,
    *,
    interview_id: str,
) -> TdsShadowComparisonResponse | None:
    context = _get_interview_context(db, interview_id=interview_id)
    if context is None:
        return None
    interview, application, role = context
    return _build_interview_shadow_comparison(
        db,
        interview=interview,
        application=application,
        role=role,
    )


def list_shadow_comparisons_for_role(
    db: Session,
    *,
    role_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[TdsShadowComparisonResponse]:
    contexts = list(
        db.execute(
            select(Interview, Application, JobRole)
            .join(Application, Interview.application_id == Application.id)
            .join(JobRole, Application.job_role_id == JobRole.id)
            .where(JobRole.id == role_id)
            .order_by(Interview.created_at.desc(), Interview.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return [
        _build_interview_shadow_comparison(db, interview=interview, application=application, role=role)
        for interview, application, role in contexts
    ]


def summarize_shadow_comparisons_for_role(
    db: Session,
    *,
    role_id: str,
    organisation_id: str,
) -> RoleShadowComparisonSummaryResponse:
    comparisons = list_shadow_comparisons_for_role(
        db,
        role_id=role_id,
        limit=10_000,
        offset=0,
    )
    counts = _build_summary_counts(comparisons)
    return RoleShadowComparisonSummaryResponse(role_id=role_id, organisation_id=organisation_id, **counts)


def summarize_shadow_comparisons_for_organisation(
    db: Session,
    *,
    organisation_id: str,
) -> OrganisationShadowComparisonSummaryResponse:
    contexts = list(
        db.execute(
            select(Interview, Application, JobRole)
            .join(Application, Interview.application_id == Application.id)
            .join(JobRole, Application.job_role_id == JobRole.id)
            .where(JobRole.organisation_id == organisation_id)
            .order_by(Interview.created_at.desc(), Interview.id.desc())
        ).all()
    )
    comparisons = [
        _build_interview_shadow_comparison(db, interview=interview, application=application, role=role)
        for interview, application, role in contexts
    ]
    counts = _build_summary_counts(comparisons)
    return OrganisationShadowComparisonSummaryResponse(organisation_id=organisation_id, **counts)


def classify_shadow_comparison(
    *,
    legacy_score_present: bool,
    legacy_recommendation: str | None,
    tds_decision_present: bool,
    tds_decision_state: str | None,
) -> ComparisonResultResponse:
    notes: list[str] = []

    if not legacy_score_present and not tds_decision_present:
        return ComparisonResultResponse(
            comparison_status="insufficient_data",
            comparison_notes=["Legacy scoring output and shadow TDS decision are both missing."],
        )

    if legacy_score_present and not tds_decision_present:
        return ComparisonResultResponse(
            comparison_status="legacy_only",
            comparison_notes=["Legacy scoring output exists, but no shadow TDS decision is available yet."],
        )

    if not legacy_score_present and tds_decision_present:
        return ComparisonResultResponse(
            comparison_status="tds_only",
            comparison_notes=["Shadow TDS decision exists, but no legacy scoring output is available."],
        )

    if tds_decision_state == "INSUFFICIENT_EVIDENCE":
        notes.append(
            "Shadow TDS returned INSUFFICIENT_EVIDENCE and remains a separate validation outcome."
        )
        if legacy_recommendation:
            notes.append(
                f"Legacy recommendation was {legacy_recommendation}, but behavioural comparison stops at insufficient evidence."
            )
        return ComparisonResultResponse(
            comparison_status="insufficient_evidence",
            comparison_notes=notes,
        )

    legacy_rank = LEGACY_RECOMMENDATION_ORDER.get(normalize_legacy_recommendation(legacy_recommendation))
    tds_rank = TDS_DECISION_ORDER.get((tds_decision_state or "").strip().upper())

    if legacy_rank is None or tds_rank is None:
        if legacy_recommendation is None:
            notes.append("Legacy scoring exists but no comparable legacy recommendation is available.")
        if tds_decision_state is None:
            notes.append("Shadow TDS decision exists but no comparable decision state is available.")
        if legacy_rank is None and legacy_recommendation is not None:
            notes.append(f"Legacy recommendation {legacy_recommendation!r} is not mapped for comparison.")
        if tds_rank is None and tds_decision_state is not None:
            notes.append(f"TDS decision state {tds_decision_state!r} is not mapped for comparison.")
        return ComparisonResultResponse(comparison_status="unknown", comparison_notes=notes)

    if legacy_rank == tds_rank:
        return ComparisonResultResponse(
            comparison_status="aligned",
            comparison_notes=[
                f"Legacy recommendation {legacy_recommendation} and shadow TDS decision {tds_decision_state} are aligned."
            ],
        )

    if tds_rank > legacy_rank:
        return ComparisonResultResponse(
            comparison_status="shifted_more_cautious",
            comparison_notes=[
                f"Shadow TDS decision {tds_decision_state} is more cautious than legacy recommendation {legacy_recommendation}."
            ],
        )

    return ComparisonResultResponse(
        comparison_status="shifted_less_cautious",
        comparison_notes=[
            f"Shadow TDS decision {tds_decision_state} is less cautious than legacy recommendation {legacy_recommendation}."
        ],
    )


def normalize_legacy_recommendation(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    return normalized


def normalize_legacy_skills_outcome_status(value: str | None) -> str:
    if value is None:
        return "unavailable"
    normalized = str(value).strip().upper()
    if not normalized:
        return "unavailable"
    return LEGACY_SKILLS_OUTCOME_STATUS_MAP.get(normalized, "unavailable")


def get_latest_interview_score(
    db: Session,
    *,
    interview_id: str,
) -> InterviewScore | None:
    return db.execute(
        select(InterviewScore)
        .where(InterviewScore.interview_id == interview_id)
        .order_by(InterviewScore.created_at.desc(), InterviewScore.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_latest_shadow_decision(
    db: Session,
    *,
    interview_id: str,
) -> DecisionOutcome | None:
    return db.execute(
        select(DecisionOutcome)
        .where(DecisionOutcome.interview_id == interview_id)
        .order_by(DecisionOutcome.created_at.desc(), DecisionOutcome.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _get_interview_context(
    db: Session,
    *,
    interview_id: str,
) -> tuple[Interview, Application, JobRole] | None:
    return db.execute(
        select(Interview, Application, JobRole)
        .join(Application, Interview.application_id == Application.id)
        .join(JobRole, Application.job_role_id == JobRole.id)
        .where(Interview.id == interview_id)
        .limit(1)
    ).first()


def _build_interview_shadow_comparison(
    db: Session,
    *,
    interview: Interview,
    application: Application,
    role: JobRole,
) -> TdsShadowComparisonResponse:
    legacy_score = get_latest_interview_score(db, interview_id=interview.id)
    decision = get_latest_shadow_decision(db, interview_id=interview.id)
    skills_summary = get_latest_skills_assessment_summary_for_interview(db, interview_id=interview.id)

    legacy_summary = _build_legacy_score_summary(legacy_score)
    tds_summary = _build_tds_decision_summary(decision)
    skills_status = _build_skills_summary_status(skills_summary)
    comparison_result = classify_shadow_comparison(
        legacy_score_present=legacy_summary.present,
        legacy_recommendation=legacy_summary.recommendation,
        tds_decision_present=tds_summary.present,
        tds_decision_state=tds_summary.decision_state,
    )

    return TdsShadowComparisonResponse(
        interview_id=interview.id,
        candidate_id=application.candidate_profile_id,
        role_id=role.id,
        organisation_id=role.organisation_id,
        interview_created_at=interview.created_at,
        legacy_score_summary=legacy_summary,
        tds_decision_summary=tds_summary,
        skills_summary_status=skills_status,
        comparison_result=comparison_result,
    )


def _build_legacy_score_summary(score: InterviewScore | None) -> LegacyScoreSummaryResponse:
    if score is None:
        return LegacyScoreSummaryResponse(present=False)

    return LegacyScoreSummaryResponse(
        legacy_score_id=score.id,
        present=True,
        culture_fit_score=score.culture_fit_score,
        overall_score=getattr(score, "overall_score", None),
        recommendation=normalize_legacy_recommendation(score.recommendation),
        overall_alignment=score.overall_alignment,
        overall_risk_level=score.overall_risk_level,
        skills_score=score.skills_score,
        legacy_skills_outcome_status=normalize_legacy_skills_outcome_status(score.skills_outcome),
        created_at=score.created_at,
    )


def _build_tds_decision_summary(decision: DecisionOutcome | None) -> TdsDecisionSummaryResponse:
    if decision is None:
        return TdsDecisionSummaryResponse(present=False)

    decoded = decode_decision_outcome_payloads(decision)
    ordered_risk_codes = _ordered_distinct(
        [risk.risk_code for risk in sorted(decision.risk_flags, key=lambda row: (row.created_at, row.id))]
    )
    evidence_gaps = [str(item) for item in decoded["evidence_gaps"]]
    return TdsDecisionSummaryResponse(
        decision_id=decision.id,
        present=True,
        decision_state=decision.decision_state,
        decision_valid=decision.decision_valid,
        confidence=decision.confidence,
        confidence_gate_passed=decision.confidence_gate_passed,
        integrity_status=decision.integrity_status,
        risk_flags=ordered_risk_codes,
        evidence_gaps=evidence_gaps,
        rule_version=decision.rule_version,
        policy_version=decision.policy_version,
        created_at=decision.created_at,
    )


def _build_skills_summary_status(summary: SkillsAssessmentSummary | None) -> SkillsSummaryStatusResponse:
    if summary is None:
        return SkillsSummaryStatusResponse(status="missing")

    return SkillsSummaryStatusResponse(
        skills_summary_id=summary.id,
        status="present",
        requires_human_review=summary.requires_human_review,
        evidence_strength=summary.evidence_strength,
        excluded_from_tds_decisioning=True,
        created_at=summary.created_at,
    )


def _build_summary_counts(comparisons: Sequence[TdsShadowComparisonResponse]) -> dict[str, int]:
    counts = {
        "total_interviews": len(comparisons),
        "with_legacy_score": 0,
        "with_tds_decision": 0,
        "with_skills_summary": 0,
        "aligned": 0,
        "shifted_more_cautious": 0,
        "shifted_less_cautious": 0,
        "insufficient_evidence": 0,
        "legacy_only": 0,
        "tds_only": 0,
        "missing_both": 0,
    }
    for comparison in comparisons:
        if comparison.legacy_score_summary.present:
            counts["with_legacy_score"] += 1
        if comparison.tds_decision_summary.present:
            counts["with_tds_decision"] += 1
        if comparison.skills_summary_status.status == "present":
            counts["with_skills_summary"] += 1

        status = comparison.comparison_result.comparison_status
        if status in counts:
            counts[status] += 1
        if (
            not comparison.legacy_score_summary.present
            and not comparison.tds_decision_summary.present
        ):
            counts["missing_both"] += 1
    return counts


def _ordered_distinct(values: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered
