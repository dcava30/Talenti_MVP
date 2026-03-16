# Dev Deployment v2 (Backend Public, Internal Workers)

## Topology

- Public:
  - Frontend (Static Web Apps)
  - Backend API (Container Apps external ingress)
- Internal only:
  - backend-worker (`python -m app.worker_main`)
  - model-service-1
  - model-service-2
  - acs-worker (`python-acs-service`)

## Database

- Backend is the only system-of-record.
- Use PostgreSQL database: `talenti_backend_dev`.
- Backend worker and ACS worker both use backend-managed state; neither requires a separate database.

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

## Required Backend Worker App Settings

- `DATABASE_URL`
- `JWT_SECRET`
- `ENVIRONMENT`
- `MODEL_SERVICE_1_URL`
- `MODEL_SERVICE_2_URL`
- `ACS_WORKER_URL`
- `ACS_WORKER_SHARED_SECRET`
- `PUBLIC_BASE_URL`
- `AZURE_STORAGE_ACCOUNT`
- `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_STORAGE_CONTAINER`
- `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS`
- `AUTO_SCORE_INTERVIEWS`

## Required ACS Worker App Settings

- `ACS_CONNECTION_STRING`
- `AZURE_STORAGE_CONNECTION_STRING`
- `RECORDING_CONTAINER=recordings`
- `BACKEND_INTERNAL_URL`
- `ACS_WORKER_SHARED_SECRET`
- `ACS_CALLBACK_URL` (set to backend public callback endpoint)

## CI/CD

- `infra-dev.yml`: deploys Bicep infra with OIDC.
- `deploy-dev.yml`:
  - Builds/pushes backend and ACS worker images from this repo.
  - Deploys the same backend image to both `backend` and `backend-worker`.
  - Consumes pinned model images from GitHub environment `dev` variables:
    - `DEV_MODEL1_IMAGE_REF`
    - `DEV_MODEL2_IMAGE_REF`
  - Fails fast if model refs are missing, malformed, or unresolved in ACR.
  - Runs backend migrations once, deploys internal services then backend, deploys frontend.

## Pinned Model Promotion Runbook

1. In model repo pipelines, retrieve immutable digest refs for successful dev images:
   - `acrtalentidev.azurecr.io/talenti/model-service-1@sha256:<64-hex>`
   - `acrtalentidev.azurecr.io/talenti/model-service-2@sha256:<64-hex>`
2. In GitHub -> main repo -> Settings -> Environments -> `dev`, set variables:
   - `DEV_MODEL1_IMAGE_REF=<model1 digest ref>`
   - `DEV_MODEL2_IMAGE_REF=<model2 digest ref>`
3. Trigger `deploy-dev` workflow (manual or matching push).
4. Verify deployment:
   - Backend health endpoint returns 200.
   - `backend-worker` is running and `background_jobs` are not stuck in `pending`.
   - Container Apps `ca-model1-dev` and `ca-model2-dev` revisions reference the pinned digest images.

## Migration

- Backend runs Alembic `upgrade head` automatically at startup and fails fast on migration errors.
- Keep `python backend/scripts/run_migrations.py` in the deployment pipeline as a pre-deploy safety check.
- If `backend-worker` is not deployed or unhealthy, interview orchestration and async file/scoring jobs will remain queued in `background_jobs`.
