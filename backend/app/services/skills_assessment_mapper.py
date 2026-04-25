from __future__ import annotations

from typing import Any, TypedDict


class SkillsAssessmentSummaryPayload(TypedDict, total=False):
    observed_competencies: dict[str, object]
    competency_coverage: dict[str, object]
    skill_gaps: list[str]
    evidence_strength: str
    confidence: str
    source_references: list[object]
    human_readable_summary: str | None
    requires_human_review: bool
    excluded_from_tds_decisioning: bool
    model_version: str | None


def _to_score_band(value: Any) -> str | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if 0.0 <= numeric <= 1.0:
        numeric *= 100.0

    if numeric >= 70:
        return "High"
    if numeric >= 40:
        return "Medium"
    return "Low"


def _to_confidence_band(scores: dict[str, Any]) -> str | None:
    confidence_values: list[float] = []
    for data in scores.values():
        if not isinstance(data, dict):
            continue
        confidence = data.get("confidence")
        if isinstance(confidence, (int, float)):
            confidence_values.append(float(confidence))

    if not confidence_values:
        return None

    average_confidence = sum(confidence_values) / len(confidence_values)
    if average_confidence >= 0.70:
        return "High"
    if average_confidence >= 0.40:
        return "Medium"
    return "Low"


def _normalize_model_version(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def map_model_service_2_output_to_skills_assessment_summary(
    model2_result: dict[str, Any],
) -> SkillsAssessmentSummaryPayload:
    """
    Adapt legacy model-service-2 output into a non-decisional skills summary.

    MVP1 governing rule: behaviour decides, skills informs. This mapper therefore
    preserves role-specific competency evidence while intentionally excluding any
    hiring-decision or ranking semantics from the persisted artifact.
    """
    if not isinstance(model2_result, dict):
        raise ValueError("model-service-2 output must be a dictionary")

    scores = model2_result.get("scores")
    if not isinstance(scores, dict) or not scores:
        raise ValueError("model-service-2 output contained no competency scores")

    observed_competencies: dict[str, object] = {}
    for competency, raw_data in scores.items():
        if not isinstance(competency, str) or not competency.strip() or not isinstance(raw_data, dict):
            continue

        mapped_competency: dict[str, object] = {}

        raw_score = raw_data.get("score")
        if isinstance(raw_score, (int, float)):
            normalized_score = float(raw_score)
            if 0.0 <= normalized_score <= 1.0:
                normalized_score *= 100.0
            mapped_competency["evidence_score"] = max(0, min(100, int(round(normalized_score))))

        confidence = raw_data.get("confidence")
        if isinstance(confidence, (int, float)):
            mapped_competency["confidence"] = float(confidence)

        rationale = raw_data.get("rationale")
        if isinstance(rationale, str) and rationale.strip():
            mapped_competency["rationale"] = rationale.strip()

        years_detected = raw_data.get("years_detected")
        if isinstance(years_detected, (int, float)):
            mapped_competency["years_detected"] = float(years_detected)

        matched_keywords = raw_data.get("matched_keywords")
        if isinstance(matched_keywords, list):
            mapped_competency["matched_keywords"] = [
                item for item in matched_keywords if isinstance(item, str) and item.strip()
            ]

        observed_competencies[competency.strip()] = mapped_competency

    if not observed_competencies:
        raise ValueError("model-service-2 output contained no mappable competencies")

    outcome = model2_result.get("outcome")
    normalized_outcome = outcome.strip().upper() if isinstance(outcome, str) else None
    summary = model2_result.get("summary")

    return {
        "observed_competencies": observed_competencies,
        "competency_coverage": {
            "required_competencies_observed": [
                item
                for item in (model2_result.get("must_haves_passed") or [])
                if isinstance(item, str) and item.strip()
            ],
            "required_competencies_missing": [
                item
                for item in (model2_result.get("must_haves_failed") or [])
                if isinstance(item, str) and item.strip()
            ],
        },
        "skill_gaps": [
            item for item in (model2_result.get("gaps") or []) if isinstance(item, str) and item.strip()
        ],
        # Legacy overall_score is translated into a broad evidence-strength band
        # only, so it cannot be mistaken for a hiring score or ranking signal.
        "evidence_strength": _to_score_band(model2_result.get("overall_score")),
        "confidence": _to_confidence_band(scores),
        "source_references": [
            {
                "producer": "model-service-2",
                "artifact_type": "skills_assessment_summary",
                "legacy_contract_adapter": "ms2-skills-summary-shadow-v1",
            }
        ],
        "human_readable_summary": summary.strip() if isinstance(summary, str) and summary.strip() else None,
        # Legacy PASS/REVIEW/FAIL outcomes are collapsed into a review flag only.
        "requires_human_review": normalized_outcome in {"REVIEW", "FAIL"},
        "excluded_from_tds_decisioning": True,
        "model_version": _normalize_model_version(model2_result.get("model_version")),
    }
