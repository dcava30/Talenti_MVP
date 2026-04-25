from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DecisionAuditTrail,
    DecisionDimensionEvaluation as DecisionDimensionEvaluationModel,
    DecisionOutcome,
    DecisionRiskFlag,
    DecisionSignalEvidence,
    HumanReviewAction,
)
from app.schemas.decisioning import BehaviouralDecisionOutput, assert_behavioural_only_payload
from app.services.json_text import json_text_dumps, json_text_loads


def create_decision_outcome_from_result(
    db: Session,
    *,
    decision_result: BehaviouralDecisionOutput | dict[str, Any],
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    org_environment_input_id: str | None = None,
    environment_profile: dict[str, Any] | None = None,
    actor_type: str = "system",
    actor_user_id: str | None = None,
) -> DecisionOutcome:
    result = _coerce_behavioural_decision_result(decision_result)
    clean_environment_profile = environment_profile or {}
    assert_behavioural_only_payload(clean_environment_profile)

    now = datetime.utcnow()
    decision = DecisionOutcome(
        interview_id=interview_id,
        candidate_id=candidate_id,
        role_id=role_id,
        organisation_id=organisation_id,
        org_environment_input_id=org_environment_input_id,
        decision_state=result.decision_state.value,
        decision_valid=result.decision_valid,
        confidence=result.confidence.value,
        confidence_gate_passed=result.confidence_gate_passed,
        integrity_status=result.integrity_status.value,
        environment_profile_json=json_text_dumps(clean_environment_profile) or "{}",
        critical_dimensions_json=json_text_dumps(result.critical_dimensions) or "[]",
        minimum_dimensions_json=json_text_dumps(result.minimum_dimensions) or "[]",
        priority_dimensions_json=json_text_dumps(result.priority_dimensions) or "[]",
        evidence_gaps_json=json_text_dumps(result.evidence_gaps) or "[]",
        invalid_signals_json=json_text_dumps(result.invalid_signals) or "[]",
        conflict_flags_json=json_text_dumps(result.conflict_flags) or "[]",
        execution_floor_result_json=json_text_dumps(result.execution_floor_result) or "{}",
        trade_off_statement=result.trade_off_statement,
        conditions_json=json_text_dumps(result.conditions) or "[]",
        rationale=result.rationale,
        audit_trace_json=json_text_dumps(result.audit_trace) or "[]",
        rule_version=result.rule_version,
        policy_version=result.policy_version,
        created_at=now,
        updated_at=now,
    )
    db.add(decision)
    db.flush()

    db.add_all(_build_dimension_evaluation_rows(decision.id, result))
    db.add_all(_build_risk_flag_rows(decision.id, result))
    db.add_all(_build_signal_evidence_rows(decision.id, result))

    create_decision_audit_event(
        db,
        decision_id=decision.id,
        event_type="decision_created",
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        rule_version=result.rule_version,
        policy_version=result.policy_version,
        event_payload={
            "decision_state": result.decision_state.value,
            "decision_valid": result.decision_valid,
            "confidence": result.confidence.value,
            "integrity_status": result.integrity_status.value,
            "risk_count": len(result.risk_stack),
            "condition_count": len(result.conditions),
        },
        event_at=now,
    )
    db.flush()
    return decision


