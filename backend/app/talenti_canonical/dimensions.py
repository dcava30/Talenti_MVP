"""
Canonical dimensions and deterministic environment rules shared by the backend.

The backend owns the tracked copy of the canonical dimension names, default
weights, environment value enums, and the rule helpers used to turn an
operating environment into per-dimension score requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

CANONICAL_DIMENSIONS: List[str] = [
    "ownership",
    "execution",
    "challenge",
    "ambiguity",
    "feedback",
]

DimensionName = Literal["ownership", "execution", "challenge", "ambiguity", "feedback"]

DEFAULT_DIMENSION_WEIGHTS: Dict[str, float] = {
    "ownership": 0.25,
    "execution": 0.25,
    "challenge": 0.20,
    "ambiguity": 0.15,
    "feedback": 0.15,
}

ENV_VARIABLE_NAMES: List[str] = [
    "control_vs_autonomy",
    "outcome_vs_process",
    "conflict_style",
    "decision_reality",
    "ambiguity_load",
    "high_performance_archetype",
]

ENV_VARIABLE_VALUES: Dict[str, List[str]] = {
    "control_vs_autonomy": ["execution_led", "guided_ownership", "full_ownership"],
    "outcome_vs_process": ["results_first", "balanced", "process_led"],
    "conflict_style": ["alignment_focused", "healthy_debate", "challenge_expected"],
    "decision_reality": ["evidence_led", "speed_led", "judgement_led"],
    "ambiguity_load": ["well_defined", "evolving", "ambiguous"],
    "high_performance_archetype": [
        "reliable_executor",
        "strong_owner",
        "directional_driver",
    ],
}


@dataclass(frozen=True)
class DimensionRequirement:
    dimension: DimensionName
    pass_threshold: int
    watch_threshold: int
    weight: float = 1.0


Adjustment = Tuple[int, int, float]


@dataclass(frozen=True)
class EnvRule:
    variable: str
    value: str
    adjustments: Dict[str, Adjustment]
    note: str = ""


_BASE_REQUIREMENTS: Dict[str, DimensionRequirement] = {
    "ownership": DimensionRequirement("ownership", pass_threshold=55, watch_threshold=40, weight=1.0),
    "execution": DimensionRequirement("execution", pass_threshold=55, watch_threshold=40, weight=1.0),
    "challenge": DimensionRequirement("challenge", pass_threshold=50, watch_threshold=35, weight=1.0),
    "ambiguity": DimensionRequirement("ambiguity", pass_threshold=50, watch_threshold=35, weight=1.0),
    "feedback": DimensionRequirement("feedback", pass_threshold=50, watch_threshold=35, weight=1.0),
}


_ENV_RULES: List[EnvRule] = [
    EnvRule(
        variable="control_vs_autonomy",
        value="execution_led",
        adjustments={
            "execution": (10, 10, 0.2),
            "ownership": (-5, -5, -0.1),
            "ambiguity": (-10, -10, -0.2),
        },
        note="Execution-led: strong execution required, less autonomy pressure",
    ),
    EnvRule(
        variable="control_vs_autonomy",
        value="guided_ownership",
        adjustments={
            "ownership": (5, 5, 0.1),
            "execution": (5, 5, 0.0),
        },
        note="Guided ownership: moderate ownership uplift",
    ),
    EnvRule(
        variable="control_vs_autonomy",
        value="full_ownership",
        adjustments={
            "ownership": (20, 15, 0.4),
            "ambiguity": (15, 15, 0.3),
            "execution": (5, 5, 0.1),
        },
        note="Full ownership: ownership and ambiguity tolerance heavily weighted",
    ),
    EnvRule(
        variable="outcome_vs_process",
        value="results_first",
        adjustments={
            "execution": (15, 10, 0.3),
            "ownership": (10, 5, 0.1),
        },
        note="Results-first: execution and ownership premium",
    ),
    EnvRule(
        variable="outcome_vs_process",
        value="balanced",
        adjustments={},
        note="Balanced: no adjustment to baseline",
    ),
    EnvRule(
        variable="outcome_vs_process",
        value="process_led",
        adjustments={
            "execution": (-5, -5, -0.1),
            "feedback": (5, 5, 0.1),
        },
        note="Process-led: slightly less execution pressure, more feedback emphasis",
    ),
    EnvRule(
        variable="conflict_style",
        value="alignment_focused",
        adjustments={
            "challenge": (-10, -10, -0.2),
            "feedback": (5, 5, 0.1),
        },
        note="Alignment-focused: lower challenge bar",
    ),
    EnvRule(
        variable="conflict_style",
        value="healthy_debate",
        adjustments={"challenge": (10, 10, 0.1)},
        note="Healthy debate: moderate challenge uplift",
    ),
    EnvRule(
        variable="conflict_style",
        value="challenge_expected",
        adjustments={
            "challenge": (20, 15, 0.3),
            "feedback": (10, 10, 0.1),
        },
        note="Challenge expected: high challenge requirement",
    ),
    EnvRule(
        variable="decision_reality",
        value="evidence_led",
        adjustments={
            "feedback": (10, 5, 0.1),
            "ambiguity": (-5, -5, -0.1),
        },
        note="Evidence-led: feedback premium",
    ),
    EnvRule(
        variable="decision_reality",
        value="speed_led",
        adjustments={
            "execution": (15, 10, 0.2),
            "ambiguity": (10, 10, 0.2),
        },
        note="Speed-led: execution and ambiguity tolerance premium",
    ),
    EnvRule(
        variable="decision_reality",
        value="judgement_led",
        adjustments={
            "ownership": (10, 5, 0.2),
            "ambiguity": (10, 10, 0.1),
        },
        note="Judgement-led: ownership and ambiguity premium",
    ),
    EnvRule(
        variable="ambiguity_load",
        value="well_defined",
        adjustments={
            "ambiguity": (-15, -15, -0.3),
            "execution": (5, 5, 0.1),
        },
        note="Well-defined: lower ambiguity bar, slight execution uplift",
    ),
    EnvRule(
        variable="ambiguity_load",
        value="evolving",
        adjustments={
            "ambiguity": (5, 5, 0.1),
            "feedback": (5, 5, 0.1),
        },
        note="Evolving: moderate ambiguity and feedback uplift",
    ),
    EnvRule(
        variable="ambiguity_load",
        value="ambiguous",
        adjustments={
            "ambiguity": (20, 15, 0.4),
            "ownership": (10, 10, 0.2),
        },
        note="Ambiguous: strong ambiguity and ownership required",
    ),
    EnvRule(
        variable="high_performance_archetype",
        value="reliable_executor",
        adjustments={
            "execution": (10, 10, 0.3),
            "feedback": (5, 5, 0.1),
            "ambiguity": (-10, -10, -0.2),
            "challenge": (-5, -5, -0.1),
        },
        note="Reliable executor: execution and feedback premium",
    ),
    EnvRule(
        variable="high_performance_archetype",
        value="strong_owner",
        adjustments={
            "ownership": (8, 5, 0.15),
            "execution": (5, 5, 0.05),
        },
        note="Strong owner: moderate ownership uplift",
    ),
    EnvRule(
        variable="high_performance_archetype",
        value="directional_driver",
        adjustments={
            "ownership": (15, 10, 0.3),
            "challenge": (15, 10, 0.25),
            "ambiguity": (10, 10, 0.2),
            "execution": (-5, -5, -0.05),
            "feedback": (-5, -5, -0.05),
        },
        note="Directional driver: ownership, challenge, ambiguity premium",
    ),
]


def compute_dimension_requirements(
    operating_environment: Dict[str, str],
) -> Dict[str, DimensionRequirement]:
    pass_thresholds = {dim: req.pass_threshold for dim, req in _BASE_REQUIREMENTS.items()}
    watch_thresholds = {dim: req.watch_threshold for dim, req in _BASE_REQUIREMENTS.items()}
    weights = {dim: req.weight for dim, req in _BASE_REQUIREMENTS.items()}

    for rule in _ENV_RULES:
        if operating_environment.get(rule.variable) != rule.value:
            continue
        for dim, (pass_delta, watch_delta, weight_delta) in rule.adjustments.items():
            if dim not in pass_thresholds:
                continue
            pass_thresholds[dim] += pass_delta
            watch_thresholds[dim] += watch_delta
            weights[dim] += weight_delta

    result: Dict[str, DimensionRequirement] = {}
    for dim in CANONICAL_DIMENSIONS:
        pass_threshold = int(round(max(0.0, min(100.0, pass_thresholds[dim]))))
        watch_threshold = int(
            round(max(0.0, min(float(pass_threshold), watch_thresholds[dim])))
        )
        weight = float(round(max(0.1, min(3.0, weights[dim])), 3))
        result[dim] = DimensionRequirement(
            dimension=dim,  # type: ignore[arg-type]
            pass_threshold=pass_threshold,
            watch_threshold=watch_threshold,
            weight=weight,
        )
    return result


ARCHETYPE_FATAL_RISKS: Dict[str, List[str]] = {
    "reliable_executor": [
        "ownership_blame_shifting",
        "execution_procrastination_or_drift",
    ],
    "strong_owner": [
        "ownership_blame_shifting",
        "feedback_defensive_or_dismissive",
    ],
    "directional_driver": [
        "challenge_conflict_avoidance",
        "ambiguity_needs_clarity_to_proceed",
        "ownership_blame_shifting",
    ],
}


def get_archetype_fatal_risks(archetype: str) -> List[str]:
    return list(ARCHETYPE_FATAL_RISKS.get(archetype, []))


__all__ = [
    "ARCHETYPE_FATAL_RISKS",
    "CANONICAL_DIMENSIONS",
    "DEFAULT_DIMENSION_WEIGHTS",
    "DimensionRequirement",
    "ENV_VARIABLE_NAMES",
    "ENV_VARIABLE_VALUES",
    "compute_dimension_requirements",
    "get_archetype_fatal_risks",
]
