from __future__ import annotations

from typing import Any

from app.models import SkillsAssessmentSummary
from app.schemas.skills_assessment_summaries import RecruiterSkillsAssessmentSummaryResponse
from app.services.skills_assessment_summary import decode_skills_assessment_summary_payloads

_DECISIONING_BOUNDARY_NOTE = "This summary is not used in the behavioural TDS decision outcome."
_FORBIDDEN_SOURCE_REFERENCE_KEYS = {
    "best_candidate",
    "confidence_gate_passed",
    "decision_id",
    "decision_state",
    "decision_summary_present",
    "decision_valid",
    "hiring_outcome",
    "integrity_status",
    "match_score",
    "outcome",
    "pass",
    "ranking",
    "rank",
    "raw_fail_marker",
    "raw_hiring_label",
    "raw_review_marker",
    "recommendation",
    "review",
    "risk_stack",
    "shortlist_position",
    "skills_outcome",
}
_FORBIDDEN_SUMMARY_TOKENS = ("PASS", "REVIEW", "FAIL")


def build_recruiter_skills_assessment_summary_response(
    summary: SkillsAssessmentSummary,
) -> RecruiterSkillsAssessmentSummaryResponse:
    decoded = decode_skills_assessment_summary_payloads(summary)
    return RecruiterSkillsAssessmentSummaryResponse(
        skills_summary_id=summary.id,
        interview_id=summary.interview_id,
        candidate_id=summary.candidate_id,
        role_id=summary.role_id,
        organisation_id=summary.organisation_id,
        observed_competencies=decoded["observed_competencies"],
        competency_coverage=decoded["competency_coverage"],
        skill_gaps=decoded["skill_gaps"],
        evidence_strength=summary.evidence_strength,
        confidence=summary.confidence,
        source_references=sanitize_skills_source_references(decoded["source_references"]),
        human_readable_summary=sanitize_skills_human_readable_summary(summary.human_readable_summary),
        requires_human_review=summary.requires_human_review,
        excluded_from_tds_decisioning=enforce_skills_decisioning_exclusion(summary.excluded_from_tds_decisioning),
        decisioning_boundary_note=_DECISIONING_BOUNDARY_NOTE,
        model_version=summary.model_version,
        created_at=summary.created_at,
    )


def enforce_skills_decisioning_exclusion(_value: bool | None) -> bool:
    return True


def sanitize_skills_source_references(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    items: list[dict[str, Any]] = []
    for raw_item in value:
        item = sanitize_skills_source_reference_item(raw_item)
        if item:
            items.append(item)
    return items


def sanitize_skills_source_reference_item(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        return {"reference": normalized}

    if not isinstance(value, dict):
        return None

    item: dict[str, Any] = {}
    source = _first_non_empty_string(value, "source", "producer", "service")
    if source:
        item["source"] = source

    artifact_type = _first_non_empty_string(value, "artifact_type", "evidence_type", "type")
    if artifact_type:
        item["artifact_type"] = artifact_type

    for key in (
        "artifact_id",
        "reference",
        "reference_id",
        "legacy_contract_adapter",
        "locator",
        "segment_id",
        "title",
        "label",
        "url",
        "uri",
        "path",
        "page",
        "section",
        "timestamp",
        "start_ms",
        "end_ms",
        "start_time",
        "end_time",
        "note",
    ):
        if key not in value:
            continue
        sanitized_value = _sanitize_source_reference_value(key, value[key])
        if sanitized_value is not None:
            item[key] = sanitized_value

    return item or None


def _sanitize_source_reference_value(key: str, value: Any) -> Any:
    normalized_key = key.strip().lower()
    if normalized_key in _FORBIDDEN_SOURCE_REFERENCE_KEYS:
        return None

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    if isinstance(value, bool | int | float):
        return value

    if isinstance(value, list):
        items = []
        for raw_item in value:
            sanitized_item = _sanitize_source_reference_value(key, raw_item)
            if sanitized_item is not None:
                items.append(sanitized_item)
        return items or None

    if isinstance(value, dict):
        nested: dict[str, Any] = {}
        for nested_key, nested_value in value.items():
            if not isinstance(nested_key, str):
                continue
            sanitized_value = _sanitize_source_reference_value(nested_key, nested_value)
            if sanitized_value is not None:
                nested[nested_key] = sanitized_value
        return nested or None

    return None


def sanitize_skills_human_readable_summary(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if any(token in normalized.upper().split() for token in _FORBIDDEN_SUMMARY_TOKENS):
        return "Skills evidence summary available for recruiter review."
    return normalized


def _first_non_empty_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return None
