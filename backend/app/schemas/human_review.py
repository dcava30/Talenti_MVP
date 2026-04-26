from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated
from typing import Any

from pydantic import BaseModel, ConfigDict, StringConstraints


class HumanReviewActionType(str, Enum):
    HUMAN_REVIEW = "HUMAN_REVIEW"
    EXCEPTION_RECORDED = "EXCEPTION_RECORDED"
    ADDITIONAL_CONTEXT = "ADDITIONAL_CONTEXT"
    DISAGREEMENT_RECORDED = "DISAGREEMENT_RECORDED"


class HumanReviewOutcome(str, Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PROCEED_WITH_HUMAN_EXCEPTION = "PROCEED_WITH_HUMAN_EXCEPTION"
    HOLD_FOR_FURTHER_REVIEW = "HOLD_FOR_FURTHER_REVIEW"
    DISAGREE_WITH_SYSTEM_DECISION = "DISAGREE_WITH_SYSTEM_DECISION"
    NO_ACTION_TAKEN = "NO_ACTION_TAKEN"


class CreateHumanReviewActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: HumanReviewActionType
    review_outcome: HumanReviewOutcome
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    notes: str | None = None
    display_delta: dict[str, Any] | list[Any] | None = None


class HumanReviewActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    human_review_action_id: str
    decision_id: str
    original_decision_state: str
    action_type: HumanReviewActionType
    review_outcome: HumanReviewOutcome
    reason: str
    notes: Any = None
    display_delta: dict[str, Any] | list[Any] | None = None
    reviewed_by: str
    created_at: datetime
    audit_event_id: str | None = None
