"""Resume parsing endpoints."""
from fastapi import APIRouter, Depends

from app.schemas.resume import ResumeParseRequest, ResumeParseResponse
from app.security.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/parse", response_model=ResumeParseResponse)
def parse_resume(
    payload: ResumeParseRequest,
    user: User = Depends(get_current_user),
) -> ResumeParseResponse:
    """Parse resume content into a simple summary."""
    content_preview = payload.content.strip()[:120]
    summary = f"Parsed resume for {user.username}: {content_preview}"
    skills = ["communication", "problem-solving", "teamwork"]
    return ResumeParseResponse(summary=summary, skills=skills)
