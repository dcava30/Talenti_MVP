from datetime import datetime

from pydantic import BaseModel


class AuditLogCreate(BaseModel):
    organisation_id: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    old_values: str | None = None
    new_values: str | None = None
    ip_address: str | None = None


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None
    organisation_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    old_values: str | None
    new_values: str | None
    ip_address: str | None
    created_at: datetime
