from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class TranscriptSegment(BaseModel):
    speaker: str
    content: str


class OperatingEnvironment(BaseModel):
    control_vs_autonomy: str
    outcome_vs_process: str
    conflict_style: str
    decision_reality: str
    ambiguity_load: str
    high_performance_archetype: str
    dimension_weights: dict[str, float]
    fatal_risks: list[str] | None = None
    coachable_risks: list[str] | None = None


class TaxonomySignal(BaseModel):
    signal_id: str
    dimension: str
    description: str
    score_map: dict[str, float]
    anti_signal_of: str | None = None
    tags: list[str] | None = None
    evidence_hints: list[str] | None = None


class TaxonomyPayload(BaseModel):
    taxonomy_id: str
    version: str
    created_utc: str | None = None
    signals: list[TaxonomySignal]


class ScoringRequest(BaseModel):
    interview_id: str
    transcript: list[TranscriptSegment]
    rubric: dict[str, float] | None = None
    job_description: str | None = None
    resume_text: str | None = None
    role_title: str | None = None
    seniority: str | None = None
    org_id: str | None = None
    role_id: str | None = None
    department_id: str | None = None
    application_id: str | None = None
    operating_environment: OperatingEnvironment | None = None
    taxonomy: TaxonomyPayload | None = None
    trace: bool | None = None


# ── Culture fit scorecard ──────────────────────────────────────────────────────
# Produced by model-service-1. Scores the 5 canonical behavioural dimensions
# (ownership, execution, challenge, ambiguity, feedback) against the org's
# operating environment. Includes environment-adjusted pass/watch/risk outcomes.

class BehaviouralDimension(BaseModel):
    """One of the 5 canonical behavioural dimensions scored by model-service-1."""
    name: str
    score: int                         # 0-100
    confidence: float | None = None    # evidence-derived, independent of score
    outcome: str | None = None         # pass | watch | risk
    required_pass: int | None = None   # env-adjusted pass threshold
    required_watch: int | None = None  # env-adjusted watch threshold
    gap: int | None = None             # score − required_pass (negative = shortfall)
    matched_signals: list[str] | None = None
    rationale: str | None = None
    source: str | None = None          # service1


class DimensionOutcome(BaseModel):
    outcome: str          # pass | watch | risk
    required_pass: int
    required_watch: int
    gap: int


class CultureFitResult(BaseModel):
    """
    Behavioural / culture fit scorecard from model-service-1.
    Environment-specific: thresholds are derived from the org's operating environment.
    """
    overall_score: int                                      # 0-100 weighted aggregate
    overall_alignment: str | None = None                   # strong_fit | mixed_fit | weak_fit
    overall_risk_level: str | None = None                  # low | medium | high
    recommendation: str | None = None                      # proceed | caution | reject
    dimensions: list[BehaviouralDimension]                 # one entry per canonical dimension
    dimension_outcomes: dict[str, DimensionOutcome] | None = None
    summary: str | None = None


# ── Skills fit scorecard ───────────────────────────────────────────────────────
# Produced by model-service-2. Scores the candidate's demonstrated skills against
# the specific competencies required by the job description and resume.
# Skill names are role-specific (e.g. python, azure, rag) — not canonical dimensions.

class SkillScore(BaseModel):
    """Score for a single JD-derived skill competency."""
    score: int                               # 0-100 (converted from model's 0-1)
    confidence: float | None = None          # 0-1
    rationale: str | None = None
    years_detected: float | None = None      # years of experience detected
    matched_keywords: list[str] | None = None


class SkillsFitResult(BaseModel):
    """
    Skills / competency scorecard from model-service-2.
    Role-specific: skill names are derived from the job description.
    """
    overall_score: int                       # 0-100
    outcome: str | None = None              # PASS | REVIEW | FAIL
    skills: dict[str, SkillScore]           # {skill_name: score_detail}
    must_haves_passed: list[str]
    must_haves_failed: list[str]
    gaps: list[str]
    summary: str | None = None


# ── Combined response ─────────────────────────────────────────────────────────

class ScoringResponse(BaseModel):
    interview_id: str
    culture_fit: CultureFitResult
    skills_fit: SkillsFitResult | None = None   # None if model-service-2 unavailable or no JD supplied


class HumanOverride(BaseModel):
    decision: str     # proceed | caution | reject
    reason: str | None = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        allowed = {"proceed", "caution", "reject"}
        if v not in allowed:
            raise ValueError(f"decision must be one of {allowed}")
        return v


class PostHireOutcomeCreate(BaseModel):
    observed_at: datetime
    snapshot_period: str = "custom"   # 3_month | 6_month | 12_month | custom
    outcome_rating: float             # 1-5 scale
    outcome_notes: str | None = None
    dimension_ratings: dict[str, float] | None = None  # {dim: 1-5}

    @field_validator("snapshot_period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        allowed = {"3_month", "6_month", "12_month", "custom"}
        if v not in allowed:
            raise ValueError(f"snapshot_period must be one of {allowed}")
        return v

    @field_validator("outcome_rating")
    @classmethod
    def validate_rating(cls, v: float) -> float:
        if not (1.0 <= v <= 5.0):
            raise ValueError("outcome_rating must be between 1 and 5")
        return v


class PostHireOutcomeResponse(BaseModel):
    id: str
    interview_score_id: str
    observed_at: datetime
    snapshot_period: str
    outcome_rating: float
    outcome_notes: str | None = None
    dimension_ratings: dict[str, float] | None = None
    recorded_by: str | None = None
    created_at: datetime


class InterviewScoreResponse(BaseModel):
    """Full interview score record as stored in the DB."""
    id: str
    interview_id: str
    culture_fit_score: int
    skills_score: int | None = None
    skills_outcome: str | None = None
    overall_alignment: str | None = None
    overall_risk_level: str | None = None
    recommendation: str | None = None
    human_override: str | None = None
    human_override_reason: str | None = None
    dimension_outcomes: dict[str, Any] | None = None
    summary: str | None = None
    model_version: str | None = None
    created_at: Any = None
