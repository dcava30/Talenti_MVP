# Dev Deployment v2 (Backend Public, Internal ACS Worker)

## Topology

- Public:
  - Frontend (Static Web Apps)
  - Backend API (Container Apps external ingress)
- Internal only:
  - model-service-1
  - model-service-2
  - acs-worker (`python-acs-service`)

## Database

- Backend is the only system-of-record.
- Use PostgreSQL database: `talenti_backend_dev`.
- ACS worker does not require its own database for deployed profile.

## Required Backend App Settings

- `DATABASE_URL`
- `JWT_SECRET`
- `ALLOWED_ORIGINS`
- `MODEL_SERVICE_1_URL`
- `MODEL_SERVICE_2_URL`
- `ACS_WORKER_URL`
- `ACS_WORKER_SHARED_SECRET`
- `PUBLIC_BASE_URL`
- Existing Azure settings:
  - `AZURE_ACS_CONNECTION_STRING`
  - `AZURE_SPEECH_KEY`
  - `AZURE_SPEECH_REGION`
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_DEPLOYMENT`
  - `AZURE_STORAGE_ACCOUNT`
  - `AZURE_STORAGE_ACCOUNT_KEY`
  - `AZURE_STORAGE_CONTAINER`

## Required ACS Worker App Settings

- `ACS_CONNECTION_STRING`
- `AZURE_STORAGE_CONNECTION_STRING`
- `RECORDING_CONTAINER=recordings`
- `BACKEND_INTERNAL_URL`
- `ACS_WORKER_SHARED_SECRET`
- `ACS_CALLBACK_URL` (set to backend public callback endpoint)

## CI/CD

- `infra-dev.yml`: deploys Bicep infra with OIDC.
- `deploy-dev.yml`: builds/pushes images, runs backend migrations once, deploys internal services then backend, deploys frontend.

## Migration

- Backend no longer runs Alembic at startup.
- Use: `python backend/scripts/run_migrations.py` in deployment pipeline.
