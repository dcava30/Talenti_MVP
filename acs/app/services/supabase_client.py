"""
Supabase client service for database operations
"""
from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """
    Service for Supabase database operations
    """
    
    def __init__(self):
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """Lazy initialization of the Supabase client"""
        if self._client is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
                raise ValueError("Supabase configuration not set")
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        return self._client
    
    async def get_interview(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """
        Get interview by ID
        """
        try:
            result = self.client.table("interviews").select("*").eq("id", interview_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get interview {interview_id}: {e}")
            return None
    
    async def update_interview(
        self,
        interview_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update interview record
        """
        try:
            # Merge updates into metadata if needed
            metadata_updates = {}
            regular_updates = {}
            
            for key, value in updates.items():
                if key in ["recording_started", "recording_id", "recording_processed"]:
                    metadata_updates[key] = value
                else:
                    regular_updates[key] = value
            
            if metadata_updates:
                # Get current metadata and merge
                interview = await self.get_interview(interview_id)
                if interview:
                    current_metadata = interview.get("metadata") or {}
                    current_metadata.update(metadata_updates)
                    regular_updates["metadata"] = current_metadata
            
            if regular_updates:
                self.client.table("interviews").update(regular_updates).eq("id", interview_id).execute()
            
            logger.info(f"Updated interview {interview_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update interview {interview_id}: {e}")
            return False
    
    async def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        """
        Get application by ID
        """
        try:
            result = self.client.table("applications").select("*, job_roles(*)").eq("id", application_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get application {application_id}: {e}")
            return None
    
    async def get_job_role(self, job_role_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job role by ID
        """
        try:
            result = self.client.table("job_roles").select("*, organisations(*)").eq("id", job_role_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get job role {job_role_id}: {e}")
            return None
    
    async def save_transcript_segment(
        self,
        interview_id: str,
        speaker: str,
        content: str,
        start_time_ms: int,
        end_time_ms: Optional[int] = None,
        confidence: Optional[float] = None
    ) -> bool:
        """
        Save a transcript segment
        """
        try:
            self.client.table("transcript_segments").insert({
                "interview_id": interview_id,
                "speaker": speaker,
                "content": content,
                "start_time_ms": start_time_ms,
                "end_time_ms": end_time_ms,
                "confidence": confidence
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to save transcript segment: {e}")
            return False
    
    async def get_transcript(self, interview_id: str) -> List[Dict[str, Any]]:
        """
        Get full transcript for an interview
        """
        try:
            result = self.client.table("transcript_segments").select("*").eq("interview_id", interview_id).order("start_time_ms").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get transcript for interview {interview_id}: {e}")
            return []
    
    async def log_audit_event(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        organisation_id: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None
    ) -> bool:
        """
        Log an audit event
        """
        try:
            self.client.table("audit_log").insert({
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "organisation_id": organisation_id,
                "old_values": old_values,
                "new_values": new_values
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False


# Singleton instance
supabase_service = SupabaseService()
