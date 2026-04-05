from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, field_validator


class OrganisationCreate(BaseModel):
    name: str
    description: str | None = None
    industry: str | None = None
    website: str | None = None
    values_framework: dict[str, Any] | str | None = None


class OrganisationResponse(BaseModel):
    id: str
    name: str
    description: str | None
    industry: str | None
    website: str | None
    created_at: datetime


class OrganisationDetail(BaseModel):
    id: str
    name: str
    description: str | None
    industry: str | None
    website: str | None
    values_framework: str | None
    recording_retention_days: int | None
    created_at: datetime
    updated_at: datetime


class OrgMembershipResponse(BaseModel):
    id: str
    role: str
    organisation: OrganisationDetail


class OrgRetentionUpdate(BaseModel):
    recording_retention_days: int


class OrgStatsResponse(BaseModel):
    activeRoles: int
    totalCandidates: int
    completedInterviews: int
    avgMatchScore: int | None


# ---------------------------------------------------------------------------
# Org environment questionnaire schemas
# ---------------------------------------------------------------------------

# Valid answer choices per question (mirrored from org_environment.py for Pydantic validation)
_Q1_CHOICES = Literal[
    "we_tell_people_exactly_what_to_do",
    "we_set_goals_and_guide_the_how",
    "we_set_direction_and_people_own_it",
]
_Q2_CHOICES = Literal[
    "reliable_follows_process_delivers_consistently",
    "owns_outcomes_balances_action_and_reflection",
    "sets_direction_challenges_status_quo_drives_change",
]
_Q3_CHOICES = Literal[
    "hitting_the_numbers_outcomes_above_all",
    "good_process_and_good_outcomes",
    "following_the_right_process_consistently",
]
_Q4_CHOICES = Literal[
    "we_move_fast_decide_with_70pct_info",
    "we_weigh_evidence_before_deciding",
    "senior_people_make_the_calls",
]
_Q5_CHOICES = Literal[
    "we_align_first_avoid_open_conflict",
    "we_debate_ideas_respectfully",
    "we_expect_people_to_challenge_directly",
]
_Q6_CHOICES = Literal[
    "raise_concern_privately_then_align",
    "voice_disagreement_constructively",
    "push_back_hard_and_change_the_outcome",
]
_Q7_CHOICES = Literal[
    "roles_are_clearly_defined_with_process",
    "roles_evolve_with_business_needs",
    "people_define_their_own_scope",
]
_Q8_CHOICES = Literal[
    "we_plan_carefully_and_follow_the_plan",
    "we_adapt_as_we_learn",
    "we_thrive_in_chaos_and_figure_it_out",
]
_Q9_CHOICES = Literal[
    "feedback_is_formal_review_cycle_only",
    "feedback_is_given_informally_when_needed",
    "feedback_is_continuous_and_expected",
]
_Q10_CHOICES = Literal[
    "people_are_expected_to_grow_on_their_own",
    "managers_coach_and_people_are_expected_to_improve",
    "coachability_is_a_hard_requirement_not_optional",
]


class OrgEnvironmentSetup(BaseModel):
    """
    10 constrained questions that define the organisation's operating environment.
    Each field maps to exactly one valid choice from the rubric.
    """
    # Q1-Q2: Proactivity / Ownership
    q1_direction_style: _Q1_CHOICES
    q2_success_archetype: _Q2_CHOICES
    # Q3-Q4: Drive / Execution
    q3_what_matters_most: _Q3_CHOICES
    q4_decision_style: _Q4_CHOICES
    # Q5-Q6: Collaboration / Challenge
    q5_conflict_tolerance: _Q5_CHOICES
    q6_bad_decision_response: _Q6_CHOICES
    # Q7-Q8: Adaptability / Ambiguity
    q7_role_clarity: _Q7_CHOICES
    q8_handles_change: _Q8_CHOICES
    # Q9-Q10: Coachability / Feedback
    q9_feedback_culture: _Q9_CHOICES
    q10_growth_expectation: _Q10_CHOICES

    def to_answers_dict(self) -> Dict[str, str]:
        """Convert to the flat dict format expected by translate_answers_to_environment."""
        return self.model_dump()


class VariableSignalResponse(BaseModel):
    """Lineage record: which answer drove which variable value."""
    question_id: str
    answer: str
    variable: str
    derived_value: str
    weight: float


class OrgEnvironmentSetupResponse(BaseModel):
    """Response from POST /api/orgs/{org_id}/environment."""
    org_id: str
    input_id: str
    derived_environment: Dict[str, str]
    defaulted_variables: List[str]
    extra_fatal_risks: List[str]
    signals: List[VariableSignalResponse]
    values_framework_updated: bool
