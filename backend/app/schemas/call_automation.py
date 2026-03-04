from datetime import datetime

from pydantic import BaseModel


class CreateCallRequest(BaseModel):
    interview_id: str
    target_identity: str
    source_identity: str | None = None


class CreateCallResponse(BaseModel):
    call_connection_id: str
    server_call_id: str | None = None
    correlation_id: str | None = None


class StartRecordingRequest(BaseModel):
    interview_id: str
    server_call_id: str
    content_type: str = "audio"
    channel_type: str = "mixed"
    format_type: str = "wav"


class StartRecordingResponse(BaseModel):
    recording_id: str
    recording_state: str


class StopRecordingResponse(BaseModel):
    recording_state: str


class WorkerRecordingEvent(BaseModel):
    interview_id: str
    recording_id: str
    status: str
    recording_url: str | None = None
    error_message: str | None = None
    processed_at: datetime | None = None
