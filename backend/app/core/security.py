from datetime import datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    claims = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_access_ttl_minutes),
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(subject: str) -> str:
    claims = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_refresh_ttl_minutes),
        "type": "refresh",
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
