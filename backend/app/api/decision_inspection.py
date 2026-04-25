from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_admin
from app.core.config import settings
from app.models import Application, DecisionOutcome, Interview, JobRole, OrgUser, User
from app.schemas.decision_inspection import (
    DecisionInspectionAuditEventResponse,
    DecisionInspectionAuditTrailSummaryResponse,
    DecisionInspectionDetailResponse,
    DecisionInspectionDimensionEvaluationResponse,
    DecisionInspectionRiskFlagResponse,
    DecisionInspectionSummaryResponse,
)
from app.schemas.decisioning import assert_behavioural_only_payload
from app.services.decision_persistence import (
    decode_decision_outcome_payloads,
    get_decision_audit_trail,
    get_decision_by_id,
    get_latest_decision_for_interview,
)
from app.services.json_text import json_text_loads

router = APIRouter(
    prefix="/api/v1/internal/decisions",
    tags=["internal-decision-inspection"],
    include_in_schema=settings.tds_decision_inspection_api_enabled,
)


def _require_inspection_admin(db: Session, org_id: str, user: User) -> None:
    try:
        require_org_admin(org_id, db, user)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organisation admins can access this resource.",
            ) from exc
        raise


def _ensure_inspection_api_enabled() -> None:
    if not settings.tds_decision_inspection_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision inspection API is not available.",
        )


def _get_interview_for_inspection(db: Session, interview_id: str) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return interview


