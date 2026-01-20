from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.core.config import settings
from app.models import Application, Interview, JobRole, User
from app.schemas.ai import AiInterviewerRequest, AiInterviewerResponse
from app.services.openai_client import get_openai_client

router = APIRouter(prefix="/api/v1/interview", tags=["ai"])


@router.post("/chat", response_model=AiInterviewerResponse)
def interview_chat(
    payload: AiInterviewerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiInterviewerResponse:
    interview = db.query(Interview).filter(Interview.id == payload.interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    application = db.query(Application).filter(Application.id == interview.application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    job_role = db.query(JobRole).filter(JobRole.id == application.job_role_id).first()
    if not job_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job role not found")
    require_org_member(job_role.organisation_id, db, user)
    if not payload.messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Messages required")

    if payload.job_title and payload.job_description:
        system_prompt = (
            f"Role: {payload.job_title}\nDescription: {payload.job_description}\n"
            "Conduct a structured interview and respond with the next question."
        )
    else:
        system_prompt = "Conduct a structured interview and respond with the next question."

    if not (settings.azure_openai_endpoint and settings.azure_openai_api_key and settings.azure_openai_deployment):
        last_message = payload.messages[-1].content
        fallback = f"Thanks for sharing. Could you expand on: {last_message[:120]}"
        return AiInterviewerResponse(reply=fallback, usage_tokens=None)

    try:
        client = get_openai_client()
        completion = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                *[message.model_dump() for message in payload.messages],
            ],
        )
        reply = completion.choices[0].message.content or ""
        usage_tokens = completion.usage.total_tokens if completion.usage else None
        return AiInterviewerResponse(reply=reply, usage_tokens=usage_tokens)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Azure OpenAI request failed"
        ) from exc
