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


# ---------------------------------------------------------------------------
# Multi-respondent environment aggregation schemas
# ---------------------------------------------------------------------------

# Minimum number of questions a single respondent must answer for their
# submission to count. Below this threshold the response is rejected (422).
MIN_QUESTIONS_PER_RESPONDENT = 6


class OrgEnvironmentPartialSetup(BaseModel):
    """
    Partial questionnaire — used for multi-respondent submissions where each
    stakeholder answers a subset of the 10 questions.

    All fields are optional but at least MIN_QUESTIONS_PER_RESPONDENT must be
    provided. Omitted fields are treated as null (null exclusion during aggregation).
    """
    respondent_label: str | None = None  # optional identifier (e.g. "CEO", "HM-1")

    q1_direction_style: Optional[_Q1_CHOICES] = None
    q2_success_archetype: Optional[_Q2_CHOICES] = None
    q3_what_matters_most: Optional[_Q3_CHOICES] = None
    q4_decision_style: Optional[_Q4_CHOICES] = None
    q5_conflict_tolerance: Optional[_Q5_CHOICES] = None
    q6_bad_decision_response: Optional[_Q6_CHOICES] = None
    q7_role_clarity: Optional[_Q7_CHOICES] = None
    q8_handles_change: Optional[_Q8_CHOICES] = None
    q9_feedback_culture: Optional[_Q9_CHOICES] = None
    q10_growth_expectation: Optional[_Q10_CHOICES] = None

    @field_validator("*", mode="before")
    @classmethod
    def _skip_none(cls, v: Any) -> Any:
        return v

    def answered_count(self) -> int:
        question_fields = [
            "q1_direction_style", "q2_success_archetype", "q3_what_matters_most",
            "q4_decision_style", "q5_conflict_tolerance", "q6_bad_decision_response",
            "q7_role_clarity", "q8_handles_change", "q9_feedback_culture",
            "q10_growth_expectation",
        ]
        return sum(1 for f in question_fields if getattr(self, f) is not None)

    def to_answers_dict(self) -> Dict[str, str]:
        """Return only the answered questions as a flat dict."""
        question_fields = [
            "q1_direction_style", "q2_success_archetype", "q3_what_matters_most",
            "q4_decision_style", "q5_conflict_tolerance", "q6_bad_decision_response",
            "q7_role_clarity", "q8_handles_change", "q9_feedback_culture",
            "q10_growth_expectation",
        ]
        return {f: getattr(self, f) for f in question_fields if getattr(self, f) is not None}


class MultiRespondentEnvironmentSetup(BaseModel):
    """
    Request body for POST /api/orgs/{org_id}/environment/aggregate.
    Accepts 2-10 partial questionnaire responses from different stakeholders.
    """
    respondents: List[OrgEnvironmentPartialSetup]

    @field_validator("respondents")
    @classmethod
    def validate_respondents(cls, v: List[OrgEnvironmentPartialSetup]) -> List[OrgEnvironmentPartialSetup]:
        if len(v) < 2:
            raise ValueError("At least 2 respondents are required for aggregation.")
        if len(v) > 10:
            raise ValueError("A maximum of 10 respondents is supported.")
        return v


class VariableAggregationResponse(BaseModel):
    """Per-variable agreement summary from aggregation."""
    variable: str
    resolved_value: str
    top_value_weight_share: float   # fraction of respondent weight on the winning value
    all_responded_values: List[str] # all distinct values seen across respondents
    is_contested: bool              # True when no clear majority (< 60% share)
    respondent_count: int           # respondents who answered this variable
    is_defaulted: bool              # True when no respondent answered this variable


class AggregatedEnvironmentResponse(BaseModel):
    """Response from POST /api/orgs/{org_id}/environment/aggregate."""
    org_id: str
    respondent_count: int
    environment_confidence: str              # high | medium | low
    derived_environment: Dict[str, str]
    variable_aggregations: Dict[str, VariableAggregationResponse]
    contested_variables: List[str]           # variables with no clear majority
    defaulted_variables: List[str]           # variables no one answered
    extra_fatal_risks: List[str]
    values_framework_updated: bool
    # Reviewer guidance when confidence is low or variables are contested
    reviewer_flags: List[str]
