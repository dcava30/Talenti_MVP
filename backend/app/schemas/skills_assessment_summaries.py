from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RecruiterSkillsAssessmentSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills_summary_id: str
    interview_id: str
    candidate_id: str
    role_id: str
    organisation_id: str
    observed_competencies: list[Any] | dict[str, Any]
    competency_coverage: dict[str, Any]
    skill_gaps: list[Any]
    evidence_strength: str | None = None
    confidence: str | None = None
    source_references: list[dict[str, Any]]
    human_readable_summary: str | None = None
    requires_human_review: bool
    excluded_from_tds_decisioning: bool
    decisioning_boundary_note: str
    model_version: str | None = None
    created_at: datetime
