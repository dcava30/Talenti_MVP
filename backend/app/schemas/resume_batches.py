from datetime import datetime

from pydantic import BaseModel


class ResumeBatchCreate(BaseModel):
    job_role_id: str
    title: str | None = None


class ResumeBatchResponse(BaseModel):
    id: str
    organisation_id: str
    job_role_id: str
    status: str
    title: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ResumeBatchItemUploadRequest(BaseModel):
    file_name: str
    content_type: str | None = None


class ResumeBatchItemUploadResponse(BaseModel):
    item_id: str
    file_id: str
    blob_path: str
    upload_url: str
    expires_in_minutes: int


class ResumeBatchItemUpdate(BaseModel):
    recruiter_review_status: str | None = None
    candidate_email: str | None = None


class ResumeBatchInviteRequest(BaseModel):
    item_ids: list[str] | None = None
    expires_in_days: int = 7


class ResumeBatchProcessResponse(BaseModel):
    ok: bool
    queued_items: int


class ResumeBatchInviteResponse(BaseModel):
    ok: bool
    queued_items: int


class ResumeBatchItemResponse(BaseModel):
    id: str
    batch_id: str
    file_id: str
    parse_status: str
    recruiter_review_status: str
    candidate_email: str | None = None
    candidate_name: str | None = None
    parse_confidence: dict | None = None
    parse_error: str | None = None
    matched_user_id: str | None = None
    candidate_profile_id: str | None = None
    application_id: str | None = None
    snapshot_id: str | None = None
    invitation_id: str | None = None
    uploaded_at: datetime | None = None
    processed_at: datetime | None = None
    invited_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
