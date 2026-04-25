from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DecisionInspectionAuditTrailSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_count: int
    event_types: list[str]
    latest_event_at: datetime | None = None


class DecisionInspectionDimensionEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    dimension: str
    score_internal: int | None = None
    confidence: str | None = None
    required_level: str | None = None
    threshold_status: str | None = None
    outcome: str | None = None
    evidence_summary: str | dict[str, Any] | list[Any] | None = None
    rationale: str | None = None
    created_at: datetime


class DecisionInspectionRiskFlagResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    risk_code: str
    severity: str
    source_dimension: str | None = None
    trigger_rule: str | None = None
    context: dict[str, Any] | list[Any] | str | None = None
    created_at: datetime


class DecisionInspectionAuditEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    decision_id: str
    event_type: str
    event_at: datetime
    actor_type: str
    actor_user_id: str | None = None
    rule_version: str | None = None
    policy_version: str | None = None
    event_payload: dict[str, Any] | list[Any] | str | None = None
    created_at: datetime


class DecisionInspectionSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    decision_mode: str = "shadow"
    interview_id: str
    candidate_id: str
    role_id: str
    organisation_id: str
    decision_state: str
    decision_valid: bool
    confidence: str
    confidence_gate_passed: bool
    integrity_status: str
    rule_version: str
    policy_version: str
    created_at: datetime


class DecisionInspectionDetailResponse(DecisionInspectionSummaryResponse):
    model_config = ConfigDict(extra="forbid")

    org_environment_input_id: str | None = None
    environment_profile: dict[str, Any]
    critical_dimensions: list[str]
    minimum_dimensions: list[str]
    priority_dimensions: list[str]
    dimension_evaluations: list[DecisionInspectionDimensionEvaluationResponse]
    evidence_gaps: list[str]
    invalid_signals: list[str]
    conflict_flags: list[str]
    risk_stack: list[DecisionInspectionRiskFlagResponse]
    execution_floor_result: dict[str, Any]
    trade_off_statement: str | None = None
    conditions: list[str]
    rationale: str | None = None
    audit_trace: list[dict[str, Any] | str]
    audit_trail_summary: DecisionInspectionAuditTrailSummaryResponse
