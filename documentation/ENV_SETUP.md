# Environment Setup

Talenti runs with a FastAPI backend, PostgreSQL database, and Azure service integrations.

## Prerequisites

- Python 3.11+
- Node.js 18+

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
.\scripts\day1-dev-deploy.ps1 -SubscriptionId <sub-id> -TenantId <tenant-id>
```

That script provisions the dev Azure resources and stores the resulting secrets in Key Vault.

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

3. Start the API:

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

Uploads are stored in Azure Blob Storage. Set:

- `AZURE_STORAGE_ACCOUNT`
- `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_STORAGE_CONTAINER`

## Auth Configuration

Auth is handled by FastAPI using JWTs and a local user table. Set:

- `JWT_SECRET`
- Optional: `JWT_ISSUER`, `JWT_AUDIENCE`, and TTL values.


