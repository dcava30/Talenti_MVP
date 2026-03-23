# Release Pipeline

Talenti now uses a trunk-based release model on `main`.

## Branching and Merge Rules

- All feature and fix PRs target `main`.
- PR titles must follow Conventional Commits, for example:
  - `feat(api): add release manifest upload`
  - `fix(worker): emit queue metrics for alerting`
- Merge with squash so the PR title becomes the release note source.
- Configure branch protection in GitHub so:
  - `pr-validate` is required before merge
  - squash merge is allowed
  - direct pushes to `main` are blocked
- Configure GitHub Actions workflow permissions so:
  - default workflow permissions are `Read and write`
  - `Allow GitHub Actions to create and approve pull requests` is enabled

## Workflows

- `pr-validate.yml`
  - Runs on pull requests to `main`
  - Enforces Conventional Commit PR titles
  - Runs frontend lint/test/build and backend tests
- `ci.yml`
  - Runs on pushes to `main`
  - Re-runs frontend lint/test/build and backend tests
- `deploy-dev.yml`
  - Runs after a successful `ci` workflow on `main`
  - Builds the backend image tagged by commit SHA
  - Runs migrations once
  - Deploys the lean DEV footprint: backend plus Static Web Apps
  - Reapplies the current Azure runtime URLs and smoke-checks backend `/health` and the DEV Static Web App through those public hostnames
- `release.yml`
  - Runs on pushes to `main`
  - Uses `release-please` with repo-root `VERSION` and `CHANGELOG.md`
  - Creates or updates the release PR
  - When the release PR is merged and a tag is created, uploads:
    - `release-manifest.json`
    - `frontend-dist.tgz`
- `promote-release.yml`
  - Is gated by `ENABLE_NON_DEV_DEPLOYS`
  - Allows future promotion to UAT or PROD by release tag once non-dev deploys are explicitly enabled
  - Imports immutable image digests into the target ACR when needed
  - Reuses the release frontend artifact instead of rebuilding it
  - Publishes UAT/PROD frontend assets to Azure Storage static website hosting
  - Purges Azure Front Door cache only when Front Door mode is active
  - Runs UAT on a self-hosted runner inside the allowlisted network when the selected WAF policy restricts frontend access

## Release Contract

- Repo-level version source: [`VERSION`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/VERSION)
- Human changelog: [`CHANGELOG.md`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/CHANGELOG.md)
- Git tag format: `vX.Y.Z`
- Machine promotion contract: `release-manifest.json`

`release-manifest.json` contains:

- `version`
- `git_sha`
- `backend_image`
- `acs_worker_image`
- `model1_image`
- `model2_image`
- `frontend_source_sha`
- `created_at`

## GitHub Environment Variables and Secrets

Create `dev`, `uat`, and `prod` GitHub environments with these variables:

- `AZURE_LOCATION`
- `AZURE_RESOURCE_GROUP`
- `ACR_NAME`
- `KEY_VAULT_NAME`
- `BACKEND_APP`
- `BACKEND_WORKER_APP`
- `MODEL1_APP`
- `MODEL2_APP`
- `ACS_WORKER_APP`
- `STATIC_WEB_APP_NAME` in `dev` only
- `DEV_FRONTEND_ORIGIN` in `dev` only
- `DEV_API_BASE_URL` in `dev` only
- `BACKEND_ALLOWED_CIDRS` in `dev` only, currently `[]` in the live raw-Azure demo setup
- `ENABLE_NON_DEV_DEPLOYS`, set to `false` by default and flipped to `true` only when non-dev promotion is approved
- `ALERT_EMAIL_ADDRESS` in `uat` and `prod`
- `FRONTEND_STORAGE_ACCOUNT` in `uat` and `prod`
- `FRONTEND_HOSTING_MODE` in `uat` and `prod`, using `storage-frontdoor` or `storage-appgateway`
- `FRONT_DOOR_PROFILE_NAME` in `uat` and `prod` when `FRONTEND_HOSTING_MODE=storage-frontdoor`
- `FRONT_DOOR_ENDPOINT_NAME` in `uat` and `prod` when `FRONTEND_HOSTING_MODE=storage-frontdoor`
- `APPLICATION_GATEWAY_NAME` in `uat` and `prod` when `FRONTEND_HOSTING_MODE=storage-appgateway`
- `APPLICATION_GATEWAY_PUBLIC_IP_NAME` in `uat` and `prod` when `FRONTEND_HOSTING_MODE=storage-appgateway`
- `FRONTEND_HOST_NAME` in `uat` and `prod` when `FRONTEND_HOSTING_MODE=storage-appgateway`
- `FRONTEND_ALLOWED_CIDRS` in `uat` only, as a JSON array string such as `["203.0.113.0/24"]`

Store these secrets per environment:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `POSTGRES_ADMIN_PASSWORD`
- `BACKEND_DATABASE_URL`
- `JWT_SECRET`
- `APP_GATEWAY_SSL_CERTIFICATE_DATA` in `uat` and `prod` when `FRONTEND_HOSTING_MODE=storage-appgateway`
- `APP_GATEWAY_SSL_CERTIFICATE_PASSWORD` in `uat` and `prod` when `FRONTEND_HOSTING_MODE=storage-appgateway`

Optional repository or environment secret:

- `RELEASE_PLEASE_TOKEN`

Use a PAT for `RELEASE_PLEASE_TOKEN` if you want downstream workflows to respond to release publication automatically. Without it, manual promotion still works.
The repository-level GitHub Actions workflow permissions above are still required so `release.yml` can create or update the release PR with `release-please`.

To create the environments and seed their OIDC secrets from the command line, use:

```powershell
.\scripts\setup-deployment-access.ps1 -SubscriptionId <sub-id> -DevFrontendOrigin https://witty-bush-06941cf00.4.azurestaticapps.net -DevApiBaseUrl https://ca-backend-dev.delightfulground-722f8c60.australiaeast.azurecontainerapps.io
```

That setup script also configures the repository GitHub Actions workflow permission model needed by [`release.yml`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/.github/workflows/release.yml).

The Azure federated credential subject must match the GitHub environment form used by the workflows:

- `repo:dcava30/Talenti_MVP:environment:dev`
- `repo:dcava30/Talenti_MVP:environment:uat`
- `repo:dcava30/Talenti_MVP:environment:prod`

## Promotion and Rollback

- UAT and PROD remain parked by default while `ENABLE_NON_DEV_DEPLOYS=false`.
- Current live dev does not use Cloudflare or custom hostnames; it uses the Azure-generated Static Web Apps and Container Apps URLs.
- Once explicitly enabled, UAT is promoted from a published GitHub Release and PROD is promoted manually by release tag.
- Promotion always uses the manifest digests captured at release time.
- UAT frontend traffic can be restricted at the selected edge with an IP allowlist WAF rule.
- Application Gateway mode requires a custom frontend hostname and TLS certificate because the browser app depends on HTTPS-only media and speech capabilities.
- UAT promotion and frontend smoke checks require a self-hosted runner with the `uat` label on an allowlisted office/VPN network whenever that WAF allowlist is enabled.
- Roll back by rerunning `promote-release.yml` with an older `release_tag`.
