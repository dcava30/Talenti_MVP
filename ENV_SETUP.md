# Environment Setup

Talenti runs with a FastAPI backend, SQLite database, and Azure service integrations.

## Prerequisites

- Python 3.11+
- Node.js 18+

## Backend Setup (FastAPI + SQLite)

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Update `.env` with your values. At minimum:

- `DATABASE_URL` (SQLite file path)
- `JWT_SECRET`
- Azure credentials (ACS, Speech, OpenAI, Blob Storage)

3. Start the API:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

```bash
npm install
export VITE_API_BASE_URL=http://localhost:8000
npm run dev
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
