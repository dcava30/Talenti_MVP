# Environment Setup

Talenti runs with a FastAPI backend, a dedicated backend worker, a PostgreSQL database, and Azure service integrations.

## Related Docs

- [`ARCHITECTURE_DIAGRAM.md`](./ARCHITECTURE_DIAGRAM.md) for runtime, infrastructure, and release-flow diagrams
- [`RELEASE_PIPELINE.md`](./RELEASE_PIPELINE.md) for the release contract and promotion rules
- [`MONITORING.md`](./MONITORING.md) for observability and alerting

## Prerequisites

- Python 3.11+
- Node.js 18+
- GitHub CLI (`gh`) for release and environment automation
- Azure CLI (`az`) for cloud provisioning

## Repository Layout

Talenti uses three separate repositories during development:

- main app repo: `git@github.com:dcava30/Talenti_MVP.git`
- `model-service-1`: `git@github.com:dcava30/Talenti_model_culture.git`
- `model-service-2`: `git@github.com:dcava30/Talenti_model_skills.git`

Clone the model repos into the expected local folders before running local scripts:

```powershell
.\scripts\setup-model-repos.ps1 -SshKeyPath C:\Users\Declan\.ssh\id_ed25519_personal -Fetch
```

## Backend Setup (FastAPI + PostgreSQL)

1. Copy the example environment file to the repository root:

```powershell
Copy-Item .env.example .env
```

2. Update root `.env` with your values. At minimum:

- `DATABASE_URL` (PostgreSQL DSN)
- `JWT_SECRET`
- `MODEL_SERVICE_1_URL` and `MODEL_SERVICE_2_URL`
- Azure credentials (ACS, Speech, OpenAI, Blob Storage) for cloud-backed features

## Azure CLI Provisioning + Env Export

If you want Azure to create the backing services first, use the existing Azure CLI provisioning script:

```powershell
.\scripts\day1-dev-deploy.ps1 -SubscriptionId <sub-id>
```

That script provisions the dev Azure resources, stores the resulting secrets in Key Vault, and syncs the GitHub `dev` environment for the deployment workflows.

If you want to create the GitHub environments plus Azure OIDC identities before the first deployment:

```powershell
.\scripts\setup-deployment-access.ps1 -SubscriptionId <sub-id> -AlertEmailAddress <team-email>
```

To write those Azure-backed values into a local env file after provisioning:

```powershell
.\scripts\export-azure-env.ps1 -SubscriptionId <sub-id> -OutputPath .env.azure
```

Profiles:

- `local` (default): writes Azure credentials + database URL, but keeps backend/model/worker URLs on `localhost`
- `deployed`: writes Azure service URLs for the deployed Container Apps as well

Example for deployed URLs:

```powershell
.\scripts\export-azure-env.ps1 -SubscriptionId <sub-id> -Profile deployed -OutputPath .env.azure
```

The generated env file includes backend worker toggles:

- `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS`
- `AUTO_SCORE_INTERVIEWS`

3. Start the API:

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Start the backend worker in a second terminal:

```powershell
cd backend
python -m app.worker_main
```

## Frontend Setup

```powershell
npm install
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

## One-Command Local Startup (Windows)

```powershell
.\scripts\start-local.ps1
```

If you have already installed local dependencies once and only want to relaunch services:

```powershell
.\scripts\start-local.ps1 -SkipDependencyBootstrap
```

## Chunked Local Workflow

Bootstrap local dependencies once:

```powershell
.\scripts\bootstrap-local-deps.ps1
```

Start local PostgreSQL only:

```powershell
.\scripts\start-local-postgres.ps1 -PostgresDb postgres -AdditionalDatabases talenti_backend_test,talenti_acs_test
```

Run backend tests only:

```powershell
.\scripts\run-backend-tests.ps1
```

Run ACS service tests only:

```powershell
.\scripts\run-acs-tests.ps1
```

Run frontend checks only:

```powershell
.\scripts\run-frontend-checks.ps1 -Mode all
```

Run just the frontend dev server:

```powershell
.\scripts\run-frontend-checks.ps1 -Mode dev
```

Run the full test suite through the smaller entry points:

```powershell
.\scripts\run-all-tests.ps1
```

External PostgreSQL mode:

```powershell
.\scripts\start-local.ps1 -DatabaseMode external -ExternalDatabaseUrl "postgresql+psycopg://user:pass@host:5432/dbname"
```

Docker Compose external override:

```powershell
$env:BACKEND_DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname"
docker compose -f docker-compose.yml -f docker-compose.external-db.yml up -d
```

## Storage Configuration

Uploads in deployed environments are stored in Azure Blob Storage. Set:

- `AZURE_STORAGE_ACCOUNT`
- `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_STORAGE_CONTAINER`

The backend worker also reads:

- `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS`
- `AUTO_SCORE_INTERVIEWS`

Notes:

- Deployed dev/uat/prod should use `/api/storage/upload-url` as the primary candidate CV upload flow.
- `/api/v1/candidates/cv` remains a local-development fallback when Blob credentials are unavailable.

## Auth Configuration

Auth is handled by FastAPI using JWTs and a local user table. Set:

- `JWT_SECRET`
- Optional: `JWT_ISSUER`, `JWT_AUDIENCE`, and TTL values.


