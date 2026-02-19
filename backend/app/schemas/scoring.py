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


class ScoringResponse(BaseModel):
    interview_id: str
    overall_score: int
    dimensions: list[ScoringDimension]
    summary: str
