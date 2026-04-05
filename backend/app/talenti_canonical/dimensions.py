"""
Canonical dimension names, default weights, and environment variable definitions.

These constants are shared between the backend and both model services.
The model services carry their own copy in talenti_dimensions.py; this file
is the authoritative backend reference.
"""
from __future__ import annotations

from typing import Dict, List

# ── Canonical dimension names ──────────────────────────────────────────────────
#
# Order is meaningful: it determines the order in which dimensions appear in
# API responses, DB rows, and report outputs.

CANONICAL_DIMENSIONS: List[str] = [
    "ownership",   # Takes accountability, drives outcomes, doesn't wait to be told
    "execution",   # Delivers reliably under pressure; pace, focus, follow-through
    "challenge",   # Comfortable with healthy conflict; pushes back, names problems
    "ambiguity",   # Operates effectively without complete information or structure
    "feedback",    # Actively seeks, receives, and acts on feedback; coachable
]

# ── Default scoring weights ────────────────────────────────────────────────────
#
# Used when no env-specific weights are available.
# Must sum to 1.0.

DEFAULT_DIMENSION_WEIGHTS: Dict[str, float] = {
    "ownership": 0.25,
    "execution": 0.25,
    "challenge": 0.20,
    "ambiguity": 0.15,
    "feedback":  0.15,
}

# ── Operating environment variable names ──────────────────────────────────────
#
# The 6 variables produced by the org questionnaire translation engine.
# See app/services/org_environment.py for the spec-alignment note explaining
# the mapping from the original 5-variable product spec.

ENV_VARIABLE_NAMES: List[str] = [
    "control_vs_autonomy",
    "outcome_vs_process",
    "conflict_style",
    "decision_reality",
    "ambiguity_load",
    "high_performance_archetype",
]

ENV_VARIABLE_VALUES: Dict[str, List[str]] = {
    "control_vs_autonomy": [
        "execution_led",
        "guided_ownership",
        "full_ownership",
    ],
    "outcome_vs_process": [
        "results_first",
        "balanced",
        "process_led",
    ],
    "conflict_style": [
        "alignment_focused",
        "healthy_debate",
        "challenge_expected",
    ],
    "decision_reality": [
        "evidence_led",
        "speed_led",
        "judgement_led",
    ],
    "ambiguity_load": [
        "well_defined",
        "evolving",
        "ambiguous",
    ],
    "high_performance_archetype": [
        "reliable_executor",
        "strong_owner",
        "directional_driver",
    ],
}
