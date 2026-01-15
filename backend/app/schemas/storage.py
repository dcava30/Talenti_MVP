from pydantic import BaseModel


class UploadUrlRequest(BaseModel):
    organisation_id: str | None = None
    file_name: str
    content_type: str | None = None


class UploadUrlResponse(BaseModel):
    file_id: str
    blob_path: str
    upload_url: str
    expires_in_minutes: int
