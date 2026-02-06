# Talenti API Reference (FastAPI)

This API is served by the FastAPI backend and uses SQLite for persistence.
All endpoints require a valid JWT unless explicitly noted.

## Base URL

```
http://<backend-host>:8000
```

## Authentication

- `POST /api/auth/register` — Create a user account.
- `POST /api/auth/login` — Obtain access/refresh tokens.
- `POST /api/auth/refresh` — Refresh an access token.
- `POST /api/auth/logout` — Revoke the current session.
- `GET /api/auth/me` — Get the current user.

## Interviews & Scoring

- `POST /api/v1/interview/chat` — AI interviewer chat.
- `POST /api/v1/scoring/analyze` — Score an interview transcript.
- `POST /api/v1/interviews` — Create interview.
- `GET /api/v1/interviews/{id}` — Fetch interview.
- `PATCH /api/v1/interviews/{id}` — Update interview.
- `GET /api/v1/interviews/{id}/transcripts` — List transcripts.
- `POST /api/v1/interviews/{id}/transcripts` — Add transcript segment.
- `GET /api/v1/interviews/{id}/score` — Fetch score.
- `POST /api/v1/interviews/{id}/scores` — Save score.

## Candidates

- `POST /api/v1/candidates/parse-resume` — Parse resume text.
- `GET /api/v1/candidates/profile` — Get profile.
- `POST /api/v1/candidates/profile` — Create/update profile.
- `PATCH /api/v1/candidates/{user_id}/profile` — Update profile.
- `POST /api/v1/candidates/cv` — Upload CV (multipart).

## Roles, Requirements, Shortlist

- `POST /api/roles` — Create role.
- `GET /api/roles` — List roles.
- `GET /api/roles/{role_id}` — Get role.
- `PATCH /api/roles/{role_id}` — Update role.
- `PATCH /api/roles/{role_id}/rubric` — Update rubric.
- `POST /api/v1/roles/extract-requirements` — Extract requirements.
- `POST /api/v1/shortlist/generate` — Generate shortlist.

## Invitations

- `POST /api/invitations` — Create invitation.
- `GET /api/v1/invitations` — List invitations.
- `PATCH /api/v1/invitations/{id}` — Update invitation.
- `GET /api/v1/invitations/validate` — Validate invitation token.

## Storage

- `POST /api/storage/upload-url` — Create Azure Blob upload URL.

## Azure Communication Services

- `POST /api/v1/acs/token` — Create ACS token.
- `POST /api/v1/acs/webhook` — ACS webhook receiver.

## Speech

- `POST /api/v1/speech/token` — Generate speech token.

## Data Retention

- `POST /api/v1/data-retention/cleanup` — Run retention cleanup.

## Notes

- The backend uses SQLite; configure `DATABASE_URL` in `.env`.
- Uploads are stored in Azure Blob Storage (see `.env.example`).
