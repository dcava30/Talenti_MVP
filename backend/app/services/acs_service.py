from azure.communication.identity import CommunicationIdentityClient

from app.core.config import settings


def get_acs_client() -> CommunicationIdentityClient:
    return CommunicationIdentityClient.from_connection_string(settings.azure_acs_connection_string)
