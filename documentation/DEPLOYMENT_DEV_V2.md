# Dev Deployment v3 (Main-Based Release Candidate Flow)

## Topology

- Public:
  - Frontend (Static Web Apps in `eastasia`; all core DEV infra remains in `australiaeast`)
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
- `LOG_LEVEL`
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
- `BACKGROUND_WORKER_METRICS_LOG_INTERVAL_SECONDS`
- `AUTO_SCORE_INTERVIEWS`
- `LOG_LEVEL`

## Required ACS Worker App Settings

- `ACS_CONNECTION_STRING`
- `AZURE_STORAGE_CONNECTION_STRING`
- `RECORDING_CONTAINER=recordings`
- `BACKEND_INTERNAL_URL`
- `ACS_WORKER_SHARED_SECRET`
- `ACS_CALLBACK_URL` (set to backend public callback endpoint)

## CI/CD

- `pr-fast-quality.yml`: validates PR title, runs frontend/backend/ACS checks, migration execution checks, and coverage gates.
- `pr-security-iac.yml`: enforces secret scanning, dependency/security scanning, container scanning, and Bicep/IaC policy checks.
- `pr-ephemeral-deploy.yml`: deploys isolated PR runtime resources in Azure using the dedicated GitHub `pr-dev` environment, runs migrations and API smoke checks, and tears down resources.
- `ci-main.yml`: builds immutable backend/ACS images once per `main` SHA, generates SBOMs, scans, signatures, and provenance attestations.
- `infra-dev.yml`: validates Bicep and IaC policy on PR/push, runs what-if, and deploys DEV Bicep infra on `main`.
- `codeql.yml`: is the repository's sole CodeQL workflow for PRs, `main`, and weekly scheduled scans.
- `deploy-dev.yml`:
  - Runs after successful `ci-main` on `main`.
  - Resolves immutable backend/ACS image digests for the exact source SHA.
  - Deploys the same backend image digest to both `backend` and `backend-worker`.
  - Consumes pinned model images from GitHub environment `dev` variables:
    - `MODEL1_IMAGE_REF`
    - `MODEL2_IMAGE_REF`
  - Fails fast if model refs are missing, malformed, or unresolved in ACR.
  - Requires matching `infra-dev` success for infra-touching commits.
  - Preflight-checks the resource group, ACR, Key Vault, Container Apps, and Static Web App.
  - Runs backend migrations once, deploys internal services then backend, deploys frontend, and smoke-checks backend/frontend availability.
- `release.yml`:
  - Runs only after successful `deploy-dev` for `main` (or manual dispatch).
  - Uses `release-please` to manage repo-root `VERSION`, `CHANGELOG.md`, and GitHub Releases.
  - Uploads `release-manifest.json` and `frontend-dist.tgz` for promotion.
- `promote-release.yml`:
  - Promotes the released digests and frontend artifact to UAT/PROD without rebuilding them.
  - Verifies release image signatures before deployment.
  - Uploads the frontend artifact to Azure Storage static website hosting and purges Azure Front Door Standard cache.
  - Uses a self-hosted `uat` runner for restricted UAT frontend smoke tests.

Seed the GitHub `dev` and `pr-dev` environments and Azure OIDC identities with:

```powershell
.\scripts\setup-deployment-access.ps1 -SubscriptionId <sub-id> -EnvironmentNames dev,pr-dev -AlertEmailAddress <team-email>
```

For first-time DEV runtime bootstrap, use:

```powershell
.\scripts\day1-dev-deploy.ps1 -SubscriptionId <sub-id> -StaticWebAppLocation eastasia
```

## Pinned Model Promotion Runbook

1. In model repo pipelines, retrieve immutable digest refs for successful dev images:
   - `acrtalentidev.azurecr.io/talenti/model-service-1@sha256:<64-hex>`
   - `acrtalentidev.azurecr.io/talenti/model-service-2@sha256:<64-hex>`
2. In GitHub -> main repo -> Settings -> Environments -> `dev`, set variables:
   - `MODEL1_IMAGE_REF=<model1 digest ref>`
   - `MODEL2_IMAGE_REF=<model2 digest ref>`
3. Trigger `deploy-dev` workflow (manual or matching push).
4. Verify deployment:
   - Backend health endpoint returns 200.
   - `backend-worker` is running and `background_jobs` are not stuck in `pending`.
   - Container Apps `ca-model1-dev` and `ca-model2-dev` revisions reference the pinned digest images.

## GitHub Environment Variables

Set these variables in the GitHub `dev` environment:

- `AZURE_LOCATION`
- `AZURE_RESOURCE_GROUP`
- `ACR_NAME`
- `KEY_VAULT_NAME`
- `STATIC_WEB_APP_NAME`
- `BACKEND_APP`
- `BACKEND_WORKER_APP`
- `MODEL1_APP`
- `MODEL2_APP`
- `ACS_WORKER_APP`
- `ALERT_EMAIL_ADDRESS`
- `MODEL1_IMAGE_REF`
- `MODEL2_IMAGE_REF`

Set these secrets in the GitHub `dev` environment:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `POSTGRES_ADMIN_PASSWORD`
- `BACKEND_DATABASE_URL`
- `JWT_SECRET`

## Migration

- Backend runs Alembic `upgrade head` automatically at startup and fails fast on migration errors.
- Keep `python backend/scripts/run_migrations.py` in the deployment pipeline as a pre-deploy safety check.
- If `backend-worker` is not deployed or unhealthy, interview orchestration and async file/scoring jobs will remain queued in `background_jobs`.
