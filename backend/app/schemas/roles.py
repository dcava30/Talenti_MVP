from datetime import datetime
from typing import Dict, Literal

from pydantic import BaseModel, field_validator


class JobRoleCreate(BaseModel):
    organisation_id: str
    title: str
    description: str | None = None
    department: str | None = None
    location: str | None = None
    work_type: str | None = None
    employment_type: str | None = None


class JobRoleResponse(BaseModel):
    id: str
    organisation_id: str
    title: str
    status: str
    created_at: datetime


class JobRoleDetail(BaseModel):
    id: str
    organisation_id: str
    title: str
    description: str | None
    department: str | None
    location: str | None
    work_type: str | None
    employment_type: str | None
    industry: str | None
    requirements: str | None
    scoring_rubric: str | None
    interview_structure: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class JobRoleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    department: str | None = None
    location: str | None = None
    work_type: str | None = None
    employment_type: str | None = None
    industry: str | None = None
    requirements: str | None = None
    interview_structure: str | None = None
    status: str | None = None


DimensionTier = Literal["Standard", "Important", "Critical"]

CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]


class DimensionRubricEntry(BaseModel):
    """
    Per-dimension rubric configuration for a job role.

    weight   — multiplier applied when computing the weighted overall culture fit score (≥ 0)
    tier     — importance classification that affects risk stacking:
               Standard  → existing risk-count rules unchanged
               Important → a risk on this dimension counts as 2 in the risk stack
               Critical  → a risk on this dimension immediately triggers reject
    """
    weight: float = 1.0
    tier: DimensionTier = "Standard"

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if v < 0:
            raise ValueError("weight must be >= 0")
        return round(v, 4)


class JobRoleRubricUpdate(BaseModel):
    """
    PATCH /{role_id}/rubric request body.

    Accepts a structured rubric where each canonical dimension may have a
    weight and tier. Only dimensions in the canonical set are accepted.
    Omitted dimensions default to weight=1.0, tier=Standard.
    """
    dimensions: Dict[str, DimensionRubricEntry]

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, v: Dict[str, DimensionRubricEntry]) -> Dict[str, DimensionRubricEntry]:
        unknown = [k for k in v if k not in CANONICAL_DIMENSIONS]
        if unknown:
            raise ValueError(
                f"Unknown dimension(s): {unknown}. "
                f"Must be one of: {CANONICAL_DIMENSIONS}"
            )
        return v

    def to_rubric_json(self) -> str:
        """Serialise to the JSON string stored in job_roles.scoring_rubric."""
        import json
        return json.dumps({
            dim: {"weight": entry.weight, "tier": entry.tier}
            for dim, entry in self.dimensions.items()
        })
