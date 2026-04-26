from __future__ import annotations

import json
from typing import Any

TDS_FLAG_NAMES = (
    "TDS_DECISION_SHADOW_WRITE_ENABLED",
    "TDS_DECISION_INSPECTION_API_ENABLED",
    "TDS_SKILLS_SUMMARY_SHADOW_WRITE_ENABLED",
    "TDS_SKILLS_SUMMARY_INSPECTION_API_ENABLED",
    "TDS_SHADOW_COMPARISON_API_ENABLED",
    "TDS_RANKING_AND_SHORTLIST_QUARANTINE_ENABLED",
    "TDS_RECRUITER_DECISION_API_ENABLED",
    "TDS_RECRUITER_SKILLS_SUMMARY_API_ENABLED",
    "TDS_HUMAN_REVIEW_API_ENABLED",
)

SKILLS_LEAKAGE_FIELDS = {
    "skills_score",
    "skills_outcome",
    "skills_summary_id",
    "skills_assessment_summary",
}

DECISION_LEAKAGE_FIELDS = {
    "decision_id",
    "decision_mode",
    "decision_state",
    "decision_valid",
    "confidence_gate_passed",
    "integrity_status",
    "risk_stack",
    "audit_trace",
    "audit_trail_summary",
    "rationale",
}

RANKING_LEAKAGE_FIELDS = {
    "best_candidate",
    "best_candidate_id",
    "match_score",
    "overall_score",
    "rank",
    "ranking",
    "shortlist_position",
}

OVERRIDE_LANGUAGE = {
    "override_ai",
    "override_recommendation",
    "override_score",
    "final_decision_override",
}

LEGACY_HIRING_OUTCOME_LANGUAGE = {"PASS", "REVIEW", "FAIL"}


def collect_keys_and_strings(value: Any) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    strings: list[str] = []

    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            nested_keys, nested_strings = collect_keys_and_strings(nested)
            keys.update(nested_keys)
            strings.extend(nested_strings)
        return keys, strings

    if isinstance(value, list):
        for nested in value:
            nested_keys, nested_strings = collect_keys_and_strings(nested)
            keys.update(nested_keys)
            strings.extend(nested_strings)
        return keys, strings

    if isinstance(value, str):
        strings.append(value)

    return keys, strings


def assert_payload_excludes_keys(payload: Any, forbidden_keys: set[str]) -> None:
    keys, _ = collect_keys_and_strings(payload)
    assert forbidden_keys.isdisjoint(keys)


def assert_payload_excludes_strings(payload: Any, forbidden_strings: set[str]) -> None:
    _, strings = collect_keys_and_strings(payload)
    assert forbidden_strings.isdisjoint(set(strings))


def assert_payload_excludes_serialized_terms(payload: Any, forbidden_terms: set[str]) -> None:
    serialized = json.dumps(payload)
    for term in forbidden_terms:
        assert term not in serialized
