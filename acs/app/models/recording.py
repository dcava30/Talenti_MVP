"""
Recording-related data models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class RecordingState(str, Enum):
    """Recording state enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RecordingContentType(str, Enum):
    """Type of content to record"""
    AUDIO = "audio"
    AUDIO_VIDEO = "audioVideo"


class RecordingChannelType(str, Enum):
    """Recording channel configuration"""
    MIXED = "mixed"
    UNMIXED = "unmixed"


class RecordingFormatType(str, Enum):
    """Recording file format"""
    WAV = "wav"
    MP3 = "mp3"
    MP4 = "mp4"


class RecordingStatus(str, Enum):
    """Recording processing status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class StartRecordingRequest(BaseModel):
    """Request to start recording"""
    server_call_id: str = Field(..., description="Server call ID to record")
    interview_id: str = Field(..., description="Interview ID to associate recording with")
    content_type: RecordingContentType = Field(
        RecordingContentType.AUDIO,
        description="Type of content to record"
    )
    channel_type: RecordingChannelType = Field(
        RecordingChannelType.MIXED,
        description="Channel configuration"
    )
    format_type: RecordingFormatType = Field(
        RecordingFormatType.WAV,
        description="Output format"
    )


class StartRecordingResponse(BaseModel):
    """Response after starting recording"""
    recording_id: str
    recording_state: RecordingState


class RecordingChunk(BaseModel):
    """Information about a recording chunk"""
    document_id: str
    content_location: str
    delete_location: str
    index: int


class RecordingInfo(BaseModel):
    """Full recording information"""
    recording_id: str
    interview_id: str
    server_call_id: str
    state: RecordingState
    status: RecordingStatus = RecordingStatus.PENDING
    content_type: RecordingContentType
    channel_type: RecordingChannelType
    format_type: RecordingFormatType
    duration_ms: Optional[int] = None
    file_size_bytes: Optional[int] = None
    blob_url: Optional[str] = None
    chunks: List[RecordingChunk] = []
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class RecordingFileStatus(BaseModel):
    """ACS recording file status event data"""
    recording_storage_info: dict
    recording_start_time: datetime
    recording_duration_ms: int
    session_end_reason: str
