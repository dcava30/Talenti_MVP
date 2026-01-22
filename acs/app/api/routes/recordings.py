"""
Recording management API endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
import logging

from app.models.recording import (
    StartRecordingRequest,
    StartRecordingResponse,
    RecordingInfo,
    RecordingStatus
)
from app.services.recording import recording_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/start", response_model=StartRecordingResponse)
async def start_recording(request: StartRecordingRequest):
    """
    Start recording a call
    """
    try:
        logger.info(f"Starting recording for call: {request.server_call_id}")
        
        result = await recording_service.start_recording(
            server_call_id=request.server_call_id,
            interview_id=request.interview_id,
            recording_content_type=request.content_type,
            recording_channel_type=request.channel_type,
            recording_format_type=request.format_type
        )
        
        return StartRecordingResponse(
            recording_id=result["recording_id"],
            recording_state=result["recording_state"]
        )
        
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{recording_id}/pause")
async def pause_recording(recording_id: str):
    """
    Pause an active recording
    """
    try:
        await recording_service.pause_recording(recording_id)
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to pause recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{recording_id}/resume")
async def resume_recording(recording_id: str):
    """
    Resume a paused recording
    """
    try:
        await recording_service.resume_recording(recording_id)
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to resume recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{recording_id}/stop")
async def stop_recording(recording_id: str, background_tasks: BackgroundTasks):
    """
    Stop a recording and trigger processing
    """
    try:
        result = await recording_service.stop_recording(recording_id)
        
        # Process recording in background
        background_tasks.add_task(
            recording_service.process_recording,
            recording_id=recording_id
        )
        
        return {"success": True, "recording_state": result}
        
    except Exception as e:
        logger.error(f"Failed to stop recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recording_id}", response_model=RecordingInfo)
async def get_recording(recording_id: str):
    """
    Get recording information and status
    """
    try:
        info = await recording_service.get_recording_info(recording_id)
        
        if not info:
            raise HTTPException(status_code=404, detail="Recording not found")
            
        return RecordingInfo(**info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recording info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recording_id}/download")
async def download_recording(recording_id: str):
    """
    Download the recording file
    """
    try:
        stream, content_type, filename = await recording_service.download_recording(
            recording_id
        )
        
        if not stream:
            raise HTTPException(status_code=404, detail="Recording file not found")
        
        return StreamingResponse(
            stream,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{recording_id}")
async def delete_recording(recording_id: str):
    """
    Delete a recording and its associated files
    """
    try:
        await recording_service.delete_recording(recording_id)
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Failed to delete recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interview/{interview_id}", response_model=list[RecordingInfo])
async def get_interview_recordings(interview_id: str):
    """
    Get all recordings for an interview
    """
    try:
        recordings = await recording_service.get_interview_recordings(interview_id)
        return [RecordingInfo(**r) for r in recordings]
        
    except Exception as e:
        logger.error(f"Failed to get interview recordings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
