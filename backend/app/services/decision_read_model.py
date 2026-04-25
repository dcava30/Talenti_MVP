from __future__ import annotations

from app.models import DecisionOutcome
from app.schemas.decisions import (
    RecruiterDecisionEvidenceSummaryItem,
    RecruiterDecisionResponse,
    RecruiterDecisionRiskSummaryItem,
)
from app.schemas.decisioning import assert_behavioural_only_payload
from app.services.decision_persistence import decode_decision_outcome_payloads
from app.services.json_text import json_text_loads


_DECISION_SUMMARY_BY_STATE = {
    "PROCEED": "Behavioural evidence supports proceeding.",
    "PROCEED_WITH_CONDITIONS": "Behavioural evidence supports proceeding if the listed conditions are addressed.",
    "DO_NOT_PROCEED": "Behavioural evidence does not support proceeding.",
    "INSUFFICIENT_EVIDENCE": "Behavioural evidence is insufficient to reach a confident decision.",
}


def build_recruiter_decision_response(decision: DecisionOutcome) -> RecruiterDecisionResponse:
    decoded = decode_decision_outcome_payloads(decision)
    payload = {
        "decision_id": decision.id,
        "interview_id": decision.interview_id,
        "candidate_id": decision.candidate_id,
        "role_id": decision.role_id,
        "organisation_id": decision.organisation_id,
        "decision_state": decision.decision_state,
        "decision_valid": decision.decision_valid,
        "confidence_gate_passed": decision.confidence_gate_passed,
        "integrity_status": decision.integrity_status,
        "decision_summary": _build_decision_summary(decision.decision_state),
        "risk_summary": [item.model_dump(mode="python") for item in _build_risk_summary(decision)],
        "evidence_summary": [item.model_dump(mode="python") for item in _build_evidence_summary(decision)],
        "evidence_gaps": _coerce_list_of_strings(decoded["evidence_gaps"]),
        "conflict_flags": _coerce_list_of_strings(decoded["conflict_flags"]),
        "conditions": _coerce_list_of_strings(decoded["conditions"]),
        "trade_off_statement": decision.trade_off_statement,
        "rationale": decision.rationale,
        "rule_version": decision.rule_version,
        "policy_version": decision.policy_version,
        "created_at": decision.created_at,
    }
    assert_behavioural_only_payload(payload)
    return RecruiterDecisionResponse(**payload)


def _build_decision_summary(decision_state: str) -> str:
    return _DECISION_SUMMARY_BY_STATE.get(decision_state, "Behavioural decision available.")


def _build_risk_summary(decision: DecisionOutcome) -> list[RecruiterDecisionRiskSummaryItem]:
    ordered_rows = sorted(decision.risk_flags, key=lambda row: (row.created_at, row.id))
    items: list[RecruiterDecisionRiskSummaryItem] = []
    for row in ordered_rows:
        items.append(
            RecruiterDecisionRiskSummaryItem(
                severity=row.severity,
                source_dimension=row.source_dimension,
                summary=_build_risk_summary_text(row.risk_code, row.source_dimension),
            )
        )
    return items


def _build_evidence_summary(decision: DecisionOutcome) -> list[RecruiterDecisionEvidenceSummaryItem]:
    ordered_rows = sorted(decision.dimension_evaluations, key=lambda row: (row.created_at, row.id))
    items: list[RecruiterDecisionEvidenceSummaryItem] = []
    for row in ordered_rows:
        items.append(
            RecruiterDecisionEvidenceSummaryItem(
                dimension=row.dimension,
                outcome=row.outcome,
                evidence_summary=json_text_loads(row.evidence_summary_json, default=None),
                rationale=row.rationale,
            )
        )
    return items


def _build_risk_summary_text(risk_code: str | None, source_dimension: str | None) -> str:
    risk_text = _humanize_token(risk_code) if risk_code else "Behavioural risk"
    if source_dimension:
        return f"{risk_text} noted in {_humanize_token(source_dimension)}."
    return f"{risk_text} noted."


def _humanize_token(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _coerce_list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]
