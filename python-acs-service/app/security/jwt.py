"""JWT helper utilities."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.config import settings


def _base64url_encode(data: bytes) -> str:
    """Encode bytes using base64url without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    """Decode base64url string with padding."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: str, secret: str) -> str:
    """Create an HMAC SHA256 signature for a message."""
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return _base64url_encode(signature)


def create_token(payload: Dict[str, Any], expires_minutes: int | None = None) -> str:
    """Create a signed JWT for the given payload."""
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload_copy = payload.copy()

    ttl = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES
    payload_copy["exp"] = int((datetime.now(timezone.utc) + timedelta(minutes=ttl)).timestamp())

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload_copy, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}"
    signature = _sign(signing_input, settings.JWT_SECRET)
    return f"{signing_input}.{signature}"


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT and return the decoded payload."""
    try:
        header_b64, payload_b64, signature = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    signing_input = f"{header_b64}.{payload_b64}"
    expected_signature = _sign(signing_input, settings.JWT_SECRET)
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid token signature")

    payload_json = _base64url_decode(payload_b64)
    payload = json.loads(payload_json)

    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Token missing expiration")
    if datetime.now(timezone.utc).timestamp() > exp:
        raise ValueError("Token expired")

    return payload


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against the stored hash."""
    return hmac.compare_digest(hash_password(password), password_hash)
