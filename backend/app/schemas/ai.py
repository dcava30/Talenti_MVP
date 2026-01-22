from pydantic import BaseModel


class InterviewMessage(BaseModel):
    role: str
    content: str


class AiInterviewerRequest(BaseModel):
    interview_id: str
    messages: list[InterviewMessage]
    job_title: str | None = None
    job_description: str | None = None


class AiInterviewerResponse(BaseModel):
    reply: str
    usage_tokens: int | None = None
