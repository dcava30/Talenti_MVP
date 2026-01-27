"""Webhook endpoints."""
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/acs")
async def acs_webhook_handler(request: Request) -> dict[str, Any]:
    """Handle ACS webhook events."""
    payload = await request.json()
    return {"status": "received", "events": payload}