def get_latest_decision_for_interview(db: Session, *, interview_id: str) -> DecisionOutcome | None:
    return db.execute(
        select(DecisionOutcome)
        .where(DecisionOutcome.interview_id == interview_id)
        .order_by(DecisionOutcome.created_at.desc(), DecisionOutcome.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_latest_decision_for_interview_version(
    db: Session,
    *,
    interview_id: str,
    rule_version: str,
    policy_version: str,
) -> DecisionOutcome | None:
    return db.execute(
        select(DecisionOutcome)
        .where(DecisionOutcome.interview_id == interview_id)
        .where(DecisionOutcome.rule_version == rule_version)
        .where(DecisionOutcome.policy_version == policy_version)
        .order_by(DecisionOutcome.created_at.desc(), DecisionOutcome.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_decision_by_id(db: Session, *, decision_id: str) -> DecisionOutcome | None:
    return db.get(DecisionOutcome, decision_id)


def list_decisions_for_role(db: Session, *, role_id: str) -> list[DecisionOutcome]:
    return list(
        db.execute(
            select(DecisionOutcome)
            .where(DecisionOutcome.role_id == role_id)
            .order_by(DecisionOutcome.created_at.desc(), DecisionOutcome.id.desc())
        ).scalars()
    )


def list_decisions_for_candidate(db: Session, *, candidate_id: str) -> list[DecisionOutcome]:
    return list(
        db.execute(
            select(DecisionOutcome)
            .where(DecisionOutcome.candidate_id == candidate_id)
            .order_by(DecisionOutcome.created_at.desc(), DecisionOutcome.id.desc())
        ).scalars()
    )


def get_decision_audit_trail(db: Session, *, decision_id: str) -> list[DecisionAuditTrail]:
    return list(
        db.execute(
            select(DecisionAuditTrail)
            .where(DecisionAuditTrail.decision_id == decision_id)
            .order_by(DecisionAuditTrail.created_at.asc(), DecisionAuditTrail.id.asc())
        ).scalars()
    )


def create_decision_audit_event(
    db: Session,
    *,
    decision_id: str,
    event_type: str,
    actor_type: str,
    actor_user_id: str | None = None,
    rule_version: str | None = None,
    policy_version: str | None = None,
    event_payload: dict[str, Any] | list[Any] | None = None,
    event_at: datetime | None = None,
) -> DecisionAuditTrail:
    event = DecisionAuditTrail(
        decision_id=decision_id,
        event_type=event_type,
        event_at=event_at or datetime.utcnow(),
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        rule_version=rule_version,
        policy_version=policy_version,
        event_payload_json=json_text_dumps(event_payload or {}) or "{}",
    )
    db.add(event)
    db.flush()
    return event


def create_human_review_action(
    db: Session,
    *,
    decision_id: str,
    action_type: str,
    reason: str,
    reviewed_by: str,
    review_outcome: str | None = None,
    notes: dict[str, Any] | list[Any] | None = None,
    display_delta: dict[str, Any] | list[Any] | None = None,
    create_audit_event: bool = True,
) -> HumanReviewAction:
    if not reason or not reason.strip():
        raise ValueError("Human review reason is required.")
    if not reviewed_by:
        raise ValueError("Human review reviewer user id is required.")

    decision = get_decision_by_id(db, decision_id=decision_id)
    if decision is None:
        raise ValueError(f"Decision outcome {decision_id} was not found.")

    review_action = HumanReviewAction(
        decision_id=decision.id,
        action_type=action_type,
        review_outcome=review_outcome,
        reason=reason.strip(),
        reviewed_by=reviewed_by,
        notes_json=json_text_dumps(notes),
        display_delta_json=json_text_dumps(display_delta),
    )
    db.add(review_action)
    db.flush()

    if create_audit_event:
        create_decision_audit_event(
            db,
            decision_id=decision.id,
            event_type="human_review_action_created",
            actor_type="human_reviewer",
            actor_user_id=reviewed_by,
            rule_version=decision.rule_version,
            policy_version=decision.policy_version,
            event_payload={
                "action_type": action_type,
                "review_outcome": review_outcome,
                "reason": reason.strip(),
                "original_system_decision_state": decision.decision_state,
                "human_review_action_id": review_action.id,
            },
        )

    return review_action


def decode_decision_outcome_payloads(decision: DecisionOutcome) -> dict[str, Any]:
    return {
        "environment_profile": json_text_loads(decision.environment_profile_json, default={}),
        "critical_dimensions": json_text_loads(decision.critical_dimensions_json, default=[]),
        "minimum_dimensions": json_text_loads(decision.minimum_dimensions_json, default=[]),
        "priority_dimensions": json_text_loads(decision.priority_dimensions_json, default=[]),
        "evidence_gaps": json_text_loads(decision.evidence_gaps_json, default=[]),
        "invalid_signals": json_text_loads(decision.invalid_signals_json, default=[]),
        "conflict_flags": json_text_loads(decision.conflict_flags_json, default=[]),
        "execution_floor_result": json_text_loads(decision.execution_floor_result_json, default={}),
        "conditions": json_text_loads(decision.conditions_json, default=[]),
        "audit_trace": json_text_loads(decision.audit_trace_json, default=[]),
    }


def _coerce_behavioural_decision_result(
    decision_result: BehaviouralDecisionOutput | dict[str, Any],
) -> BehaviouralDecisionOutput:
    assert_behavioural_only_payload(decision_result)
    if isinstance(decision_result, BehaviouralDecisionOutput):
        return decision_result
    return BehaviouralDecisionOutput.model_validate(decision_result)


def _build_dimension_evaluation_rows(
    decision_id: str,
    decision_result: BehaviouralDecisionOutput,
) -> list[DecisionDimensionEvaluationModel]:
    return [
        DecisionDimensionEvaluationModel(
            decision_id=decision_id,
            dimension=evaluation.dimension,
            score_internal=evaluation.score_internal,
            confidence=evaluation.confidence.value if evaluation.confidence else None,
            required_level=evaluation.required_level,
            threshold_status=evaluation.threshold_status,
            outcome=evaluation.outcome,
            evidence_summary_json=json_text_dumps(evaluation.evidence_summary),
            rationale=evaluation.rationale,
        )
        for evaluation in decision_result.dimension_evaluations
    ]


def _build_risk_flag_rows(
    decision_id: str,
    decision_result: BehaviouralDecisionOutput,
) -> list[DecisionRiskFlag]:
    return [
        DecisionRiskFlag(
            decision_id=decision_id,
            risk_code=risk.risk_code,
            severity=risk.severity.value,
            source_dimension=risk.source_dimension,
            trigger_rule=risk.trigger_rule,
            context_json=json_text_dumps(
                {
                    "source_dimension": risk.source_dimension,
                    "severity": risk.severity.value,
                    "trigger_rule": risk.trigger_rule,
                }
            ),
        )
        for risk in decision_result.risk_stack
    ]


def _build_signal_evidence_rows(
    decision_id: str,
    decision_result: BehaviouralDecisionOutput,
) -> list[DecisionSignalEvidence]:
    signal_rows: list[DecisionSignalEvidence] = []
    for evaluation in decision_result.dimension_evaluations:
        for signal_code in evaluation.valid_signals:
            signal_rows.append(
                DecisionSignalEvidence(
                    decision_id=decision_id,
                    dimension=evaluation.dimension,
                    signal_code=signal_code,
                    signal_status="VALID",
                )
            )
        for signal_code in evaluation.invalid_signals:
            signal_rows.append(
                DecisionSignalEvidence(
                    decision_id=decision_id,
                    dimension=evaluation.dimension,
                    signal_code=signal_code,
                    signal_status="INVALID",
                    # TODO: Persist richer source references and invalid reasons once
                    # upstream behavioural evidence includes provenance-rich signal data.
                )
            )
    return signal_rows
