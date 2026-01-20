from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.candidates import ParseResumeRequest, ParseResumeResponse, ParsedResume

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])


@router.post("/parse-resume", response_model=ParseResumeResponse)
def parse_resume(
    payload: ParseResumeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ParseResumeResponse:
    if not payload.resume_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume text required")

    lines = [line.strip() for line in payload.resume_text.splitlines() if line.strip()]
    name = lines[0] if lines else None
    email = next((line for line in lines if "@" in line), None)
    skills = [line for line in lines if line.lower().startswith("skill")]

    parsed = ParsedResume(full_name=name, email=email, skills=skills)
    return ParseResumeResponse(candidate_id=payload.candidate_id, parsed=parsed)
