from pydantic import BaseModel


class ShortlistCandidate(BaseModel):
    application_id: str
    score: float


class ShortlistRequest(BaseModel):
    job_role_id: str
    candidates: list[ShortlistCandidate]


class ShortlistResponse(BaseModel):
    job_role_id: str
    ranked: list[ShortlistCandidate]
