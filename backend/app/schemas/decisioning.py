from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.talenti_canonical.dimensions import CANONICAL_DIMENSIONS, DimensionName

NON_BEHAVIOURAL_EXCLUSION_FIELDS = frozenset(
    {
        "skills_score",
        "skills_outcome",
        "skills_summary_id",
        "overall_score",
        "match_score",
        "ranking",
        "rank",
        "shortlist_position",
        "best_candidate",
        "best_candidate_id",
        "pass",
        "review",
        "fail",
        "must_haves_passed",
        "must_haves_failed",
        "skill_gaps",
        "gaps",
        "skills_summary",
        "skills_assessment_summary",
        "skills_assessment",
        "skills_fit",
    }
)
SKILLS_EXCLUSION_FIELDS = NON_BEHAVIOURAL_EXCLUSION_FIELDS


class DecisionState(str, Enum):
    PROCEED = "PROCEED"
    PROCEED_WITH_CONDITIONS = "PROCEED_WITH_CONDITIONS"
    DO_NOT_PROCEED = "DO_NOT_PROCEED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class IntegrityState(str, Enum):
    CLEAN = "CLEAN"
    MIXED = "MIXED"
    AT_RISK = "AT_RISK"
    INVALID = "INVALID"


class ConfidenceBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DimensionEvaluationStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"


def find_excluded_non_behavioural_fields(value: Any, path: str = "") -> list[str]:
    matches: list[str] = []

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")

    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in NON_BEHAVIOURAL_EXCLUSION_FIELDS:
                matches.append(nested_path)
            matches.extend(find_excluded_non_behavioural_fields(nested, nested_path))
        return matches

    if isinstance(value, list):
        for index, nested in enumerate(value):
            nested_path = f"{path}[{index}]" if path else f"[{index}]"
            matches.extend(find_excluded_non_behavioural_fields(nested, nested_path))

    return matches


def find_excluded_skills_fields(value: Any, path: str = "") -> list[str]:
    return find_excluded_non_behavioural_fields(value, path)


def assert_behavioural_only_payload(value: Any) -> Any:
    matches = sorted(set(find_excluded_non_behavioural_fields(value)))
    if matches:
        formatted = ", ".join(matches)
        raise ValueError(
            "Decision Layer accepts behavioural evidence only. "
            f"Remove skills-derived fields or ranking fields: {formatted}"
        )
    return value


class BehaviouralDimensionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: DimensionName
    score_internal: int = Field(ge=-2, le=2)
    confidence: ConfidenceBand | None = None
    evidence_summary: str | None = None
    rationale: str | None = None
    valid_signals: list[str] = Field(default_factory=list)
    invalid_signals: list[str] = Field(default_factory=list)
    conflict_flags: list[str] = Field(default_factory=list)


class BehaviouralDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interview_id: str
    candidate_id: str
    role_id: str
    organisation_id: str
    environment_profile: dict[str, Any]
    environment_confidence: ConfidenceBand
    behavioural_dimension_evidence: list[BehaviouralDimensionEvidence]
    critical_dimensions: list[DimensionName] = Field(default_factory=list)
    minimum_dimensions: list[DimensionName] = Field(default_factory=list)
    priority_dimensions: list[DimensionName] = Field(default_factory=list)
    rule_version: str
    policy_version: str

    @model_validator(mode="before")
    @classmethod
    def validate_behavioural_only(cls, value: Any) -> Any:
        return assert_behavioural_only_payload(value)

    @model_validator(mode="after")
    def validate_unique_dimensions(self) -> BehaviouralDecisionInput:
        seen: set[str] = set()
        duplicates: list[str] = []
        for evidence in self.behavioural_dimension_evidence:
            if evidence.dimension in seen:
                duplicates.append(evidence.dimension)
            seen.add(evidence.dimension)
        if duplicates:
            duplicate_text = ", ".join(sorted(set(duplicates)))
            raise ValueError(f"Duplicate behavioural_dimension_evidence dimensions: {duplicate_text}")
        return self


class DecisionDimensionEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: DimensionName
    status: DimensionEvaluationStatus
    score_internal: int | None = Field(default=None, ge=-2, le=2)
    confidence: ConfidenceBand | None = None
    required_level: str | None = None
    threshold_status: str | None = None
    outcome: str | None = None
    evidence_summary: str | None = None
    rationale: str | None = None
    valid_signals: list[str] = Field(default_factory=list)
    invalid_signals: list[str] = Field(default_factory=list)
    conflict_flags: list[str] = Field(default_factory=list)


class DecisionAuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DecisionRiskItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_code: str
    severity: RiskSeverity
    source_dimension: DimensionName
    trigger_rule: str


class ExecutionFloorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    reason: str
    trigger_rule: str | None = None


class BehaviouralDecisionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_state: DecisionState
    decision_valid: bool
    confidence: ConfidenceBand
    confidence_gate_passed: bool
    integrity_status: IntegrityState
    critical_dimensions: list[DimensionName]
    minimum_dimensions: list[DimensionName]
    priority_dimensions: list[DimensionName]
    dimension_evaluations: list[DecisionDimensionEvaluation]
    evidence_gaps: list[DimensionName]
    invalid_signals: list[str]
    conflict_flags: list[str]
    risk_stack: list[DecisionRiskItem]
    execution_floor_result: ExecutionFloorResult
    trade_off_statement: str | None = None
    conditions: list[str]
    rationale: str
    audit_trace: list[DecisionAuditEntry]
    rule_version: str
    policy_version: str


CANONICAL_BEHAVIOURAL_DIMENSIONS = tuple(CANONICAL_DIMENSIONS)


__all__ = [
    "BehaviouralDecisionInput",
    "BehaviouralDecisionOutput",
    "BehaviouralDimensionEvidence",
    "CANONICAL_BEHAVIOURAL_DIMENSIONS",
    "ConfidenceBand",
    "DecisionAuditEntry",
    "DecisionDimensionEvaluation",
    "DecisionRiskItem",
    "DecisionState",
    "DimensionEvaluationStatus",
    "ExecutionFloorResult",
    "IntegrityState",
    "NON_BEHAVIOURAL_EXCLUSION_FIELDS",
    "RiskSeverity",
    "SKILLS_EXCLUSION_FIELDS",
    "assert_behavioural_only_payload",
    "find_excluded_non_behavioural_fields",
    "find_excluded_skills_fields",
]
