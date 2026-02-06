from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.applications import ApplicationResponse


class InterviewCreate(BaseModel):
    application_id: str
    status: str | None = None
    scheduled_at: datetime | None = None


class InterviewUpdate(BaseModel):
    status: str | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    recording_url: str | None = None
    transcript_status: str | None = None
    summary: str | None = None
    anti_cheat_signals: list[dict[str, Any]] | None = None


class InterviewResponse(BaseModel):
    id: str
    application_id: str
    status: str
    scheduled_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    recording_url: str | None
    transcript_status: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime
    application: ApplicationResponse | None = None


class TranscriptSegmentCreate(BaseModel):
    speaker: str
    content: str
    start_time_ms: int | None = None
    end_time_ms: int | None = None


class TranscriptSegmentResponse(BaseModel):
    id: str
    interview_id: str
    sequence: int
    speaker: str
    content: str
    created_at: datetime
    start_time_ms: int | None = None
    end_time_ms: int | None = None


class ScoreDimensionCreate(BaseModel):
    name: str
    score: int
    rationale: str | None = None


class ScoreDimensionResponse(BaseModel):
    id: str
    interview_id: str
    name: str
    score: int
    rationale: str | None
    created_at: datetime


class InterviewScoreSave(BaseModel):
    interview_id: str
    overall_score: int
    narrative_summary: str | None = None
    candidate_feedback: str | None = None
    dimensions: list[ScoreDimensionCreate] = []


class InterviewScoreUpdate(BaseModel):
    overall_score: int | None = None
    summary: str | None = None
    recommendation: str | None = None


class InterviewScoreResponse(BaseModel):
    id: str
    interview_id: str
    overall_score: int
    summary: str | None
    recommendation: str | None
    created_at: datetime


class InterviewReportResponse(BaseModel):
    interview: InterviewResponse
    score: InterviewScoreResponse | None = None
    dimensions: list[ScoreDimensionResponse] = []
    transcripts: list[TranscriptSegmentResponse] = []
