from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


def json_text_dumps(payload: Any) -> str | None:
    if payload is None:
        return None
    return json.dumps(
        payload,
        default=_json_text_default,
        separators=(",", ":"),
        sort_keys=True,
    )


def json_text_loads(payload: str | None, default: Any = None) -> Any:
    if payload is None or payload == "":
        return default
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return default


def _json_text_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
