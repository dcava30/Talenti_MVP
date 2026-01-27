"""Azure client helpers."""
from azure.communication.identity import CommunicationIdentityClient

from app.config import settings


def get_acs_identity_client() -> CommunicationIdentityClient:
    """Create the ACS identity client."""
    if not settings.ACS_CONNECTION_STRING:
        raise ValueError("ACS_CONNECTION_STRING not configured")
    return CommunicationIdentityClient.from_connection_string(settings.ACS_CONNECTION_STRING)


def get_speech_token_url() -> str:
    """Build the speech token endpoint URL."""
    if not settings.AZURE_SPEECH_REGION:
        raise ValueError("AZURE_SPEECH_REGION not configured")
    return f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"


def get_speech_key() -> str:
    """Return the configured speech key."""
    if not settings.AZURE_SPEECH_KEY:
        raise ValueError("AZURE_SPEECH_KEY not configured")
    return settings.AZURE_SPEECH_KEY
