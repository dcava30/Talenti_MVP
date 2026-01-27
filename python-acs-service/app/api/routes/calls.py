"""
Call management API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import logging

from app.models.call import (
    CreateCallRequest,
    CreateCallResponse,
    CallInfo,
    PlayAudioRequest,
    AddParticipantRequest
)
from app.services.call_automation import call_automation_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=CreateCallResponse)
async def create_call(request: CreateCallRequest):
    """
    Create a new outbound call for an interview
    """
    try:
        logger.info(f"Creating call for interview: {request.interview_id}")
        
        result = await call_automation_service.create_call(
            interview_id=request.interview_id,
            target_identity=request.target_identity,
            source_identity=request.source_identity,
            callback_url=request.callback_url
        )
        
        return CreateCallResponse(
            call_connection_id=result["call_connection_id"],
            server_call_id=result["server_call_id"],
            correlation_id=result["correlation_id"]
        )
        
    except Exception as e:
        logger.error(f"Failed to create call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{call_connection_id}", response_model=CallInfo)
async def get_call(call_connection_id: str):
    """
    Get information about an active call
    """
    try:
        call_info = await call_automation_service.get_call(call_connection_id)
        
        if not call_info:
            raise HTTPException(status_code=404, detail="Call not found")
            
        return CallInfo(**call_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get call info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{call_connection_id}/answer")
async def answer_call(call_connection_id: str, callback_url: Optional[str] = None):
    """
    Answer an incoming call
    """
    try:
        result = await call_automation_service.answer_call(
            call_connection_id=call_connection_id,
            callback_url=callback_url
        )
        return {"success": True, "call_connection_id": result}
        
    except Exception as e:
        logger.error(f"Failed to answer call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{call_connection_id}/hangup")
async def hangup_call(call_connection_id: str, for_everyone: bool = True):
    """
    End a call
    """
    try:
        await call_automation_service.hangup_call(
            call_connection_id=call_connection_id,
            for_everyone=for_everyone
        )
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to hangup call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{call_connection_id}/play")
async def play_audio(call_connection_id: str, request: PlayAudioRequest):
    """
    Play audio (TTS or file) to the call
    """
    try:
        await call_automation_service.play_audio(
            call_connection_id=call_connection_id,
            text=request.text,
            audio_url=request.audio_url,
            voice_name=request.voice_name,
            loop=request.loop
        )
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to play audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{call_connection_id}/participants")
async def add_participant(call_connection_id: str, request: AddParticipantRequest):
    """
    Add a participant to the call
    """
    try:
        result = await call_automation_service.add_participant(
            call_connection_id=call_connection_id,
            target_identity=request.target_identity,
            source_identity=request.source_identity
        )
        return {"success": True, "participant_id": result}
        
    except Exception as e:
        logger.error(f"Failed to add participant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{call_connection_id}/participants/{participant_id}")
async def remove_participant(call_connection_id: str, participant_id: str):
    """
    Remove a participant from the call
    """
    try:
        await call_automation_service.remove_participant(
            call_connection_id=call_connection_id,
            participant_id=participant_id
        )
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to remove participant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{call_connection_id}/mute/{participant_id}")
async def mute_participant(call_connection_id: str, participant_id: str):
    """
    Mute a participant
    """
    try:
        await call_automation_service.mute_participant(
            call_connection_id=call_connection_id,
            participant_id=participant_id
        )
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to mute participant: {e}")
        raise HTTPException(status_code=500, detail=str(e))
