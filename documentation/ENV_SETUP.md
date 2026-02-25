# Environment Setup

Talenti runs with a FastAPI backend, SQLite database, and Azure service integrations.

## Prerequisites

- Python 3.11+
- Node.js 18+

## Backend Setup (FastAPI + SQLite)

1. Copy the example environment file to the repository root:

```powershell
Copy-Item .env.example .env
```

2. Update root `.env` with your values. At minimum:

- `DATABASE_URL` (SQLite file path)
- `JWT_SECRET`
- `MODEL_SERVICE_1_URL` and `MODEL_SERVICE_2_URL`
- Azure credentials (ACS, Speech, OpenAI, Blob Storage) for cloud-backed features

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

## Storage Configuration

Uploads are stored in Azure Blob Storage. Set:

- `AZURE_STORAGE_ACCOUNT`
- `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_STORAGE_CONTAINER`

## Auth Configuration

Auth is handled by FastAPI using JWTs and a local user table. Set:

- `JWT_SECRET`
- Optional: `JWT_ISSUER`, `JWT_AUDIENCE`, and TTL values.
