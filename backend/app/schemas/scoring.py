from typing import Any

from pydantic import BaseModel


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


class ScoringDimension(BaseModel):
    name: str
    score: int
    rationale: str | None = None
    # Decision-dominant fields
    confidence: float | None = None
    outcome: str | None = None       # pass | watch | risk
    required_pass: int | None = None
    required_watch: int | None = None
    gap: int | None = None           # score − required_pass
    matched_signals: list[str] | None = None
    source: str | None = None        # service1 | service2 | merged


class DimensionOutcome(BaseModel):
    outcome: str                     # pass | watch | risk
    required_pass: int
    required_watch: int
    gap: int


class HumanOverride(BaseModel):
    decision: str                    # proceed | caution | reject
    reason: str | None = None


class ScoringResponse(BaseModel):
    interview_id: str
    overall_score: int
    dimensions: list[ScoringDimension]
    summary: str
    # Decision-dominant top-level outputs
    overall_alignment: str | None = None     # strong_fit | mixed_fit | weak_fit
    overall_risk_level: str | None = None    # low | medium | high
    recommendation: str | None = None        # proceed | caution | reject
    dimension_outcomes: dict[str, DimensionOutcome] | None = None


class InterviewScoreResponse(BaseModel):
    """Full interview score record as stored in the DB."""
    id: str
    interview_id: str
    overall_score: int
    overall_alignment: str | None = None
    overall_risk_level: str | None = None
    recommendation: str | None = None
    human_override: str | None = None
    human_override_reason: str | None = None
    dimension_outcomes: dict[str, Any] | None = None
    summary: str | None = None
    model_version: str | None = None
    created_at: Any = None
