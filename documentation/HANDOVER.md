# Talenti Handover

This handover describes the current Talenti platform architecture: **React frontend + FastAPI backend + PostgreSQL** with Azure service integrations.

## 1. System Overview

- **Frontend:** React (Vite) + Tailwind CSS
- **Backend:** FastAPI (Python) + PostgreSQL
- **Backend worker:** Local/on-demand runtime for DB-backed jobs/events in the current cost-controlled setup
- **Auth:** JWT issued and validated by FastAPI
- **Storage:** Azure Blob Storage
- **AI + Comms:** Azure OpenAI, Azure Communication Services, Azure Speech

## 2. Backend Responsibilities

The backend handles:
- User registration, login, and JWT refresh
- Interview orchestration and scoring
- Background job processing (`background_jobs`) and domain event handling (`domain_events`)
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

The primary candidate-facing interview lifecycle is:

- `POST /api/v1/interviews/start`
- `POST /api/v1/interviews/{id}/complete`

## 4. Configuration

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/talenti`
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

- Current live cloud deployment is `dev` only.
- The public demo currently uses the raw Azure URLs:
  - Frontend: `https://witty-bush-06941cf00.4.azurestaticapps.net`
  - Backend: `https://ca-backend-dev.delightfulground-722f8c60.australiaeast.azurecontainerapps.io`
- Ensure the PostgreSQL instance is reachable from the backend.
- Configure Azure environment variables for the backend.
- Use a secure JWT secret in production.
- `background_jobs` remain pending unless a developer starts the local worker with [`start-dev-worker-local.ps1`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/scripts/start-dev-worker-local.ps1).
- Live scoring and ACS call automation are disabled in the lean cloud baseline.

## 7. Operational Runbook (Quick)

- **Health check:** `GET /health`
- **Auth issues:** verify JWT settings and user table migrations.
- **Storage issues:** verify Azure Blob credentials and container name.
- **Stuck orchestration jobs:** start the local `backend-worker` and verify it can reach PostgreSQL.
- **AI issues:** verify Azure OpenAI credentials and deployment name.
- **Speech issues:** verify Azure Speech key/region.