def _get_role_for_inspection(db: Session, role_id: str) -> JobRole:
    role = db.get(JobRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


def _get_application_for_inspection(db: Session, application_id: str) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


def _get_admin_org_ids(db: Session, user: User) -> list[str]:
    return list(
        db.execute(
            select(OrgUser.organisation_id)
            .where(OrgUser.user_id == user.id)
            .where(OrgUser.role.in_(("admin", "owner")))
        ).scalars()
    )


def _build_audit_trail_summary(
    audit_entries: list[Any],
) -> DecisionInspectionAuditTrailSummaryResponse:
    ordered_event_types: list[str] = []
    for entry in audit_entries:
        if entry.event_type not in ordered_event_types:
            ordered_event_types.append(entry.event_type)
    return DecisionInspectionAuditTrailSummaryResponse(
        event_count=len(audit_entries),
        event_types=ordered_event_types,
        latest_event_at=audit_entries[-1].event_at if audit_entries else None,
    )


def _build_dimension_evaluations(decision: DecisionOutcome) -> list[DecisionInspectionDimensionEvaluationResponse]:
    ordered_rows = sorted(decision.dimension_evaluations, key=lambda row: (row.created_at, row.id))
    return [
        DecisionInspectionDimensionEvaluationResponse(
            id=row.id,
            dimension=row.dimension,
            score_internal=row.score_internal,
            confidence=row.confidence,
            required_level=row.required_level,
            threshold_status=row.threshold_status,
            outcome=row.outcome,
            evidence_summary=json_text_loads(row.evidence_summary_json, default=None),
            rationale=row.rationale,
            created_at=row.created_at,
        )
        for row in ordered_rows
    ]


def _build_risk_stack(decision: DecisionOutcome) -> list[DecisionInspectionRiskFlagResponse]:
    ordered_rows = sorted(decision.risk_flags, key=lambda row: (row.created_at, row.id))
    return [
        DecisionInspectionRiskFlagResponse(
            id=row.id,
            risk_code=row.risk_code,
            severity=row.severity,
            source_dimension=row.source_dimension,
            trigger_rule=row.trigger_rule,
            context=json_text_loads(row.context_json, default=None),
            created_at=row.created_at,
        )
        for row in ordered_rows
    ]


def _build_decision_summary(decision: DecisionOutcome) -> DecisionInspectionSummaryResponse:
    payload = {
        "decision_id": decision.id,
        "decision_mode": "shadow",
        "interview_id": decision.interview_id,
        "candidate_id": decision.candidate_id,
        "role_id": decision.role_id,
        "organisation_id": decision.organisation_id,
        "decision_state": decision.decision_state,
        "decision_valid": decision.decision_valid,
        "confidence": decision.confidence,
        "confidence_gate_passed": decision.confidence_gate_passed,
        "integrity_status": decision.integrity_status,
        "rule_version": decision.rule_version,
        "policy_version": decision.policy_version,
        "created_at": decision.created_at,
    }
    assert_behavioural_only_payload(payload)
    return DecisionInspectionSummaryResponse(**payload)


def _build_decision_detail(decision: DecisionOutcome, db: Session) -> DecisionInspectionDetailResponse:
    decoded = decode_decision_outcome_payloads(decision)
    audit_entries = get_decision_audit_trail(db, decision_id=decision.id)
    payload = {
        **_build_decision_summary(decision).model_dump(mode="python"),
        "org_environment_input_id": decision.org_environment_input_id,
        "environment_profile": decoded["environment_profile"],
        "critical_dimensions": decoded["critical_dimensions"],
        "minimum_dimensions": decoded["minimum_dimensions"],
        "priority_dimensions": decoded["priority_dimensions"],
        "dimension_evaluations": [item.model_dump(mode="python") for item in _build_dimension_evaluations(decision)],
        "evidence_gaps": decoded["evidence_gaps"],
        "invalid_signals": decoded["invalid_signals"],
        "conflict_flags": decoded["conflict_flags"],
        "risk_stack": [item.model_dump(mode="python") for item in _build_risk_stack(decision)],
        "execution_floor_result": decoded["execution_floor_result"],
        "trade_off_statement": decision.trade_off_statement,
        "conditions": decoded["conditions"],
        "rationale": decision.rationale,
        "audit_trace": decoded["audit_trace"],
        "audit_trail_summary": _build_audit_trail_summary(audit_entries).model_dump(mode="python"),
    }
    assert_behavioural_only_payload(payload)
    return DecisionInspectionDetailResponse(**payload)


def _get_decision_or_404(db: Session, decision_id: str) -> DecisionOutcome:
    decision = get_decision_by_id(db, decision_id=decision_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return decision


@router.get("/interviews/{interview_id}/latest", response_model=DecisionInspectionDetailResponse)
def get_latest_interview_decision(
    interview_id: str,
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DecisionInspectionDetailResponse:
    interview = _get_interview_for_inspection(db, interview_id)
    application = _get_application_for_inspection(db, interview.application_id)
    role = _get_role_for_inspection(db, application.job_role_id)
    _require_inspection_admin(db, role.organisation_id, user)

    decision = get_latest_decision_for_interview(db, interview_id=interview_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return _build_decision_detail(decision, db)


@router.get("/roles/{role_id}", response_model=list[DecisionInspectionSummaryResponse])
def list_role_decisions(
    role_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DecisionInspectionSummaryResponse]:
    role = _get_role_for_inspection(db, role_id)
    _require_inspection_admin(db, role.organisation_id, user)

    decisions = list(
        db.execute(
            select(DecisionOutcome)
            .where(DecisionOutcome.role_id == role_id)
            .order_by(DecisionOutcome.created_at.desc(), DecisionOutcome.id.desc())
            .offset(offset)
            .limit(limit)
        ).scalars()
    )
    return [_build_decision_summary(decision) for decision in decisions]


@router.get("/candidates/{candidate_id}", response_model=list[DecisionInspectionSummaryResponse])
def list_candidate_decisions(
    candidate_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DecisionInspectionSummaryResponse]:
    admin_org_ids = _get_admin_org_ids(db, user)
    if not admin_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can access this resource.",
        )

    decisions = list(
        db.execute(
            select(DecisionOutcome)
            .where(DecisionOutcome.candidate_id == candidate_id)
            .where(DecisionOutcome.organisation_id.in_(admin_org_ids))
            .order_by(DecisionOutcome.created_at.desc(), DecisionOutcome.id.desc())
            .offset(offset)
            .limit(limit)
        ).scalars()
    )
    return [_build_decision_summary(decision) for decision in decisions]


@router.get("/{decision_id}/audit-trace", response_model=list[DecisionInspectionAuditEventResponse])
def get_decision_audit_trace(
    decision_id: str,
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DecisionInspectionAuditEventResponse]:
    decision = _get_decision_or_404(db, decision_id)
    _require_inspection_admin(db, decision.organisation_id, user)

    return [
        DecisionInspectionAuditEventResponse(
            id=entry.id,
            decision_id=entry.decision_id,
            event_type=entry.event_type,
            event_at=entry.event_at,
            actor_type=entry.actor_type,
            actor_user_id=entry.actor_user_id,
            rule_version=entry.rule_version,
            policy_version=entry.policy_version,
            event_payload=json_text_loads(entry.event_payload_json, default={}),
            created_at=entry.created_at,
        )
        for entry in get_decision_audit_trail(db, decision_id=decision.id)
    ]


@router.get("/{decision_id}", response_model=DecisionInspectionDetailResponse)
def get_decision(
    decision_id: str,
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DecisionInspectionDetailResponse:
    decision = _get_decision_or_404(db, decision_id)
    _require_inspection_admin(db, decision.organisation_id, user)
    return _build_decision_detail(decision, db)
