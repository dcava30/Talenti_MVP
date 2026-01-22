from pydantic import BaseModel


class RetentionCleanupRequest(BaseModel):
    retention_days: int


class RetentionCleanupResponse(BaseModel):
    interviews_removed: int
    recordings_removed: int
    applications_anonymized: int
