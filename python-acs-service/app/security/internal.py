from fastapi import Header, HTTPException, status

from app.config import settings


def require_internal_shared_secret(
    x_acs_worker_secret: str | None = Header(default=None),
) -> None:
    if not settings.ACS_WORKER_SHARED_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACS_WORKER_SHARED_SECRET not configured",
        )
    if x_acs_worker_secret != settings.ACS_WORKER_SHARED_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid worker secret")
