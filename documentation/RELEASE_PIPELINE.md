# Release Pipeline

Talenti now uses a trunk-based release model on `main`.

## Branching and Merge Rules

- All feature and fix PRs target `main`.
- PR titles must follow Conventional Commits, for example:
  - `feat(api): add release manifest upload`
  - `fix(worker): emit queue metrics for alerting`
- Merge with squash so the PR title becomes the release note source.
- Configure branch protection in GitHub so:
  - `pr-fast-quality`, `pr-security-iac`, and `pr-ephemeral-deploy` are required before merge
  - squash merge is allowed
  - direct pushes to `main` are blocked
- Configure GitHub Actions workflow permissions so:
  - default workflow permissions are `Read`
  - `Allow GitHub Actions to create and approve pull requests` is disabled

## Workflows

- `pr-fast-quality.yml`
  - Runs on pull requests to `main`
  - Enforces Conventional Commit PR titles
  - Runs frontend lint/test/build, backend tests, ACS tests, migration execution checks, and coverage gates
- `pr-security-iac.yml`
  - Runs on pull requests to `main`
  - Runs CodeQL, secret scanning, dependency auditing, container scanning, and Bicep/IaC policy checks
- `pr-ephemeral-deploy.yml`
  - Runs on pull requests to `main` from internal branches
  - Provisions ephemeral PR runtime resources, runs migrations and API smoke tests, then tears everything down
- `ci-main.yml`
  - Runs on pushes to `main`
  - Builds backend/ACS images once per SHA
  - Publishes immutable image digests
  - Generates SBOMs, vulnerability scan evidence, signatures, and provenance attestations
- `deploy-dev.yml`
  - Runs after a successful `ci-main` workflow on `main`
  - Manual dispatch requires `source_sha` (full 40-character SHA on `main`)
  - Manual dispatch validates a successful `ci-main` run exists for that SHA before deployment
  - Resolves immutable backend/ACS image digests from ACR for the commit SHA
  - Validates pinned model digests
  - Requires matching `infra-dev` success when infra files changed in that commit
  - Runs migrations once
  - Deploys DEV backend, worker, ACS worker, and frontend
  - Smoke-checks backend `/health` and the DEV Static Web App
- `release.yml`
  - Runs after successful `deploy-dev` on `main` (or manual dispatch)
  - Manual dispatch requires `source_sha` and validates that SHA was already deployed to `dev`
  - Uses `release-please` with repo-root `VERSION` and `CHANGELOG.md`
  - Creates or updates the release PR
  - When the release PR is merged and a tag is created, uploads:
    - `release-manifest.json`
    - `frontend-dist.tgz`
- `promote-release.yml`
  - Auto-promotes published releases to UAT
  - Allows manual promotion to UAT or PROD by release tag
  - Imports immutable image digests into the target ACR when needed
  - Verifies backend/ACS release signatures before deployment
  - Reuses the release frontend artifact instead of rebuilding it
  - Publishes UAT/PROD frontend assets to Azure Storage static website hosting
  - Purges Azure Front Door Standard cache after upload
  - Runs UAT on a self-hosted runner inside the allowlisted network
  - Optionally verifies model image signatures when `MODEL1_COSIGN_IDENTITY_REGEX` and `MODEL2_COSIGN_IDENTITY_REGEX` are set in the target environment

- Workflow security baseline
  - Third-party GitHub Actions are pinned to immutable commit SHAs.
  - Release tooling binaries (Syft, Trivy, Hadolint, Gitleaks) are downloaded at fixed versions with checksum verification.

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
- `ALERT_EMAIL_ADDRESS`
- `STATIC_WEB_APP_NAME` in `dev` only
- `MODEL1_IMAGE_REF` and `MODEL2_IMAGE_REF` in `dev` only
- `FRONTEND_STORAGE_ACCOUNT` in `uat` and `prod`
- `FRONT_DOOR_PROFILE_NAME` in `uat` and `prod`
- `FRONT_DOOR_ENDPOINT_NAME` in `uat` and `prod`
- `FRONTEND_ALLOWED_CIDRS` in `uat` only, as a JSON array string such as `["203.0.113.0/24"]`

Store these secrets per environment:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `POSTGRES_ADMIN_PASSWORD`
- `BACKEND_DATABASE_URL`
- `JWT_SECRET`

Optional repository or environment secret:

- `RELEASE_PLEASE_TOKEN`

Additional `dev` variables for the PR ephemeral deploy gate:

- `CONTAINER_ENV_NAME` (defaults to `cae-talenti-dev-aue` if omitted)
- `POSTGRES_SERVER_NAME` (defaults to `psql-talenti-dev-aue` if omitted)
- `STORAGE_ACCOUNT_NAME` (defaults to `sttalentidevaue` if omitted)

Use a PAT for `RELEASE_PLEASE_TOKEN` if you want downstream workflows to respond to release publication automatically. Without it, manual promotion still works.
The repository-level GitHub Actions workflow permissions above are still required so `release.yml` can create or update the release PR with `release-please`.

To create the environments and seed their OIDC secrets from the command line, use:

```powershell
.\scripts\setup-deployment-access.ps1 -SubscriptionId <sub-id> -AlertEmailAddress <team-email>
```

That setup script also configures the repository GitHub Actions workflow permission model needed by [`release.yml`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/.github/workflows/release.yml).

The Azure federated credential subject must match the GitHub environment form used by the workflows:

- `repo:dcava30/Talenti_MVP:environment:dev`
- `repo:dcava30/Talenti_MVP:environment:uat`
- `repo:dcava30/Talenti_MVP:environment:prod`

## Promotion and Rollback

- UAT is promoted from a published GitHub Release.
- PROD is promoted manually by release tag.
- Promotion always uses the manifest digests captured at release time.
- UAT frontend traffic is restricted at Azure Front Door Standard with an IP allowlist custom WAF rule.
- UAT promotion and frontend smoke checks require a self-hosted runner with the `uat` label on an allowlisted office/VPN network.
- Roll back by rerunning `promote-release.yml` with an older `release_tag`.

## Local Pre-Commit Gate

To catch workflow failures before pushing:

1. Install the tracked git hook:
   - `npm run hooks:install`
2. Default commit hook runs:
   - `scripts/run-pre-commit.ps1 -Scope staged -Profile fast`
3. Run full local parity checks manually when needed:
   - `npm run precommit:full`
4. Optional tools used by `full` profile:
   - Docker (for gitleaks, hadolint, trivy image scans)
   - Azure CLI + Bicep (for infra compile checks)
5. Every run writes a timestamped log:
   - `.tmp/precommit/precommit-YYYYMMDD-HHMMSS.log`
6. Failures end with a summary that includes:
   - the failed step
   - why that step is a gate
   - targeted remediation hints

`fast` mirrors `pr-fast-quality` behavior for touched components.
`full` adds local equivalents of `pr-security-iac` checks (excluding CodeQL, which remains CI-only).

## Environment Protection Notes

- `dev` should use a deployment branch policy restricted to `main`.
- `uat` and `prod` should use required reviewers when the billing plan supports environment reviewer rules.
- If reviewer protection is not supported on the current plan, keep `can_admins_bypass=false` and enforce approvals via repository process until the plan is upgraded.
