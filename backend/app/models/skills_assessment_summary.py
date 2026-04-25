import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SkillsAssessmentSummary(Base):
    __tablename__ = "skills_assessment_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id"))
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey("candidate_profiles.id"))
    role_id: Mapped[str] = mapped_column(String, ForeignKey("job_roles.id"))
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.id"))
    observed_competencies_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    competency_coverage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_gaps_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_strength: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    source_references_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_readable_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    excluded_from_tds_decisioning: Mapped[bool] = mapped_column(Boolean, default=True)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
