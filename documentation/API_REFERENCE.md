# Talenti API Reference (FastAPI)

> Last Updated: April 2026

This API is served by the FastAPI backend on port 8000 and uses PostgreSQL for persistence.
All endpoints require a valid JWT unless explicitly noted. Tokens are passed via `Authorization: Bearer <token>`.

## Base URL

```
http://<backend-host>:8000
```

Interactive docs are available at `/docs` (Swagger UI) and `/redoc` (ReDoc) in non-production environments.

---

## Health

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Service health check | No |

---

## Authentication (`/api/auth`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register` | Create a new user account | No |
| POST | `/api/auth/login` | Obtain access and refresh tokens | No |
| POST | `/api/auth/refresh` | Refresh an access token using the refresh-token cookie | No |
| POST | `/api/auth/logout` | Revoke the current session | No |
| GET | `/api/auth/me` | Get the current authenticated user | Yes |
| GET | `/api/auth/claim-context` | Validate an invitation token before account claim (query: `token`) | No |
| POST | `/api/auth/claim-invite` | Claim an invited account with email and password | No |

---

## Organizations (`/api/orgs`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/orgs` | Create a new organization | Yes |
| GET | `/api/orgs/current` | Get current user's organization membership | Yes |
| PATCH | `/api/orgs/{organisation_id}/retention` | Update recording retention policy | Yes |
| GET | `/api/orgs/{organisation_id}/stats` | Get org statistics (roles, candidates, interviews, avg score) | Yes |
| POST | `/api/orgs/{organisation_id}/environment` | Submit operating-environment questionnaire (10 answers) | Yes |
| POST | `/api/orgs/{organisation_id}/environment/aggregate` | Aggregate environment from multiple respondents via majority voting | Yes |

---

## Job Roles (`/api/roles`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/roles` | Create a job role | Yes |
| GET | `/api/roles` | List job roles (optional query: `organisation_id`) | Yes |
| GET | `/api/roles/{role_id}` | Get job role details | Yes |
| PATCH | `/api/roles/{role_id}` | Update job role fields | Yes |
| PATCH | `/api/roles/{role_id}/rubric` | Update scoring rubric for a role | Yes |

### Requirements Extraction (`/api/v1/roles`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/roles/extract-requirements` | Extract skills, responsibilities, and qualifications from a job description | Yes |

---

## Candidates (`/api/v1/candidates`)

### Profile

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/candidates/profile` | Get candidate profile (optional query: `user_id`) | Yes |
| POST | `/api/v1/candidates/profile` | Upsert (create or update) candidate profile | Yes |
| PATCH | `/api/v1/candidates/{user_id}/profile` | Update candidate profile by user ID | Yes |
| POST | `/api/v1/candidates/profile/confirm` | Confirm and lock candidate profile | Yes |
| POST | `/api/v1/candidates/parse-resume` | Parse resume text or uploaded file | Yes |
| POST | `/api/v1/candidates/cv` | Upload CV file directly (local-development fallback; use `/api/storage/upload-url` in deployed environments) | Yes |
| DELETE | `/api/v1/candidates/{user_id}` | Delete candidate account | Yes |

### Employment History

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/candidates/employment` | List employment history (optional query: `user_id`) | Yes |
| POST | `/api/v1/candidates/employment` | Create employment history entry | Yes |
| PATCH | `/api/v1/candidates/employment/{employment_id}` | Update employment entry | Yes |
| DELETE | `/api/v1/candidates/employment/{employment_id}` | Delete employment entry | Yes |

### Education

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/candidates/education` | List education entries (optional query: `user_id`) | Yes |
| POST | `/api/v1/candidates/education` | Create education entry | Yes |
| PATCH | `/api/v1/candidates/education/{education_id}` | Update education entry | Yes |
| DELETE | `/api/v1/candidates/education/{education_id}` | Delete education entry | Yes |

### Skills

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/candidates/skills` | List candidate skills (optional query: `user_id`) | Yes |
| POST | `/api/v1/candidates/skills` | Create skill entry | Yes |
| DELETE | `/api/v1/candidates/skills/{skill_id}` | Delete skill | Yes |

### Candidate-Facing Lists

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/candidates/applications` | List candidate's applications | Yes |
| POST | `/api/v1/candidates/applications` | Create application (body: `job_role_id`) | Yes |
| GET | `/api/v1/candidates/invitations` | List candidate's invitations | Yes |
| GET | `/api/v1/candidates/feedback` | List candidate feedback | Yes |

### Practice Interviews

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/candidates/practice-interviews` | List practice interviews | Yes |
| POST | `/api/v1/candidates/practice-interviews` | Create practice interview | Yes |
| GET | `/api/v1/candidates/practice-interviews/{practice_id}` | Get practice interview | Yes |
| PATCH | `/api/v1/candidates/practice-interviews/{practice_id}` | Update practice interview | Yes |

### Data Deletion (GDPR)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/candidates/deletion-requests` | List data deletion requests | Yes |
| POST | `/api/v1/candidates/deletion-requests` | Create data deletion request | Yes |

---

## Resume Batches (`/api/v1/resume-batches`)

