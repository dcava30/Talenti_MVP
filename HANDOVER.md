# Talenti Handover

This handover describes the current Talenti platform architecture: **React frontend + FastAPI backend + SQLite** with Azure service integrations.

## 1. System Overview

- **Frontend:** React (Vite) + Tailwind CSS
- **Backend:** FastAPI (Python) + SQLite
- **Auth:** JWT issued and validated by FastAPI
- **Storage:** Azure Blob Storage
- **AI + Comms:** Azure OpenAI, Azure Communication Services, Azure Speech

## 2. Backend Responsibilities

The backend handles:
- User registration, login, and JWT refresh
- Interview orchestration and scoring
- Candidate profiles, applications, and invitations
- File upload URLs and storage metadata
- Azure token issuance (ACS, Speech)

## 3. Key API Endpoints

- Auth: `/api/auth/*`
- Interviews: `/api/v1/interviews/*`
- AI Chat: `/api/v1/interview/chat`
- Scoring: `/api/v1/scoring/analyze`
- Candidates: `/api/v1/candidates/*`
- Invitations: `/api/invitations` + `/api/v1/invitations/*`
- Storage: `/api/storage/upload-url`
- ACS: `/api/v1/acs/*`
- Speech: `/api/v1/speech/token`

## 4. Configuration

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL=sqlite:///./data/app.db`
- `JWT_SECRET` and optional JWT settings
- Azure credentials for ACS, Speech, OpenAI, and Blob Storage

## 5. Running Locally

```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd ..
export VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev
```

## 6. Deployment Notes

- Ensure the SQLite database path is writable on the server.
- Configure all Azure environment variables.
- Use a secure JWT secret in production.

## 7. Operational Runbook (Quick)

- **Health check:** `GET /health`
- **Auth issues:** verify JWT settings and user table migrations.
- **Storage issues:** verify Azure Blob credentials and container name.
- **AI issues:** verify Azure OpenAI credentials and deployment name.
- **Speech issues:** verify Azure Speech key/region.
