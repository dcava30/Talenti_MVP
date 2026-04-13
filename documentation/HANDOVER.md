# Talenti Handover

> Last Updated: April 2026

This handover describes the Talenti AI interview platform — a microservices system for conducting, scoring, and reporting on AI-powered candidate interviews.

For the full architecture diagrams (system design, runtime topology, environment layout, delivery pipeline), see [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md).

## 1. System Overview

| Service | Technology | Port | Ingress |
|---------|-----------|------|---------|
| **Frontend** | React 18 + Vite | 8080 (dev) | Public (Static Web Apps / Front Door) |
| **Backend API** | FastAPI (Python 3.11) | 8000 | Public |
| **Backend Worker** | Same image as backend | — | Internal |
| **model-service-1** | FastAPI (Python 3.11) | 8001 | Internal |
| **model-service-2** | FastAPI (Python 3.11) | 8002 | Internal |
| **python-acs-service** | FastAPI (Python 3.11) | Internal | Internal |
| **PostgreSQL** | PostgreSQL 16 | 5432 | Internal |

- **Auth:** JWT issued and validated by FastAPI (HS256, configurable TTL)
- **Storage:** Azure Blob Storage (SAS URL upload pattern)
- **AI + Comms:** Azure OpenAI, Azure Communication Services, Azure Speech

## 2. Backend Responsibilities

The backend API handles:
- User registration, login, JWT refresh, and invitation claim flow
- Interview orchestration (create, start, complete, transcript, scoring)
- Background job processing (`background_jobs` table) and domain event handling (`domain_events` table)
- Candidate profiles (personal info, employment, education, skills, CV)
- Job role management, requirements extraction, and scoring rubrics
- Resume batch upload, parsing, and candidate invitation
- Azure token issuance (ACS identity, Speech)
- Audit logging and GDPR data deletion requests

The **backend-worker** polls the `background_jobs` table and processes:
- Resume parsing and profile prefill
- Auto-scoring (when `AUTO_SCORE_INTERVIEWS=true`)
- Invitation preparation
- Recording processing

## 3. Model Services (Dual Scorecard)

Scoring is split into two independent assessments that are never merged:

**model-service-1 (Culture/Behavioural Fit)** — port 8001
- Analyses interview transcripts against the organisation's operating environment
- Returns scores across 5 canonical dimensions: ownership, execution, challenge, ambiguity, feedback
- Decision-dominant architecture: ML extracts signals, deterministic rules produce scores

**model-service-2 (Skills/Technical Fit)** — port 8002
- Evaluates competencies from transcripts against job description requirements
- Returns per-competency scores with outcomes: PASS / REVIEW / FAIL
- Deterministic scoring with configurable weights and thresholds

The backend orchestrates scoring via `POST /api/v1/scoring/analyze`, calling both services and storing results in `interview_scores` and `score_dimensions`.

## 4. Python ACS Service

An internal microservice for Azure Communication Services call automation:
- Creates and manages outbound interview calls
- Starts/stops call recordings
- Processes recording artifacts and notifies the backend via callback
- Authenticated via shared secret (`ACS_WORKER_SHARED_SECRET`)
- No public ingress — only the backend and backend-worker communicate with it

## 5. Key API Endpoints

See [API_REFERENCE.md](./API_REFERENCE.md) for the complete list (~90 endpoints). Key groups:

- Auth: `/api/auth/*` (register, login, refresh, claim-invite)
- Organisations: `/api/orgs/*` (create, environment setup, stats, retention)
- Roles: `/api/roles/*` (CRUD, rubric, requirements extraction)
- Candidates: `/api/v1/candidates/*` (profile, employment, education, skills, CV, practice interviews)
- Applications: `/api/v1/applications/*`
- Interviews: `/api/v1/interviews/*` (create, start, complete, transcripts, scores, report)
- Scoring: `/api/v1/scoring/analyze`
- Resume Batches: `/api/v1/resume-batches/*` (upload, parse, invite)
- Invitations: `/api/invitations` + `/api/v1/invitations/*`
- Storage: `/api/storage/upload-url`
- ACS: `/api/v1/acs/*` + `/api/v1/call-automation/*`
- Speech: `/api/v1/speech/token`
- Audit: `/api/v1/audit-log`

The primary interview lifecycle:
1. `POST /api/v1/interviews/start` — starts interview, enqueues orchestration
2. `POST /api/v1/interviews/{id}/transcripts` — streams transcript segments
3. `POST /api/v1/interviews/{id}/complete` — completes interview, enqueues post-interview jobs
4. `POST /api/v1/scoring/analyze` — scores transcript against both models

## 6. Configuration

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/talenti`
- `JWT_SECRET` (required)
- `MODEL_SERVICE_1_URL` and `MODEL_SERVICE_2_URL`
- `ACS_WORKER_URL` and `ACS_WORKER_SHARED_SECRET`
- Azure credentials: ACS, Speech, OpenAI, Blob Storage

See [ENV_SETUP.md](./ENV_SETUP.md) for the complete environment variable reference.

## 7. Running Locally

**Quick start (Windows):**
```powershell
.\scripts\start-local.ps1
```

**Manual:**
```bash
# Backend API
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Backend worker (separate terminal)
cd backend
python -m app.worker_main

# Frontend
export VITE_API_BASE_URL=http://localhost:8000
npm install && npm run dev
```

For model services, see `model-service-1/QUICKSTART.md` and `model-service-2/README.md`.

Docker Compose is available for running all services:
```bash
docker compose up
```

## 8. Deployment & CI/CD

- **CI:** PR gates include lint, test, build, CodeQL, CVE scan, IaC scan, and ephemeral deploy
- **CD:** `ci-main` builds immutable images → `deploy-dev` → `release-please` → auto-promote to UAT → manual promote to PROD
- Images are signed and attested; `release-manifest.json` captures exact digests
- See [RELEASE_PIPELINE.md](./RELEASE_PIPELINE.md) and [DEPLOYMENT_DEV_V2.md](./DEPLOYMENT_DEV_V2.md)

## 9. Operational Runbook (Quick)

- **Health check:** `GET /health` (backend), `GET /health` (model services), `GET /health` (ACS service)
- **Auth issues:** verify `JWT_SECRET` and user table migrations
- **Storage issues:** verify Azure Blob credentials and container name
- **Stuck orchestration jobs:** verify `backend-worker` is deployed and can reach PostgreSQL; check `background_jobs` table for `failed` status
- **Scoring failures:** verify `MODEL_SERVICE_1_URL` and `MODEL_SERVICE_2_URL` are reachable; check model service health endpoints
- **Call/recording issues:** verify `python-acs-service` is running; check `ACS_WORKER_SHARED_SECRET` matches between services
- **AI chat issues:** verify Azure OpenAI credentials and deployment name
- **Speech issues:** verify Azure Speech key/region


