"""
CANONICAL_TAXONOMY_V2 — the production signal taxonomy for Talenti scoring.

This is the taxonomy_id="talenti_canonical_v2" taxonomy used by both model
services and seeded into every new Organisation's values_framework.

Signals: 15 total — 3 per canonical dimension.
Version: 2026.2

When updating signals:
  1. Update this file.
  2. Update the _default_values_framework() in backend/app/api/orgs.py to match.
  3. Update the CANONICAL_TAXONOMY dict in model-service-1/talenti_dimensions.py.
  4. Update the CANONICAL_TAXONOMY dict in model-service-2/talenti_dimensions.py.
  5. Bump the version string here and in all three locations above.
"""
from typing import Any, Dict, List

CANONICAL_TAXONOMY_V2: Dict[str, Any] = {
    "taxonomy_id": "talenti_canonical_v2",
    "version": "2026.2",
    "signals": [
        # ── Ownership ──────────────────────────────────────────────────────────
        {
            "signal_id": "ownership_accountability",
            "dimension": "ownership",
            "description": "Takes clear personal accountability for outcomes.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ownership"],
            "evidence_hints": ["I owned", "my decision", "I led", "I drove",
                                "I was responsible", "I took ownership"],
        },
        {
            "signal_id": "ownership_proactivity",
            "dimension": "ownership",
            "description": "Acts without being asked; spots gaps and self-initiates.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ownership"],
            "evidence_hints": ["without being asked", "I noticed", "I proposed", "I started",
                                "I spotted the gap", "I initiated"],
        },
        {
            "signal_id": "ownership_follow_through",
            "dimension": "ownership",
            "description": "Follows through to resolution, not just initiation.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ownership"],
            "evidence_hints": ["I fixed it", "I resolved", "I stepped up", "I handled it",
                                "I took action", "I saw it through"],
        },
        # ── Execution ──────────────────────────────────────────────────────────
        {
            "signal_id": "execution_delivery",
            "dimension": "execution",
            "description": "Delivers reliably; ships things that reach real users.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["execution"],
            "evidence_hints": ["I delivered", "shipped", "launched", "went live",
                                "hit the target", "completed on time", "deployed"],
        },
        {
            "signal_id": "execution_pace_focus",
            "dimension": "execution",
            "description": "Maintains pace and prioritises ruthlessly under pressure.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["execution"],
            "evidence_hints": ["moved quickly", "prioritised", "cut scope", "stayed on track",
                                "fast-paced", "kept moving", "under pressure"],
        },
        {
            "signal_id": "execution_measurable_outcome",
            "dimension": "execution",
            "description": "Cites specific, measurable outcomes — not just activity.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["execution"],
            "evidence_hints": ["measured", "outcome was", "improved by", "reduced",
                                "saved", "increased", "specific metric"],
        },
        # ── Challenge ──────────────────────────────────────────────────────────
        {
            "signal_id": "challenge_constructive_pushback",
            "dimension": "challenge",
            "description": "Names disagreement clearly and constructively.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["challenge"],
            "evidence_hints": ["I disagreed", "I pushed back", "I challenged", "I flagged",
                                "I raised the concern", "I said I wasn't comfortable"],
        },
        {
            "signal_id": "challenge_stakeholder_navigation",
            "dimension": "challenge",
            "description": "Navigates competing interests across stakeholders.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["challenge"],
            "evidence_hints": ["competing priorities", "I aligned", "I facilitated",
                                "conflicting", "I mediated", "different stakeholders"],
        },
        {
            "signal_id": "challenge_problem_naming",
            "dimension": "challenge",
            "description": "Names the real problem, not just the surface issue.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["challenge"],
            "evidence_hints": ["root cause", "identified the issue", "the real issue",
                                "I named", "I called out", "I highlighted"],
        },
        # ── Ambiguity ──────────────────────────────────────────────────────────
        {
            "signal_id": "ambiguity_operates_without_direction",
            "dimension": "ambiguity",
            "description": "Creates structure and moves forward without a clear brief.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ambiguity"],
            "evidence_hints": ["no clear brief", "figured it out", "defined the scope",
                                "green field", "I created structure", "no one knew"],
        },
        {
            "signal_id": "ambiguity_iterates_under_change",
            "dimension": "ambiguity",
            "description": "Adapts plan when requirements shift; doesn't get stuck.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ambiguity"],
            "evidence_hints": ["changed approach", "pivoted", "requirements changed",
                                "adjusted the plan", "learned as we went", "re-evaluated"],
        },
        {
            "signal_id": "ambiguity_tests_assumptions",
            "dimension": "ambiguity",
            "description": "Validates assumptions through low-cost experiments.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["ambiguity"],
            "evidence_hints": ["hypothesis", "experiment", "tested assumption",
                                "validated", "ran a test", "tried a different"],
        },
        # ── Feedback ───────────────────────────────────────────────────────────
        {
            "signal_id": "feedback_seeks_feedback",
            "dimension": "feedback",
            "description": "Actively seeks feedback rather than waiting for it.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["feedback", "coachability"],
            "evidence_hints": ["I asked for feedback", "I sought input", "I checked in",
                                "I requested a review", "wanted to know how I was doing"],
        },
        {
            "signal_id": "feedback_acts_on_feedback",
            "dimension": "feedback",
            "description": "Applies feedback and demonstrates changed behaviour.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["feedback", "coachability"],
            "evidence_hints": ["after the feedback", "I took that on board", "I applied it",
                                "I improved", "I changed how", "I worked on"],
        },
        {
            "signal_id": "feedback_reflective_learning",
            "dimension": "feedback",
            "description": "Reflects honestly on failures and draws clear lessons.",
            "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
            "tags": ["feedback", "coachability"],
            "evidence_hints": ["reflected on", "learned from", "made me think",
                                "recognised I need", "I realised", "in hindsight"],
        },
    ],
}
