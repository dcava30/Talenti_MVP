from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_admin
from app.core.config import settings
from app.models import User
from app.schemas.human_review import (
    CreateHumanReviewActionRequest,
    HumanReviewActionResponse,
)
from app.services.decision_persistence import (
    create_human_review_action,
    decode_human_review_action_payloads,
    get_decision_audit_trail,
    get_decision_by_id,
    list_human_review_actions_for_decision,
)
from app.services.json_text import json_text_loads

router = APIRouter(
    prefix="/api/v1/decisions",
    tags=["decision-human-review"],
    include_in_schema=settings.tds_human_review_api_enabled,
)


def _ensure_human_review_api_enabled() -> None:
    if not settings.tds_human_review_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision human review API is not available.",
        )


def _require_human_review_admin(db: Session, org_id: str, user: User) -> None:
    # TODO: tighten this to platform/internal review scopes before any exposure beyond org admins.
    try:
        require_org_admin(org_id, db, user)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organisation admins can access this resource.",
            ) from exc
        raise


def _get_decision_or_404(db: Session, decision_id: str):
    decision = get_decision_by_id(db, decision_id=decision_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return decision


def _build_human_review_audit_event_map(decision_id: str, db: Session) -> dict[str, str]:
    event_map: dict[str, str] = {}
    for event in get_decision_audit_trail(db, decision_id=decision_id):
        if event.event_type != "human_review_action_created":
            continue
        payload = json_text_loads(event.event_payload_json, default={})
        if not isinstance(payload, dict):
            continue
        human_review_action_id = payload.get("human_review_action_id")
        if isinstance(human_review_action_id, str):
            event_map[human_review_action_id] = event.id
    return event_map


def _build_human_review_response(action, *, original_decision_state: str, audit_event_id: str | None) -> HumanReviewActionResponse:
    decoded = decode_human_review_action_payloads(action)
    return HumanReviewActionResponse(
        human_review_action_id=action.id,
        decision_id=action.decision_id,
        original_decision_state=original_decision_state,
        action_type=action.action_type,
        review_outcome=action.review_outcome,
        reason=action.reason,
        notes=decoded["notes"],
        display_delta=decoded["display_delta"],
        reviewed_by=action.reviewed_by,
        created_at=action.created_at,
        audit_event_id=audit_event_id,
    )


@router.post(
    "/{decision_id}/human-review",
    response_model=HumanReviewActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_decision_human_review_action(
    decision_id: str,
    payload: CreateHumanReviewActionRequest,
    _: None = Depends(_ensure_human_review_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HumanReviewActionResponse:
    decision = _get_decision_or_404(db, decision_id)
    _require_human_review_admin(db, decision.organisation_id, user)
    original_decision_state = decision.decision_state

    review_action = create_human_review_action(
        db,
        decision_id=decision.id,
        action_type=payload.action_type.value,
        review_outcome=payload.review_outcome.value,
        reason=payload.reason,
        reviewed_by=user.id,
        notes=payload.notes,
        display_delta=payload.display_delta,
    )
    db.commit()
    db.refresh(review_action)

    audit_event_id = _build_human_review_audit_event_map(decision.id, db).get(review_action.id)
    return _build_human_review_response(
        review_action,
        original_decision_state=original_decision_state,
        audit_event_id=audit_event_id,
    )


@router.get(
    "/{decision_id}/human-review",
    response_model=list[HumanReviewActionResponse],
)
def list_decision_human_review_actions(
    decision_id: str,
    _: None = Depends(_ensure_human_review_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[HumanReviewActionResponse]:
    decision = _get_decision_or_404(db, decision_id)
    _require_human_review_admin(db, decision.organisation_id, user)

    actions = list_human_review_actions_for_decision(db, decision_id=decision.id)
    audit_event_ids = _build_human_review_audit_event_map(decision.id, db)
    return [
        _build_human_review_response(
            action,
            original_decision_state=decision.decision_state,
            audit_event_id=audit_event_ids.get(action.id),
        )
        for action in actions
    ]
