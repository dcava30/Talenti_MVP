import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id"))
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey("candidate_profiles.id"))
    role_id: Mapped[str] = mapped_column(String, ForeignKey("job_roles.id"))
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.id"))
    org_environment_input_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("org_environment_inputs.id"),
        nullable=True,
    )
    decision_state: Mapped[str] = mapped_column(String)
    decision_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[str] = mapped_column(String)
    confidence_gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    integrity_status: Mapped[str] = mapped_column(String)
    environment_profile_json: Mapped[str] = mapped_column(Text)
    critical_dimensions_json: Mapped[str] = mapped_column(Text)
    minimum_dimensions_json: Mapped[str] = mapped_column(Text)
    priority_dimensions_json: Mapped[str] = mapped_column(Text)
    evidence_gaps_json: Mapped[str] = mapped_column(Text)
    invalid_signals_json: Mapped[str] = mapped_column(Text)
    conflict_flags_json: Mapped[str] = mapped_column(Text)
    execution_floor_result_json: Mapped[str] = mapped_column(Text)
    trade_off_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions_json: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_trace_json: Mapped[str] = mapped_column(Text)
    rule_version: Mapped[str] = mapped_column(String)
    policy_version: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dimension_evaluations: Mapped[List["DecisionDimensionEvaluation"]] = relationship(  # noqa: F821
        "DecisionDimensionEvaluation",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    signal_evidence_items: Mapped[List["DecisionSignalEvidence"]] = relationship(  # noqa: F821
        "DecisionSignalEvidence",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    risk_flags: Mapped[List["DecisionRiskFlag"]] = relationship(  # noqa: F821
        "DecisionRiskFlag",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    audit_trail_entries: Mapped[List["DecisionAuditTrail"]] = relationship(  # noqa: F821
        "DecisionAuditTrail",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    human_review_actions: Mapped[List["HumanReviewAction"]] = relationship(  # noqa: F821
        "HumanReviewAction",
        back_populates="decision",
        cascade="all, delete-orphan",
    )
