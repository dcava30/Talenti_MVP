import httpx

from app.core.config import settings


class AcsWorkerError(Exception):
    pass


def _worker_headers() -> dict[str, str]:
    if not settings.acs_worker_shared_secret:
        raise AcsWorkerError("ACS_WORKER_SHARED_SECRET not configured")
    return {"X-ACS-Worker-Secret": settings.acs_worker_shared_secret}


def _worker_url(path: str) -> str:
    if not settings.acs_worker_url:
        raise AcsWorkerError("ACS_WORKER_URL not configured")
    return f"{settings.acs_worker_url.rstrip('/')}{path}"


async def create_call(
    *,
    interview_id: str,
    target_identity: str,
    source_identity: str | None,
    callback_url: str,
) -> dict:
    payload = {
        "interview_id": interview_id,
        "target_identity": target_identity,
        "source_identity": source_identity,
        "callback_url": callback_url,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            _worker_url("/internal/calls/create"),
            headers=_worker_headers(),
            json=payload,
        )
    if response.status_code >= 400:
        raise AcsWorkerError(f"Acs worker create_call failed: {response.status_code} {response.text}")
    return response.json()


async def hangup_call(call_connection_id: str) -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            _worker_url(f"/internal/calls/{call_connection_id}/hangup"),
            headers=_worker_headers(),
            json={"for_everyone": True},
        )
    if response.status_code >= 400:
        raise AcsWorkerError(f"Acs worker hangup_call failed: {response.status_code} {response.text}")


async def start_recording(
    *,
    interview_id: str,
    server_call_id: str,
    content_type: str,
    channel_type: str,
    format_type: str,
) -> dict:
    payload = {
        "interview_id": interview_id,
        "server_call_id": server_call_id,
        "content_type": content_type,
        "channel_type": channel_type,
        "format_type": format_type,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            _worker_url("/internal/recordings/start"),
            headers=_worker_headers(),
            json=payload,
        )
    if response.status_code >= 400:
        raise AcsWorkerError(
            f"Acs worker start_recording failed: {response.status_code} {response.text}"
        )
    return response.json()


async def stop_recording(recording_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            _worker_url(f"/internal/recordings/{recording_id}/stop"),
            headers=_worker_headers(),
        )
    if response.status_code >= 400:
        raise AcsWorkerError(
            f"Acs worker stop_recording failed: {response.status_code} {response.text}"
        )
    return response.json()
