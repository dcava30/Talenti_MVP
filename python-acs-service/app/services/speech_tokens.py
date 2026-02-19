"""Speech token service."""
from datetime import datetime, timedelta, timezone
from typing import Dict

import httpx

from app.services.azure_clients import get_speech_key, get_speech_token_url


def generate_speech_token() -> Dict[str, str]:
    """Generate a speech token via the Azure Speech REST endpoint."""
    try:
        endpoint = get_speech_token_url()
        key = get_speech_key()
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc

    headers = {"Ocp-Apim-Subscription-Key": key}

    try:
        response = httpx.post(endpoint, headers=headers, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to request speech token: {exc}") from exc

    return {
        "token": response.text,
        "expires_on": (datetime.now(timezone.utc) + timedelta(minutes=9)).isoformat(),
    }
