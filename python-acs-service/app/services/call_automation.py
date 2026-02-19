"""
Azure Communication Services Call Automation Service
"""
from typing import Optional, Dict, Any, Tuple
import logging
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


def _load_acs_clients() -> Tuple[Any, Any, Any, Any, Any, Any]:
    """Load ACS client classes lazily to avoid import-time failures."""
    from azure.communication.callautomation import (  # noqa: WPS433
        CallAutomationClient,
        CallInvite,
        CommunicationUserIdentifier,
        PhoneNumberIdentifier,
        TextSource,
        FileSource,
    )
    from azure.communication.callautomation.aio import (  # noqa: WPS433
        CallAutomationClient as AsyncCallAutomationClient,
    )

    return (
        CallAutomationClient,
        CallInvite,
        CommunicationUserIdentifier,
        PhoneNumberIdentifier,
        TextSource,
        FileSource,
        AsyncCallAutomationClient,
    )


class CallAutomationService:
    """
    Service for managing ACS Call Automation operations
    """
    
    def __init__(self):
        self._client: Optional[Any] = None
    
    @property
    def client(self) -> Any:
        """Lazy initialization of the ACS client."""
        if self._client is None:
            _, _, _, _, _, _, async_client = _load_acs_clients()
            if not settings.ACS_CONNECTION_STRING:
                raise ValueError("ACS_CONNECTION_STRING not configured")
            self._client = async_client.from_connection_string(
                settings.ACS_CONNECTION_STRING
            )
        return self._client
    
    def _parse_identity(self, identity: str):
        """Parse identity string to appropriate identifier type"""
        _, _, communication_user, phone_number, _, _, _ = _load_acs_clients()
        if identity.startswith("+"):
            return phone_number(identity)
        return communication_user(identity)
    
    async def create_call(
        self,
        interview_id: str,
        target_identity: str,
        source_identity: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create an outbound call
        """
        correlation_id = str(uuid.uuid4())
        callback = callback_url or settings.ACS_CALLBACK_URL
        
        target = self._parse_identity(target_identity)
        _, call_invite_class, _, phone_number, _, _, _ = _load_acs_clients()
        call_invite = call_invite_class(target=target)
        
        if source_identity:
            call_invite.source_caller_id_number = phone_number(source_identity)
        
        logger.info(f"Creating call to {target_identity} for interview {interview_id}")
        
        result = await self.client.create_call(
            target_participant=call_invite,
            callback_url=f"{callback}?interview_id={interview_id}",
            operation_context=interview_id,
            cognitive_services_endpoint=None  # Optional: for speech services
        )
        
        return {
            "call_connection_id": result.call_connection_id,
            "server_call_id": result.call_connection_properties.server_call_id,
            "correlation_id": correlation_id
        }
    
    async def get_call(self, call_connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an active call
        """
        try:
            call_connection = self.client.get_call_connection(call_connection_id)
            properties = await call_connection.get_call_properties()
            
            return {
                "call_connection_id": call_connection_id,
                "server_call_id": properties.server_call_id,
                "correlation_id": properties.correlation_id,
                "call_state": properties.call_connection_state.value,
                "source": str(properties.source) if properties.source else None,
                "targets": [str(t) for t in properties.targets] if properties.targets else [],
            }
        except Exception as e:
            logger.error(f"Failed to get call {call_connection_id}: {e}")
            return None
    
    async def answer_call(
        self,
        incoming_call_context: str,
        callback_url: Optional[str] = None
    ) -> str:
        """
        Answer an incoming call
        """
        callback = callback_url or settings.ACS_CALLBACK_URL
        
        result = await self.client.answer_call(
            incoming_call_context=incoming_call_context,
            callback_url=callback
        )
        
        return result.call_connection_id
    
    async def hangup_call(
        self,
        call_connection_id: str,
        for_everyone: bool = True
    ) -> None:
        """
        End a call
        """
        call_connection = self.client.get_call_connection(call_connection_id)
        
        if for_everyone:
            await call_connection.hang_up(for_everyone=True)
        else:
            await call_connection.hang_up(for_everyone=False)
        
        logger.info(f"Call {call_connection_id} ended")
    
    async def play_audio(
        self,
        call_connection_id: str,
        text: Optional[str] = None,
        audio_url: Optional[str] = None,
        voice_name: str = "en-AU-NatashaNeural",
        loop: bool = False
    ) -> None:
        """
        Play audio to all participants (TTS or file)
        """
        call_connection = self.client.get_call_connection(call_connection_id)
        
        if text:
            _, _, _, _, text_source, file_source, _ = _load_acs_clients()
            play_source = text_source(
                text=text,
                voice_name=voice_name
            )
        elif audio_url:
            _, _, _, _, _, file_source, _ = _load_acs_clients()
            play_source = file_source(url=audio_url)
        else:
            raise ValueError("Either text or audio_url must be provided")
        
        await call_connection.play_media(
            play_source=play_source,
            loop=loop
        )
        
        logger.info(f"Playing audio on call {call_connection_id}")
    
    async def add_participant(
        self,
        call_connection_id: str,
        target_identity: str,
        source_identity: Optional[str] = None
    ) -> str:
        """
        Add a participant to an existing call
        """
        call_connection = self.client.get_call_connection(call_connection_id)
        target = self._parse_identity(target_identity)
        
        _, call_invite_class, _, phone_number, _, _, _ = _load_acs_clients()
        call_invite = call_invite_class(target=target)
        if source_identity:
            call_invite.source_caller_id_number = phone_number(source_identity)
        
        result = await call_connection.add_participant(call_invite)
        
        logger.info(f"Added participant {target_identity} to call {call_connection_id}")
        return str(result.participant.identifier)
    
    async def remove_participant(
        self,
        call_connection_id: str,
        participant_id: str
    ) -> None:
        """
        Remove a participant from a call
        """
        call_connection = self.client.get_call_connection(call_connection_id)
        participant = self._parse_identity(participant_id)
        
        await call_connection.remove_participant(participant)
        
        logger.info(f"Removed participant {participant_id} from call {call_connection_id}")
    
    async def mute_participant(
        self,
        call_connection_id: str,
        participant_id: str
    ) -> None:
        """
        Mute a participant
        """
        call_connection = self.client.get_call_connection(call_connection_id)
        participant = self._parse_identity(participant_id)
        
        await call_connection.mute_participant(participant)
        
        logger.info(f"Muted participant {participant_id} in call {call_connection_id}")


# Singleton instance
call_automation_service = CallAutomationService()
