from __future__ import annotations

import json
from typing import Any

from app.models import Organisation


class CultureContextError(ValueError):
    pass


def parse_values_framework(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def extract_operating_environment(values: dict[str, Any]) -> dict[str, Any] | None:
    env = values.get("operating_environment") or values.get("team_operating_environment")
    return env if isinstance(env, dict) else None


def extract_taxonomy(values: dict[str, Any]) -> dict[str, Any] | None:
    taxonomy = values.get("taxonomy")
    if isinstance(taxonomy, dict):
        return taxonomy

    taxonomy_id = values.get("taxonomy_id")
    version = values.get("taxonomy_version")
    signals = values.get("signals") or values.get("taxonomy_signals")
    if taxonomy_id and version and isinstance(signals, list):
        return {
            "taxonomy_id": taxonomy_id,
            "version": version,
            "created_utc": values.get("taxonomy_created_utc"),
            "signals": signals,
        }
    return None


def load_org_culture_context(organisation: Organisation) -> tuple[dict[str, Any], dict[str, Any]]:
    values = parse_values_framework(organisation.values_framework)
    if not values:
        raise CultureContextError("Organisation values_framework is missing or invalid JSON.")

    operating_environment = extract_operating_environment(values)
    if not operating_environment:
        raise CultureContextError("Organisation values_framework missing operating_environment.")

    taxonomy = extract_taxonomy(values)
    if not taxonomy:
        raise CultureContextError("Organisation values_framework missing taxonomy.")

    return operating_environment, taxonomy
