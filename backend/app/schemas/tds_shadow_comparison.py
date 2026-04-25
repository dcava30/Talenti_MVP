from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LegacyScoreSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legacy_score_id: str | None = None
    present: bool
    culture_fit_score: int | None = None
    overall_score: int | None = None
    recommendation: str | None = None
    overall_alignment: str | None = None
    overall_risk_level: str | None = None
    skills_score: int | None = None
    legacy_skills_outcome_status: str = "unavailable"
    created_at: datetime | None = None


class TdsDecisionSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str | None = None
    present: bool
    decision_state: str | None = None
    decision_valid: bool | None = None
    confidence: str | None = None
    confidence_gate_passed: bool | None = None
    integrity_status: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    rule_version: str | None = None
    policy_version: str | None = None
    created_at: datetime | None = None


class SkillsSummaryStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills_summary_id: str | None = None
    status: str
    requires_human_review: bool | None = None
    evidence_strength: str | None = None
    excluded_from_tds_decisioning: bool | None = None
    created_at: datetime | None = None


class ComparisonResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_status: str
    comparison_notes: list[str] = Field(default_factory=list)


class TdsShadowComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interview_id: str
    candidate_id: str
    role_id: str
    organisation_id: str
    interview_created_at: datetime
    legacy_score_summary: LegacyScoreSummaryResponse
    tds_decision_summary: TdsDecisionSummaryResponse
    skills_summary_status: SkillsSummaryStatusResponse
    comparison_result: ComparisonResultResponse


class RoleShadowComparisonSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: str
    organisation_id: str
    total_interviews: int
    with_legacy_score: int
    with_tds_decision: int
    with_skills_summary: int
    aligned: int
    shifted_more_cautious: int
    shifted_less_cautious: int
    insufficient_evidence: int
    legacy_only: int
    tds_only: int
    missing_both: int


class OrganisationShadowComparisonSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organisation_id: str
    total_interviews: int
    with_legacy_score: int
    with_tds_decision: int
    with_skills_summary: int
    aligned: int
    shifted_more_cautious: int
    shifted_less_cautious: int
    insufficient_evidence: int
    legacy_only: int
    tds_only: int
    missing_both: int
