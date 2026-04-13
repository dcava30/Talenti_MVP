# Talenti AI Interview Platform

> Last Updated: April 2026

Talenti is a B2B AI-powered interview platform that conducts, scores, and reports on candidate interviews using Azure Cognitive Services. The platform produces a **dual scorecard** — culture/behavioural fit and skills/technical fit — scored independently and never merged.

---

## Architecture

| Service | Stack | Port |
|---------|-------|------|
| Frontend | React 18 + Vite + Tailwind + shadcn/ui | 8080 |
| Backend API | FastAPI + PostgreSQL 16 | 8000 |
| Backend Worker | Same codebase as backend | — |
| model-service-1 | FastAPI (culture fit scoring) | 8001 |
| model-service-2 | FastAPI (skills fit scoring) | 8002 |
| python-acs-service | FastAPI (call automation) | Internal |

Key integrations: Azure Communication Services (video calls), Azure Speech (TTS/STT), Azure OpenAI (AI interviewer), Azure Blob Storage (files).

## How can I edit this code?

There are several ways of editing your application.

**Use your preferred IDE**

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the main app repository over SSH.
git clone git@github.com:dcava30/Talenti_MVP.git

# Step 2: Navigate to the project directory.
cd Talenti_MVP

# Step 3: Clone the model repositories into the expected local folders.
powershell -ExecutionPolicy Bypass -File .\scripts\setup-model-repos.ps1 -SshKeyPath C:\Users\Declan\.ssh\id_ed25519_personal -Fetch

# Step 4: Install the necessary dependencies.
npm i

# Step 5: Create local environment configuration at repo root.
cp .env.example .env

# Step 6: Start the backend API (FastAPI + PostgreSQL).
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Step 7: Start the backend worker for background jobs.
python -m app.worker_main

# Step 8: Start the frontend development server with auto-reloading and an instant preview.
cd ..
export VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Or on Windows, bootstrap and start all local services with one command:

```powershell
.\scripts\start-local.ps1
```

To use an external PostgreSQL instance:

```powershell
.\scripts\start-local.ps1 -DatabaseMode external -ExternalDatabaseUrl "postgresql+psycopg://user:pass@host:5432/dbname"
```

Windows (manual startup) equivalents:

```powershell
Copy-Item .env.example .env
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python -m app.worker_main
cd ..
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

**Frontend:**
- React 18 + Vite + JavaScript (JSX)
- TanStack React Query 5 (server state)
- React Hook Form + Zod (forms and validation)
- shadcn/ui + Tailwind CSS (styling)
- Azure SDKs: Communication Calling, Speech SDK, Avatar

**Backend:**
- FastAPI + Python 3.11
- PostgreSQL 16 + SQLAlchemy 2 + Alembic
- JWT authentication (python-jose + bcrypt)
- Azure SDKs: Blob Storage, Communication Identity, OpenAI

**ML Scoring:**
- model-service-1: Culture fit (decision-dominant, deterministic rules)
- model-service-2: Skills fit (hybrid deterministic + ML)

## Documentation

| Document | Description |
|----------|-------------|
| [HANDOVER.md](documentation/HANDOVER.md) | Technical handover and system overview |
| [ARCHITECTURE_DIAGRAM.md](documentation/ARCHITECTURE_DIAGRAM.md) | Mermaid architecture diagrams (system, runtime, infra, CI/CD) |
| [ARCHITECTURE_DECISIONS.md](documentation/ARCHITECTURE_DECISIONS.md) | Architecture decision records (ADRs) |
| [API_REFERENCE.md](documentation/API_REFERENCE.md) | FastAPI endpoint reference (~90 endpoints) |
| [DATABASE_SCHEMA.md](documentation/DATABASE_SCHEMA.md) | PostgreSQL tables and relationships |
| [FRONTEND_GUIDE.md](documentation/FRONTEND_GUIDE.md) | React architecture and implementation guide |
| [USER_GUIDE.md](documentation/USER_GUIDE.md) | End-user workflow guide |
| [ENV_SETUP.md](documentation/ENV_SETUP.md) | Environment setup and local configuration |
| [CODEX_CAPABILITY_SETUP.md](documentation/CODEX_CAPABILITY_SETUP.md) | Local GitHub/Azure auth, model repo setup, and OIDC bootstrap |
| [RELEASE_PIPELINE.md](documentation/RELEASE_PIPELINE.md) | Release, promotion, and GitHub Actions workflow guide |
| [DEPLOYMENT_DEV_V2.md](documentation/DEPLOYMENT_DEV_V2.md) | Dev deployment topology and runbook |
| [MONITORING.md](documentation/MONITORING.md) | Logging, metrics, and observability guidance |
| [AZURE_DEV_UAT_PROD_SETUP.txt](documentation/AZURE_DEV_UAT_PROD_SETUP.txt) | Azure environment setup notes |

## How can I deploy this project?

Deploy the FastAPI service, backend worker, and Vite frontend using your preferred infrastructure (container platform, VM, or PaaS).
Ensure both backend runtimes have access to the PostgreSQL DSN and required Azure credentials.
In deployed dev/staging/prod, candidate CV uploads should use Blob-first upload via `/api/storage/upload-url`; the direct `/api/v1/candidates/cv` route is only a local fallback.

For the GitHub Actions release flow, start with [CODEX_CAPABILITY_SETUP.md](documentation/CODEX_CAPABILITY_SETUP.md), [RELEASE_PIPELINE.md](documentation/RELEASE_PIPELINE.md), [DEPLOYMENT_DEV_V2.md](documentation/DEPLOYMENT_DEV_V2.md), and [MONITORING.md](documentation/MONITORING.md). DEV keeps Azure Static Web Apps with a separate hosting region, while UAT/PROD use Azure Storage static website hosting in `australiaeast` behind Azure Front Door Standard.



