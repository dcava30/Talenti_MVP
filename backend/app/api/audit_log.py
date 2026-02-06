from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import AuditLog, User
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_log(
    organisation_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AuditLogResponse]:
    query = db.query(AuditLog)
    if organisation_id:
        query = query.filter(AuditLog.organisation_id == organisation_id)
    entries = query.order_by(AuditLog.created_at.desc()).all()
    return [
        AuditLogResponse(
            id=entry.id,
            user_id=entry.user_id,
            organisation_id=entry.organisation_id,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            old_values=entry.old_values,
            new_values=entry.new_values,
            ip_address=entry.ip_address,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


@router.post("", response_model=AuditLogResponse)
def create_audit_log(
    payload: AuditLogCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditLogResponse:
    entry = AuditLog(
        user_id=user.id,
        organisation_id=payload.organisation_id,
        action=payload.action,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        old_values=payload.old_values,
        new_values=payload.new_values,
        ip_address=payload.ip_address,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return AuditLogResponse(
        id=entry.id,
        user_id=entry.user_id,
        organisation_id=entry.organisation_id,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        old_values=entry.old_values,
        new_values=entry.new_values,
        ip_address=entry.ip_address,
        created_at=entry.created_at,
    )
