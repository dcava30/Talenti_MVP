# Talenti API Reference (FastAPI)

This API is served by the FastAPI backend and uses PostgreSQL for persistence.
All endpoints require a valid JWT unless explicitly noted.

## Base URL

```
http://<backend-host>:8000
```

## Authentication

- `POST /api/auth/register` - Create a user account.
- `POST /api/auth/login` - Obtain access/refresh tokens.
- `POST /api/auth/refresh` - Refresh an access token.
- `POST /api/auth/logout` - Revoke the current session.
- `GET /api/auth/me` - Get the current user.

## Interviews & Scoring

- `POST /api/v1/interview/chat` - AI interviewer chat.
- `POST /api/v1/scoring/analyze` - Score an interview transcript.
- `POST /api/v1/interviews` - Create interview.
- `POST /api/v1/interviews/start` - Start or resume the active interview for an application and trigger background orchestration.
- `GET /api/v1/interviews/{id}` - Fetch interview.
- `PATCH /api/v1/interviews/{id}` - Update interview.
- `POST /api/v1/interviews/{id}/complete` - Complete an interview and enqueue post-interview orchestration.
- `GET /api/v1/interviews/{id}/transcripts` - List transcripts.
- `POST /api/v1/interviews/{id}/transcripts` - Add transcript segment.
- `GET /api/v1/interviews/{id}/score` - Fetch score.
- `POST /api/v1/interviews/{id}/scores` - Save score.

## Candidates

- `POST /api/v1/candidates/parse-resume` - Parse resume text.
- `GET /api/v1/candidates/profile` - Get profile.
- `POST /api/v1/candidates/profile` - Create/update profile.
- `PATCH /api/v1/candidates/{user_id}/profile` - Update profile.
- `POST /api/v1/candidates/cv` - Deprecated local-development fallback for direct CV upload.

## Roles, Requirements, Shortlist

- `POST /api/roles` - Create role.
- `GET /api/roles` - List roles.
- `GET /api/roles/{role_id}` - Get role.
- `PATCH /api/roles/{role_id}` - Update role.
- `PATCH /api/roles/{role_id}/rubric` - Update rubric.
- `POST /api/v1/roles/extract-requirements` - Extract requirements.
- `POST /api/v1/shortlist/generate` - Generate shortlist.

## Invitations

- `POST /api/invitations` - Create invitation.
- `GET /api/v1/invitations` - List invitations.
- `PATCH /api/v1/invitations/{id}` - Update invitation.
- `GET /api/v1/invitations/validate` - Validate invitation token.

## Storage

- `POST /api/storage/upload-url` - Create Azure Blob upload URL for direct browser upload. This is the primary deployed CV upload entrypoint.

## Azure Communication Services

- `POST /api/v1/acs/token` - Create ACS token.
- `POST /api/v1/acs/webhook` - ACS webhook receiver.

## Speech

- `POST /api/v1/speech/token` - Generate speech token.

## Data Retention

- `POST /api/v1/data-retention/cleanup` - Run retention cleanup.

## Notes

- The backend uses PostgreSQL; configure `DATABASE_URL` in `.env`.
- Uploads are stored in Azure Blob Storage in deployed environments (see `.env.example`).
- Candidate CV upload in deployed environments is: request `/api/storage/upload-url` -> upload directly to Blob -> save `cv_file_id` on the candidate profile.
- Interview start/complete lifecycle endpoints trigger DB-backed background jobs. Those jobs are processed when `backend-worker` is running; in the current lean cloud setup that worker is started locally on demand.


