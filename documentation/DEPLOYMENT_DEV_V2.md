# Dev Deployment v3 (Current Lean Dev State)

## Topology

- Public:
  - Frontend (`Azure Static Web Apps` in `eastasia`)
  - Backend API (`Azure Container Apps` with external ingress)
- Local/on-demand:
  - `backend-worker` (`python -m app.worker_main`)
  - `model-service-1`
  - `model-service-2`
  - `acs-worker` (`python-acs-service`)

Current public dev URLs:

- Frontend: `https://witty-bush-06941cf00.4.azurestaticapps.net`
- Backend: `https://ca-backend-dev.delightfulground-722f8c60.australiaeast.azurecontainerapps.io`

## Database

- Backend is the only system-of-record.
- Use PostgreSQL database: `talenti_backend_dev`.
- Local worker and ACS worker both use backend-managed state; neither requires a separate database.

## Required Backend App Settings

- `DATABASE_URL`
- `JWT_SECRET`
- `ALLOWED_ORIGINS`
- `MODEL_SERVICE_1_URL` (blank in the lean cloud baseline unless local scoring is in use)
- `MODEL_SERVICE_2_URL` (blank in the lean cloud baseline unless local scoring is in use)
- `ACS_WORKER_URL` (blank in the lean cloud baseline unless local ACS worker is in use)
- `ACS_WORKER_SHARED_SECRET` (only needed when the local ACS worker is in use)
- `PUBLIC_BASE_URL`
- `ENABLE_LIVE_SCORING=false`
- `ENABLE_ACS_CALL_AUTOMATION=false`
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

## Local Worker Settings

- Use [`start-dev-worker-local.ps1`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/scripts/start-dev-worker-local.ps1) to export the Azure-backed env file and start `backend-worker` locally against the shared DEV PostgreSQL and Storage resources.
- Leave `AUTO_SCORE_INTERVIEWS=false` for the lean cloud baseline; opt into local model/ACS runtime only when needed.
- Without the local worker, queued jobs remain pending in PostgreSQL and any scoring or call-automation flows that depend on the local services return explicit `503` responses.

## CI/CD

- `pr-validate.yml`: validates Conventional Commit PR titles and runs CI for PRs to `main`.
- `ci.yml`: runs on pushes to `main` and is the gate for DEV deployment.
- `infra-dev.yml`: deploys the lean DEV Bicep infra with OIDC.
- `deploy-dev.yml`:
  - Runs after successful `ci` on `main`.
  - Builds/pushes the backend image from this repo.
  - Preflight-checks the resource group, ACR, Key Vault, backend Container App, and Static Web App.
  - Runs backend migrations once, deploys the backend, reapplies the raw Azure runtime URLs, deploys the frontend, and smoke-checks backend/frontend availability through the Azure-generated public hostnames.
- `release.yml`:
  - Uses `release-please` to manage repo-root `VERSION`, `CHANGELOG.md`, and GitHub Releases.
  - Uploads `release-manifest.json` and `frontend-dist.tgz` for promotion.
- `promote-release.yml`:
  - Stays parked until `ENABLE_NON_DEV_DEPLOYS=true` for the target environment.
  - Later promotes the released digests and frontend artifact to UAT/PROD without rebuilding them.

Seed the GitHub `dev` environment and Azure OIDC identity with:

```powershell
.\scripts\setup-deployment-access.ps1 -SubscriptionId <sub-id> -EnvironmentNames dev -DevFrontendOrigin https://witty-bush-06941cf00.4.azurestaticapps.net -DevApiBaseUrl https://ca-backend-dev.delightfulground-722f8c60.australiaeast.azurecontainerapps.io
```

For first-time DEV runtime bootstrap, use:

```powershell
.\scripts\day1-dev-deploy.ps1 -SubscriptionId <sub-id> -StaticWebAppLocation eastasia -FrontendOrigin https://witty-bush-06941cf00.4.azurestaticapps.net -ApiBaseUrl https://ca-backend-dev.delightfulground-722f8c60.australiaeast.azurecontainerapps.io
```

Current live dev does not use Cloudflare or custom hostnames. If branded hostnames are introduced later, treat that as an additional edge setup step rather than part of the default dev runbook.

## GitHub Environment Variables

Set these variables in the GitHub `dev` environment:

- `AZURE_LOCATION`
- `AZURE_RESOURCE_GROUP`
- `ACR_NAME`
- `KEY_VAULT_NAME`
- `STATIC_WEB_APP_NAME`
- `BACKEND_APP`
- `DEV_FRONTEND_ORIGIN`
- `DEV_API_BASE_URL`
- `BACKEND_ALLOWED_CIDRS`

Current live values are:

- `DEV_FRONTEND_ORIGIN=https://witty-bush-06941cf00.4.azurestaticapps.net`
- `DEV_API_BASE_URL=https://ca-backend-dev.delightfulground-722f8c60.australiaeast.azurecontainerapps.io`
- `BACKEND_ALLOWED_CIDRS=[]`

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
- In the lean cloud footprint, queued async jobs remain pending until a developer starts the local worker with [`start-dev-worker-local.ps1`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/scripts/start-dev-worker-local.ps1).
