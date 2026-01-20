from pydantic import BaseModel


class ExtractRequirementsRequest(BaseModel):
    job_role_id: str
    job_description: str


class ExtractRequirementsResponse(BaseModel):
    skills: list[str]
    responsibilities: list[str]
    qualifications: list[str]