Bulk resume upload, parsing, and candidate invitation workflow.

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/resume-batches` | Create a new resume ingestion batch | Yes |
| GET | `/api/v1/resume-batches/{batch_id}` | Get batch details | Yes |
| GET | `/api/v1/resume-batches/{batch_id}/items` | List items in a batch | Yes |
| POST | `/api/v1/resume-batches/{batch_id}/items/upload-url` | Generate Blob Storage upload URL for a batch item | Yes |
| POST | `/api/v1/resume-batches/{batch_id}/process` | Process batch items (parse resumes via background jobs) | Yes |
| PATCH | `/api/v1/resume-batches/items/{item_id}` | Update batch item (email, review status) | Yes |
| POST | `/api/v1/resume-batches/{batch_id}/invite` | Send invitations to candidates from a processed batch | Yes |

---

## Applications (`/api/v1`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/applications` | Create application | Yes |
| GET | `/api/v1/applications` | List applications (optional query: `candidate_id`) | Yes |
| PATCH | `/api/v1/applications/{application_id}` | Update application status or metadata | Yes |
| GET | `/api/v1/applications/{application_id}/context` | Get full application context (candidate, job, org, competencies) | Yes |
| GET | `/api/v1/roles/{role_id}/applications` | List applications for a specific role | Yes |

---

## Invitations

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/invitations` | Create invitation for an application | Yes |
| GET | `/api/v1/invitations` | List invitations (optional query: `application_id`) | Yes |
| PATCH | `/api/v1/invitations/{invitation_id}` | Update invitation status | Yes |
| GET | `/api/v1/invitations/validate` | Validate invitation token (query: `token`) | No |

---

## Interviews (`/api/v1/interviews`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/interviews` | Create interview session | Yes |
| POST | `/api/v1/interviews/start` | Start or resume the active interview for an application; triggers background orchestration | Yes |
| GET | `/api/v1/interviews/active` | Get active interview (query: `application_id`) | Yes |
| GET | `/api/v1/interviews/{interview_id}` | Get interview details | Yes |
| PATCH | `/api/v1/interviews/{interview_id}` | Update interview metadata | Yes |
| POST | `/api/v1/interviews/{interview_id}/complete` | Complete an interview; enqueues post-interview orchestration | Yes |
| GET | `/api/v1/interviews/{interview_id}/transcripts` | List transcript segments | Yes |
| POST | `/api/v1/interviews/{interview_id}/transcripts` | Add transcript segment | Yes |
| GET | `/api/v1/interviews/{interview_id}/score` | Get interview score | Yes |
| GET | `/api/v1/interviews/{interview_id}/dimensions` | List score dimensions | Yes |
| POST | `/api/v1/interviews/{interview_id}/scores` | Save or update interview scores | Yes |
| GET | `/api/v1/interviews/{interview_id}/report` | Get full interview report (interview + score + dimensions + transcripts) | Yes |

---

## AI Interview Chat (`/api/v1/interview`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/interview/chat` | AI interviewer chat — generates the next interview question | Yes |

---

## Scoring (`/api/v1/scoring`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/scoring/analyze` | Score interview transcript against culture fit (model-service-1) and skills fit (model-service-2) | Yes |

---

## Interview Scores (`/api/v1/interview-scores`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| PATCH | `/api/v1/interview-scores/{score_id}` | Update interview score | Yes |
| POST | `/api/v1/interview-scores/{score_id}/override` | Set human override of hiring recommendation | Yes |
| POST | `/api/v1/interview-scores/{score_id}/outcomes` | Record post-hire performance outcome | Yes |

---

## Shortlist (`/api/v1/shortlist`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/shortlist/generate` | Generate ranked shortlist of candidates for a role | Yes |

---

## Storage (`/api/storage`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/storage/upload-url` | Generate Azure Blob Storage SAS upload URL for direct browser upload | Yes |

This is the primary deployed CV/resume upload entrypoint. The flow is: request upload URL -> browser uploads directly to Blob Storage -> save `cv_file_id` on the candidate profile.

---

## Azure Communication Services (`/api/v1/acs`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/acs/token` | Create ACS identity token for video calls | Yes |
| POST | `/api/v1/acs/webhook` | ACS webhook receiver for recording and call-state events | No |
| POST | `/api/v1/acs/worker-events` | Internal callback from python-acs-service for recording completion | Header (`X-ACS-Worker-Secret`) |

---

## Call Automation (`/api/v1/call-automation`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/call-automation/calls` | Create outbound interview call | Yes |
| POST | `/api/v1/call-automation/calls/{call_connection_id}/hangup` | Hang up an interview call | Yes |
| POST | `/api/v1/call-automation/recordings/start` | Start recording on an active call | Yes |
| POST | `/api/v1/call-automation/recordings/{recording_id}/stop` | Stop a recording | Yes |

---

## Speech (`/api/v1/speech`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/speech/token` | Generate Azure Speech Services token for TTS/STT | Yes |

---

## Data Retention (`/api/v1/data-retention`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/data-retention/cleanup` | Execute data retention cleanup (remove expired recordings, anonymize data) | Yes |

---

## Audit Log (`/api/v1/audit-log`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/audit-log` | List audit log entries (optional query: `organisation_id`) | Yes |
| POST | `/api/v1/audit-log` | Create audit log entry | Yes |

---

## Notes

- The backend uses PostgreSQL; configure `DATABASE_URL` in `.env`.
- Uploads are stored in Azure Blob Storage in deployed environments (see `.env.example`).
- Interview start/complete lifecycle endpoints trigger DB-backed background jobs processed by `backend-worker`.
- Scoring calls both model-service-1 (culture/behavioral fit) and model-service-2 (skills/technical fit) and combines results.
- The `python-acs-service` communicates with the backend via the `/api/v1/acs/worker-events` callback authenticated by a shared secret.
- All requests include an `X-Request-ID` header for tracing; pass one in the request or the backend generates a UUID.
