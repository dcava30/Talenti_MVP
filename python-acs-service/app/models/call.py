"""
Call-related data models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class CallState(str, Enum):
    """Call state enumeration"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    TRANSFERRING = "transferring"
    TRANSFER_ACCEPTED = "transferAccepted"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class CreateCallRequest(BaseModel):
    """Request to create a new call"""
    interview_id: str = Field(..., description="Interview ID to associate with the call")
    target_identity: str = Field(..., description="Target participant identity (ACS user ID or phone)")
    source_identity: Optional[str] = Field(None, description="Source identity for the call")
    callback_url: Optional[str] = Field(None, description="Callback URL for call events")


class CreateCallResponse(BaseModel):
    """Response after creating a call"""
    call_connection_id: str
    server_call_id: str
    correlation_id: str


class CallInfo(BaseModel):
    """Information about an active call"""
    call_connection_id: str
    server_call_id: str
    correlation_id: Optional[str] = None
    call_state: CallState
    source: Optional[str] = None
    targets: List[str] = []
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None


class PlayAudioRequest(BaseModel):
    """Request to play audio in a call"""
    text: Optional[str] = Field(None, description="Text to speak using TTS")
    audio_url: Optional[str] = Field(None, description="URL of audio file to play")
    voice_name: str = Field("en-AU-NatashaNeural", description="Azure TTS voice name")
    loop: bool = Field(False, description="Whether to loop the audio")


class AddParticipantRequest(BaseModel):
    """Request to add a participant to a call"""
    target_identity: str = Field(..., description="Target participant identity")
    source_identity: Optional[str] = Field(None, description="Source display identity")


class ParticipantInfo(BaseModel):
    """Information about a call participant"""
    identifier: str
    is_muted: bool = False
    is_on_hold: bool = False


class CallEventData(BaseModel):
    """ACS call event data"""
    event_type: str
    call_connection_id: str
    server_call_id: str
    correlation_id: Optional[str] = None
    result_info: Optional[dict] = None
    participants: Optional[List[ParticipantInfo]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
