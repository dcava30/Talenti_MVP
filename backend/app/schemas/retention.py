from pydantic import BaseModel


class RetentionCleanupRequest(BaseModel):
    organisation_id: str
    retention_days: int


class RetentionCleanupResponse(BaseModel):
    interviews_removed: int
    recordings_removed: int
    applications_anonymized: int
