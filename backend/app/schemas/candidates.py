from pydantic import BaseModel, EmailStr


class ParseResumeRequest(BaseModel):
    candidate_id: str
    resume_text: str


class ParsedResume(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    skills: list[str] = []


class ParseResumeResponse(BaseModel):
    candidate_id: str
    parsed: ParsedResume
