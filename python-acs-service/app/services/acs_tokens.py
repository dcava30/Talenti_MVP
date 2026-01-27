"""ACS token service."""
from typing import Dict

from azure.core.exceptions import AzureError

from app.services.azure_clients import get_acs_identity_client


def generate_acs_token() -> Dict[str, str]:
    """Generate an ACS access token with a new identity."""
    try:
        client = get_acs_identity_client()
        identity = client.create_user()
        token = client.get_token(identity, ["voip"])  # type: ignore[arg-type]
    except (ValueError, AzureError) as exc:
        raise RuntimeError(f"Failed to generate ACS token: {exc}") from exc

    return {
        "token": token.token,
        "expires_on": token.expires_on.isoformat(),
    }
