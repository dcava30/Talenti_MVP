from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class RecruiterDecisionState(str, Enum):
    PROCEED = "PROCEED"
    PROCEED_WITH_CONDITIONS = "PROCEED_WITH_CONDITIONS"
    DO_NOT_PROCEED = "DO_NOT_PROCEED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RecruiterDecisionRiskSummaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: str
    source_dimension: str | None = None
    summary: str


class RecruiterDecisionEvidenceSummaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str
    outcome: str | None = None
    evidence_summary: str | dict[str, Any] | list[Any] | None = None
    rationale: str | None = None


class RecruiterDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    interview_id: str
    candidate_id: str
    role_id: str
    organisation_id: str
    decision_state: RecruiterDecisionState
    decision_valid: bool
    confidence_gate_passed: bool
    integrity_status: str
    decision_summary: str
    risk_summary: list[RecruiterDecisionRiskSummaryItem]
    evidence_summary: list[RecruiterDecisionEvidenceSummaryItem]
    evidence_gaps: list[str]
    conflict_flags: list[str]
    conditions: list[str]
    trade_off_statement: str | None = None
    rationale: str | None = None
    rule_version: str | None = None
    policy_version: str | None = None
    created_at: datetime
