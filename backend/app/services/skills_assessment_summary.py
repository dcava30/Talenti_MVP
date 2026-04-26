from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SkillsAssessmentSummary
from app.services.json_text import json_text_dumps, json_text_loads


def create_skills_assessment_summary(
    db: Session,
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    observed_competencies: list[str] | dict[str, object] | None = None,
    competency_coverage: dict[str, object] | list[object] | None = None,
    skill_gaps: list[str] | dict[str, object] | None = None,
    evidence_strength: str | None = None,
    confidence: str | None = None,
    source_references: list[object] | dict[str, object] | None = None,
    human_readable_summary: str | None = None,
    requires_human_review: bool = False,
    excluded_from_tds_decisioning: bool = True,
    model_version: str | None = None,
) -> SkillsAssessmentSummary:
    # MVP1 boundary: this artifact is always informational only and must remain
    # excluded from behavioural TDS decisioning even if a caller passes False.
    summary = SkillsAssessmentSummary(
        interview_id=interview_id,
        candidate_id=candidate_id,
        role_id=role_id,
        organisation_id=organisation_id,
        observed_competencies_json=json_text_dumps(observed_competencies),
        competency_coverage_json=json_text_dumps(competency_coverage),
        skill_gaps_json=json_text_dumps(skill_gaps),
        evidence_strength=evidence_strength,
        confidence=confidence,
        source_references_json=json_text_dumps(source_references),
        human_readable_summary=human_readable_summary,
        requires_human_review=requires_human_review,
        excluded_from_tds_decisioning=True,
        model_version=model_version,
    )
    db.add(summary)
    db.flush()
    return summary


def get_latest_skills_assessment_summary_for_interview(
    db: Session,
    *,
    interview_id: str,
) -> SkillsAssessmentSummary | None:
    return db.execute(
        select(SkillsAssessmentSummary)
        .where(SkillsAssessmentSummary.interview_id == interview_id)
        .order_by(SkillsAssessmentSummary.created_at.desc(), SkillsAssessmentSummary.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_latest_skills_assessment_summary_for_interview_model_version(
    db: Session,
    *,
    interview_id: str,
    model_version: str,
) -> SkillsAssessmentSummary | None:
    return db.execute(
        select(SkillsAssessmentSummary)
        .where(SkillsAssessmentSummary.interview_id == interview_id)
        .where(SkillsAssessmentSummary.model_version == model_version)
        .order_by(SkillsAssessmentSummary.created_at.desc(), SkillsAssessmentSummary.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_skills_assessment_summary_by_id(
    db: Session,
    *,
    summary_id: str,
) -> SkillsAssessmentSummary | None:
    return db.get(SkillsAssessmentSummary, summary_id)


def list_skills_assessment_summaries_for_role(
    db: Session,
    *,
    role_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[SkillsAssessmentSummary]:
    return list(
        db.execute(
            select(SkillsAssessmentSummary)
            .where(SkillsAssessmentSummary.role_id == role_id)
            .order_by(SkillsAssessmentSummary.created_at.desc(), SkillsAssessmentSummary.id.desc())
            .offset(offset)
            .limit(limit)
        ).scalars()
    )


def list_skills_assessment_summaries_for_candidate(
    db: Session,
    *,
    candidate_id: str,
    organisation_ids: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[SkillsAssessmentSummary]:
    query = (
        select(SkillsAssessmentSummary)
        .where(SkillsAssessmentSummary.candidate_id == candidate_id)
        .order_by(SkillsAssessmentSummary.created_at.desc(), SkillsAssessmentSummary.id.desc())
        .offset(offset)
        .limit(limit)
    )
    if organisation_ids is not None:
        query = query.where(SkillsAssessmentSummary.organisation_id.in_(organisation_ids))
    return list(db.execute(query).scalars())


def decode_skills_assessment_summary_payloads(summary: SkillsAssessmentSummary) -> dict[str, Any]:
    return {
        "observed_competencies": _load_structured_json(
            summary.observed_competencies_json,
            default=[],
            allowed_types=(list, dict),
        ),
        "competency_coverage": _load_structured_json(
            summary.competency_coverage_json,
            default={},
            allowed_types=(dict,),
        ),
        "skill_gaps": _load_structured_json(
            summary.skill_gaps_json,
            default=[],
            allowed_types=(list,),
        ),
        "source_references": _load_structured_json(
            summary.source_references_json,
            default=[],
            allowed_types=(list,),
        ),
    }


def _load_structured_json(
    payload: str | None,
    *,
    default: Any,
    allowed_types: tuple[type[Any], ...],
) -> Any:
    value = json_text_loads(payload, default=default)
    if isinstance(value, allowed_types):
        return value
    return default
