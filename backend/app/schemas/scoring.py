from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    speaker: str
    content: str


class ScoringRequest(BaseModel):
    interview_id: str
    transcript: list[TranscriptSegment]
    rubric: dict[str, float] | None = None


class ScoringDimension(BaseModel):
    name: str
    score: int
    rationale: str | None = None


class ScoringResponse(BaseModel):
    interview_id: str
    overall_score: int
    dimensions: list[ScoringDimension]
    summary: str
