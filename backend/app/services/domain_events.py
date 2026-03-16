import json
from datetime import datetime
from typing import Any

from app.models import DomainEvent


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, default=_json_default)


def json_loads(payload: str | None, default: Any = None) -> Any:
    if not payload:
        return default
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return default


def record_domain_event(
    *,
    db,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> DomainEvent:
    event = DomainEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload_json=json_dumps(payload),
        correlation_id=correlation_id,
    )
    db.add(event)
    return event


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
