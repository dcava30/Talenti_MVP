"""
Organisation Environment Setup — Questionnaire and Answer-to-Variable Translation

This module implements the deterministic rubric that converts 10 structured
organisation questionnaire answers into the 6 operating environment variables
used by the scoring engine.

Design principles
-----------------
- All mapping is deterministic. Given the same answers, the same environment
  variables are always produced.
- UNKNOWN / NOT_INFERRED values are treated as null — they do not contribute
  to variable derivation.
- Lineage is preserved: the translation result carries which answers produced
  which variable values.
- The 10 questions are grouped into 5 dimension areas (2 questions per area).
  Each answer maps to one or two environment variables via the rubric table.

Question groups
---------------
  Q1–Q2 : Proactivity / Ownership    → control_vs_autonomy, high_performance_archetype
  Q3–Q4 : Drive / Execution          → outcome_vs_process, decision_reality
  Q5–Q6 : Collaboration / Challenge  → conflict_style
  Q7–Q8 : Adaptability / Ambiguity   → ambiguity_load
  Q9–Q10: Coachability / Feedback    → (feedback culture maps into archetype + fatal_risks)

Variable outputs
----------------
  control_vs_autonomy     : execution_led | guided_ownership | full_ownership
  outcome_vs_process      : results_first | balanced | process_led
  conflict_style          : alignment_focused | healthy_debate | challenge_expected
  decision_reality        : evidence_led | speed_led | judgement_led
  ambiguity_load          : well_defined | evolving | ambiguous
  high_performance_archetype: reliable_executor | strong_owner | directional_driver
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

# ---------------------------------------------------------------------------
# Question definitions — constrained answer choices
# ---------------------------------------------------------------------------

QUESTION_CHOICES: Dict[str, List[str]] = {
    # ── PROACTIVITY / OWNERSHIP ──────────────────────────────────────────
    "q1_direction_style": [
        "we_tell_people_exactly_what_to_do",   # execution_led
        "we_set_goals_and_guide_the_how",      # guided_ownership
        "we_set_direction_and_people_own_it",  # full_ownership
    ],
    "q2_success_archetype": [
        "reliable_follows_process_delivers_consistently",   # reliable_executor
        "owns_outcomes_balances_action_and_reflection",     # strong_owner
        "sets_direction_challenges_status_quo_drives_change", # directional_driver
    ],
    # ── DRIVE / EXECUTION ────────────────────────────────────────────────
    "q3_what_matters_most": [
        "hitting_the_numbers_outcomes_above_all",   # results_first
        "good_process_and_good_outcomes",            # balanced
        "following_the_right_process_consistently", # process_led
    ],
    "q4_decision_style": [
        "we_move_fast_decide_with_70pct_info",      # speed_led
        "we_weigh_evidence_before_deciding",        # evidence_led
        "senior_people_make_the_calls",             # judgement_led
    ],
    # ── COLLABORATION / CHALLENGE ────────────────────────────────────────
    "q5_conflict_tolerance": [
        "we_align_first_avoid_open_conflict",       # alignment_focused
        "we_debate_ideas_respectfully",             # healthy_debate
        "we_expect_people_to_challenge_directly",  # challenge_expected
    ],
    "q6_bad_decision_response": [
        "raise_concern_privately_then_align",       # alignment_focused (secondary)
        "voice_disagreement_constructively",        # healthy_debate (secondary)
        "push_back_hard_and_change_the_outcome",    # challenge_expected (secondary)
    ],
    # ── ADAPTABILITY / AMBIGUITY ─────────────────────────────────────────
    "q7_role_clarity": [
        "roles_are_clearly_defined_with_process",   # well_defined
        "roles_evolve_with_business_needs",         # evolving
        "people_define_their_own_scope",            # ambiguous
    ],
    "q8_handles_change": [
        "we_plan_carefully_and_follow_the_plan",    # well_defined (secondary)
        "we_adapt_as_we_learn",                     # evolving (secondary)
        "we_thrive_in_chaos_and_figure_it_out",     # ambiguous (secondary)
    ],
    # ── COACHABILITY / FEEDBACK ──────────────────────────────────────────
    "q9_feedback_culture": [
        "feedback_is_formal_review_cycle_only",     # low feedback culture → process_led tweak
        "feedback_is_given_informally_when_needed", # balanced feedback
        "feedback_is_continuous_and_expected",      # high feedback → adjusts archetype
    ],
    "q10_growth_expectation": [
        "people_are_expected_to_grow_on_their_own",         # low coaching expectation
        "managers_coach_and_people_are_expected_to_improve", # balanced
        "coachability_is_a_hard_requirement_not_optional",   # high → adds to fatal_risks
    ],
}

# Human-readable question labels (for UI rendering)
QUESTION_LABELS: Dict[str, str] = {
    "q1_direction_style": "How much direction do you give people in this role?",
    "q2_success_archetype": "Which best describes the person who succeeds here?",
    "q3_what_matters_most": "What matters most in how work gets done?",
    "q4_decision_style": "How are decisions typically made?",
    "q5_conflict_tolerance": "How does the team handle disagreement?",
    "q6_bad_decision_response": "When someone sees a bad decision being made, what do you expect?",
    "q7_role_clarity": "How clearly defined are roles and responsibilities?",
    "q8_handles_change": "How does the organisation typically respond to change?",
    "q9_feedback_culture": "How is feedback typically given here?",
    "q10_growth_expectation": "What is your expectation around personal growth and coachability?",
}


# ---------------------------------------------------------------------------
# Rubric table — maps each answer to one or two variable signals
#
# Format: answer_value → List of (variable_name, variable_value, weight)
# weight: 1 = primary mapping, 0.5 = secondary mapping
# ---------------------------------------------------------------------------

_RUBRIC: Dict[str, List[Tuple[str, str, float]]] = {
    # q1 → control_vs_autonomy
    "we_tell_people_exactly_what_to_do":
        [("control_vs_autonomy", "execution_led", 1.0)],
    "we_set_goals_and_guide_the_how":
        [("control_vs_autonomy", "guided_ownership", 1.0)],
    "we_set_direction_and_people_own_it":
        [("control_vs_autonomy", "full_ownership", 1.0)],

    # q2 → high_performance_archetype
    "reliable_follows_process_delivers_consistently":
        [("high_performance_archetype", "reliable_executor", 1.0)],
    "owns_outcomes_balances_action_and_reflection":
        [("high_performance_archetype", "strong_owner", 1.0)],
    "sets_direction_challenges_status_quo_drives_change":
        [("high_performance_archetype", "directional_driver", 1.0)],

    # q3 → outcome_vs_process
    "hitting_the_numbers_outcomes_above_all":
        [("outcome_vs_process", "results_first", 1.0)],
    "good_process_and_good_outcomes":
        [("outcome_vs_process", "balanced", 1.0)],
    "following_the_right_process_consistently":
        [("outcome_vs_process", "process_led", 1.0)],

    # q4 → decision_reality
    "we_move_fast_decide_with_70pct_info":
        [("decision_reality", "speed_led", 1.0)],
    "we_weigh_evidence_before_deciding":
        [("decision_reality", "evidence_led", 1.0)],
    "senior_people_make_the_calls":
        [("decision_reality", "judgement_led", 1.0)],

    # q5 → conflict_style (primary)
    "we_align_first_avoid_open_conflict":
        [("conflict_style", "alignment_focused", 1.0)],
    "we_debate_ideas_respectfully":
        [("conflict_style", "healthy_debate", 1.0)],
    "we_expect_people_to_challenge_directly":
        [("conflict_style", "challenge_expected", 1.0)],

    # q6 → conflict_style (secondary — reinforces or softens q5 signal)
    "raise_concern_privately_then_align":
        [("conflict_style", "alignment_focused", 0.5)],
    "voice_disagreement_constructively":
        [("conflict_style", "healthy_debate", 0.5)],
    "push_back_hard_and_change_the_outcome":
        [("conflict_style", "challenge_expected", 0.5)],

    # q7 → ambiguity_load (primary)
    "roles_are_clearly_defined_with_process":
        [("ambiguity_load", "well_defined", 1.0)],
    "roles_evolve_with_business_needs":
        [("ambiguity_load", "evolving", 1.0)],
    "people_define_their_own_scope":
        [("ambiguity_load", "ambiguous", 1.0)],

    # q8 → ambiguity_load (secondary)
    "we_plan_carefully_and_follow_the_plan":
        [("ambiguity_load", "well_defined", 0.5)],
    "we_adapt_as_we_learn":
        [("ambiguity_load", "evolving", 0.5)],
    "we_thrive_in_chaos_and_figure_it_out":
        [("ambiguity_load", "ambiguous", 0.5)],

    # q9 → feedback culture influences outcome_vs_process and archetype
    "feedback_is_formal_review_cycle_only":
        [("outcome_vs_process", "process_led", 0.5)],
    "feedback_is_given_informally_when_needed":
        [],  # neutral — no adjustment
    "feedback_is_continuous_and_expected":
        [("high_performance_archetype", "strong_owner", 0.5)],
        # Continuous feedback culture aligns with strong_owner archetype;
        # if archetype is already directional_driver, this acts as softener

    # q10 → coachability expectation — influences fatal_risks
    # (handled specially below in translate_answers_to_environment)
    "people_are_expected_to_grow_on_their_own":
        [],  # no fatal risk
    "managers_coach_and_people_are_expected_to_improve":
        [],  # no fatal risk
    "coachability_is_a_hard_requirement_not_optional":
        [],  # adds feedback_defensive_or_dismissive to fatal_risks (handled in code)
}

# Variable resolution order: when a variable receives multiple signals (primary +
# secondary), the highest-weight signal wins. Ties broken by primary > secondary.
_VARIABLE_PRIORITY_ORDER = [
    "control_vs_autonomy",
    "outcome_vs_process",
    "conflict_style",
    "decision_reality",
    "ambiguity_load",
    "high_performance_archetype",
]

# The valid value set for each variable (used for validation)
_VARIABLE_VALID_VALUES: Dict[str, List[str]] = {
    "control_vs_autonomy": ["execution_led", "guided_ownership", "full_ownership"],
    "outcome_vs_process": ["results_first", "balanced", "process_led"],
    "conflict_style": ["alignment_focused", "healthy_debate", "challenge_expected"],
    "decision_reality": ["evidence_led", "speed_led", "judgement_led"],
    "ambiguity_load": ["well_defined", "evolving", "ambiguous"],
    "high_performance_archetype": ["reliable_executor", "strong_owner", "directional_driver"],
}

# Default values used when a variable receives no signal from answers
_VARIABLE_DEFAULTS: Dict[str, str] = {
    "control_vs_autonomy": "guided_ownership",
    "outcome_vs_process": "balanced",
    "conflict_style": "healthy_debate",
    "decision_reality": "evidence_led",
    "ambiguity_load": "evolving",
    "high_performance_archetype": "strong_owner",
}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VariableSignal:
    """A single mapping from one answer to one variable value."""
    question_id: str
    answer: str
    variable: str
    derived_value: str
    weight: float  # 1.0 = primary, 0.5 = secondary


@dataclass
class TranslationResult:
    """
    Full output of the answer-to-variable translation.
    Carries derived variable values, lineage, and any fatal risk additions.
    """
    # Final resolved environment variable values
    environment: Dict[str, str]

    # Lineage: which answers contributed to each variable
    signals: List[VariableSignal]

    # Variables that received no signal → used default
    defaulted_variables: List[str]

    # Additional fatal risk signal IDs added by q10
    extra_fatal_risks: List[str]

    # Raw answer snapshot (for audit persistence)
    raw_answers: Dict[str, str]


# ---------------------------------------------------------------------------
# Translation engine
# ---------------------------------------------------------------------------

def translate_answers_to_environment(answers: Dict[str, str]) -> TranslationResult:
    """
    Deterministically convert org questionnaire answers to operating environment
    variables.

    Parameters
    ----------
    answers : dict
        Mapping of question_id → answer_value.
        Unknown question IDs are ignored.
        Invalid answer values are treated as null (NOT_INFERRED).

    Returns
    -------
    TranslationResult
        Contains resolved environment variables, full signal lineage,
        defaulted variable list, and any extra fatal risk signal IDs.
    """
    # Collect raw signals per variable: variable → List[(value, weight, question_id, answer)]
    variable_candidates: Dict[str, List[Tuple[str, float, str, str]]] = {
        v: [] for v in _VARIABLE_PRIORITY_ORDER
    }
    signals: List[VariableSignal] = []
    extra_fatal_risks: List[str] = []

    for question_id, answer in answers.items():
        if question_id not in QUESTION_CHOICES:
            continue  # Unknown question — ignore
        if answer not in QUESTION_CHOICES[question_id]:
            continue  # Invalid answer — treat as null / NOT_INFERRED

        mappings = _RUBRIC.get(answer, [])
        for variable, value, weight in mappings:
            variable_candidates[variable].append((value, weight, question_id, answer))
            signals.append(VariableSignal(
                question_id=question_id,
                answer=answer,
                variable=variable,
                derived_value=value,
                weight=weight,
            ))

    # Special handling: q10 "coachability_is_a_hard_requirement" → add fatal risk
    q10_answer = answers.get("q10_growth_expectation", "")
    if q10_answer == "coachability_is_a_hard_requirement_not_optional":
        extra_fatal_risks.append("feedback_defensive_or_dismissive")

    # Resolve each variable: highest weight wins; ties go to primary (1.0 > 0.5)
    environment: Dict[str, str] = {}
    defaulted_variables: List[str] = []

    for variable in _VARIABLE_PRIORITY_ORDER:
        candidates = variable_candidates[variable]
        if not candidates:
            # No signal — use safe default, flag as defaulted
            environment[variable] = _VARIABLE_DEFAULTS[variable]
            defaulted_variables.append(variable)
        else:
            # Sort: primary signals (weight=1.0) before secondary (weight=0.5)
            # Within same weight: last answer in iteration order wins (stable)
            candidates_sorted = sorted(candidates, key=lambda x: x[1], reverse=True)
            winning_value = candidates_sorted[0][0]
            environment[variable] = winning_value

    return TranslationResult(
        environment=environment,
        signals=signals,
        defaulted_variables=defaulted_variables,
        extra_fatal_risks=extra_fatal_risks,
        raw_answers={k: v for k, v in answers.items() if k in QUESTION_CHOICES},
    )


def build_values_framework_from_translation(
    translation: TranslationResult,
    taxonomy: Optional[Dict] = None,
    dimension_weights: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Build a complete values_framework dict from a TranslationResult.
    This is the format stored in Organisation.values_framework.

    Parameters
    ----------
    translation : TranslationResult
    taxonomy : dict, optional
        Custom taxonomy to include. Defaults to canonical taxonomy from
        talenti_dimensions (imported lazily to avoid circular imports in backend).
    dimension_weights : dict, optional
        Per-dimension scoring weights. Defaults to canonical defaults.
    """
    from app.api.orgs import _default_values_framework  # lazy import

    defaults = _default_values_framework()
    canonical_taxonomy = defaults["taxonomy"]
    canonical_weights = defaults["operating_environment"]["dimension_weights"]

    env = dict(translation.environment)
    env["dimension_weights"] = dimension_weights or canonical_weights
    env["fatal_risks"] = translation.extra_fatal_risks
    env["coachable_risks"] = []

    return {
        "operating_environment": env,
        "taxonomy": taxonomy or canonical_taxonomy,
    }
