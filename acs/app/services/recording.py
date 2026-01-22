"""
Recording management service
"""
from azure.communication.callautomation import (
    RecordingContent,
    RecordingChannel,
    RecordingFormat
)
from azure.communication.callautomation.aio import CallAutomationClient as AsyncCallAutomationClient
from azure.storage.blob.aio import BlobServiceClient
from typing import Optional, Dict, Any, List, Tuple, AsyncIterator
import logging
import httpx
from datetime import datetime

from app.config import settings
from app.models.recording import (
    RecordingContentType,
    RecordingChannelType,
    RecordingFormatType,
    RecordingState,
    RecordingStatus
)
from app.services.supabase_client import supabase_service

logger = logging.getLogger(__name__)


class RecordingService:
    """
    Service for managing call recordings
    """
    
    def __init__(self):
        self._acs_client: Optional[AsyncCallAutomationClient] = None
        self._blob_client: Optional[BlobServiceClient] = None
        self._recordings: Dict[str, Dict[str, Any]] = {}  # In-memory cache
    
    @property
    def acs_client(self) -> AsyncCallAutomationClient:
        """Lazy initialization of the ACS client"""
        if self._acs_client is None:
            self._acs_client = AsyncCallAutomationClient.from_connection_string(
                settings.ACS_CONNECTION_STRING
            )
        return self._acs_client
    
    @property
    def blob_client(self) -> BlobServiceClient:
        """Lazy initialization of the Blob client"""
        if self._blob_client is None:
            self._blob_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
        return self._blob_client
    
    def _map_content_type(self, content_type: RecordingContentType) -> RecordingContent:
        """Map our enum to ACS enum"""
        return RecordingContent.AUDIO if content_type == RecordingContentType.AUDIO else RecordingContent.AUDIO_VIDEO
    
    def _map_channel_type(self, channel_type: RecordingChannelType) -> RecordingChannel:
        """Map our enum to ACS enum"""
        return RecordingChannel.MIXED if channel_type == RecordingChannelType.MIXED else RecordingChannel.UNMIXED
    
    def _map_format_type(self, format_type: RecordingFormatType) -> RecordingFormat:
        """Map our enum to ACS enum"""
        mapping = {
            RecordingFormatType.WAV: RecordingFormat.WAV,
            RecordingFormatType.MP3: RecordingFormat.MP3,
            RecordingFormatType.MP4: RecordingFormat.MP4
        }
        return mapping.get(format_type, RecordingFormat.WAV)
    
    async def start_recording(
        self,
        server_call_id: str,
        interview_id: str,
        recording_content_type: RecordingContentType = RecordingContentType.AUDIO,
        recording_channel_type: RecordingChannelType = RecordingChannelType.MIXED,
        recording_format_type: RecordingFormatType = RecordingFormatType.WAV
    ) -> Dict[str, Any]:
        """
        Start recording a call
        """
        logger.info(f"Starting recording for server call: {server_call_id}")
        
        result = await self.acs_client.start_recording(
            call_locator=server_call_id,
            recording_content_type=self._map_content_type(recording_content_type),
            recording_channel_type=self._map_channel_type(recording_channel_type),
            recording_format_type=self._map_format_type(recording_format_type)
        )
        
        recording_id = result.recording_id
        
        # Store recording metadata
        self._recordings[recording_id] = {
            "recording_id": recording_id,
            "interview_id": interview_id,
            "server_call_id": server_call_id,
            "state": RecordingState.ACTIVE,
            "status": RecordingStatus.PENDING,
            "content_type": recording_content_type,
            "channel_type": recording_channel_type,
            "format_type": recording_format_type,
            "started_at": datetime.utcnow()
        }
        
        # Update interview record
        await supabase_service.update_interview(
            interview_id,
            {"recording_started": True, "recording_id": recording_id}
        )
        
        return {
            "recording_id": recording_id,
            "recording_state": RecordingState.ACTIVE
        }
    
    async def pause_recording(self, recording_id: str) -> None:
        """Pause an active recording"""
        await self.acs_client.pause_recording(recording_id)
        
        if recording_id in self._recordings:
            self._recordings[recording_id]["state"] = RecordingState.PAUSED
        
        logger.info(f"Recording {recording_id} paused")
    
    async def resume_recording(self, recording_id: str) -> None:
        """Resume a paused recording"""
        await self.acs_client.resume_recording(recording_id)
        
        if recording_id in self._recordings:
            self._recordings[recording_id]["state"] = RecordingState.ACTIVE
        
        logger.info(f"Recording {recording_id} resumed")
    
    async def stop_recording(self, recording_id: str) -> RecordingState:
        """Stop a recording"""
        await self.acs_client.stop_recording(recording_id)
        
        if recording_id in self._recordings:
            self._recordings[recording_id]["state"] = RecordingState.STOPPED
            self._recordings[recording_id]["stopped_at"] = datetime.utcnow()
        
        logger.info(f"Recording {recording_id} stopped")
        return RecordingState.STOPPED
    
    async def get_recording_info(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Get recording information"""
        return self._recordings.get(recording_id)
    
    async def process_recording(self, recording_id: str) -> None:
        """
        Process a completed recording:
        1. Download from ACS
        2. Upload to Azure Blob Storage
        3. Update database
        """
        if recording_id not in self._recordings:
            logger.error(f"Recording {recording_id} not found")
            return
        
        recording = self._recordings[recording_id]
        recording["status"] = RecordingStatus.DOWNLOADING
        
        try:
            # Get download URL from ACS
            logger.info(f"Downloading recording {recording_id}")
            recording["status"] = RecordingStatus.DOWNLOADING
            
            # Download the recording content
            stream = await self.acs_client.download_recording(recording_id)
            content = await stream.readall()
            
            recording["status"] = RecordingStatus.UPLOADING
            
            # Upload to Azure Blob Storage
            interview_id = recording["interview_id"]
            format_type = recording["format_type"]
            blob_name = f"{interview_id}/{recording_id}.{format_type.value}"
            
            container_client = self.blob_client.get_container_client(
                settings.RECORDING_CONTAINER
            )
            
            # Ensure container exists
            try:
                await container_client.create_container()
            except Exception:
                pass  # Container already exists
            
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.upload_blob(content, overwrite=True)
            
            blob_url = blob_client.url
            
            # Update recording metadata
            recording["status"] = RecordingStatus.COMPLETED
            recording["blob_url"] = blob_url
            recording["file_size_bytes"] = len(content)
            recording["processed_at"] = datetime.utcnow()
            
            # Update interview record in Supabase
            await supabase_service.update_interview(
                interview_id,
                {
                    "recording_url": blob_url,
                    "recording_processed": True
                }
            )
            
            logger.info(f"Recording {recording_id} processed and uploaded to {blob_url}")
            
        except Exception as e:
            logger.error(f"Failed to process recording {recording_id}: {e}")
            recording["status"] = RecordingStatus.FAILED
            recording["error_message"] = str(e)
    
    async def download_recording(
        self,
        recording_id: str
    ) -> Tuple[Optional[AsyncIterator[bytes]], str, str]:
        """
        Download a recording file
        Returns: (stream, content_type, filename)
        """
        recording = self._recordings.get(recording_id)
        
        if not recording or not recording.get("blob_url"):
            return None, "", ""
        
        blob_url = recording["blob_url"]
        format_type = recording["format_type"]
        
        content_types = {
            RecordingFormatType.WAV: "audio/wav",
            RecordingFormatType.MP3: "audio/mpeg",
            RecordingFormatType.MP4: "video/mp4"
        }
        
        # Parse blob URL to get container and blob name
        interview_id = recording["interview_id"]
        blob_name = f"{interview_id}/{recording_id}.{format_type.value}"
        
        container_client = self.blob_client.get_container_client(
            settings.RECORDING_CONTAINER
        )
        blob_client = container_client.get_blob_client(blob_name)
        
        stream = await blob_client.download_blob()
        
        return (
            stream.chunks(),
            content_types.get(format_type, "application/octet-stream"),
            f"{recording_id}.{format_type.value}"
        )
    
    async def delete_recording(self, recording_id: str) -> None:
        """Delete a recording and its files"""
        recording = self._recordings.get(recording_id)
        
        if not recording:
            logger.warning(f"Recording {recording_id} not found")
            return
        
        # Delete from blob storage
        if recording.get("blob_url"):
            try:
                interview_id = recording["interview_id"]
                format_type = recording["format_type"]
                blob_name = f"{interview_id}/{recording_id}.{format_type.value}"
                
                container_client = self.blob_client.get_container_client(
                    settings.RECORDING_CONTAINER
                )
                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.delete_blob()
            except Exception as e:
                logger.error(f"Failed to delete blob for recording {recording_id}: {e}")
        
        # Remove from cache
        del self._recordings[recording_id]
        
        logger.info(f"Recording {recording_id} deleted")
    
    async def get_interview_recordings(self, interview_id: str) -> List[Dict[str, Any]]:
        """Get all recordings for an interview"""
        return [
            r for r in self._recordings.values()
            if r.get("interview_id") == interview_id
        ]


# Singleton instance
recording_service = RecordingService()
