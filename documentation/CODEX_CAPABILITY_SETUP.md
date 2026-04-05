# Codex Capability Setup

Use this guide to give Codex enough local and cloud access to manage Talenti across GitHub, Azure, and the separate model repositories.

## Canonical Repositories

- Main app: `git@github.com:dcava30/Talenti_MVP.git`
- `model-service-1`: `git@github.com:dcava30/Talenti_model_culture.git`
- `model-service-2`: `git@github.com:dcava30/Talenti_model_skills.git`

Local workspace mapping:

- `model-service-1` = culture model
- `model-service-2` = skills model

## Local Prerequisites

- Git
- GitHub CLI (`gh`)
- Azure CLI (`az`)
- Docker
- SSH key: `C:\Users\Declan\.ssh\id_ed25519_personal`

Authenticate locally:

```powershell
gh auth login --web --git-protocol ssh
az login
az account set --subscription ea9dd497-9980-40a6-9e63-024f2c54e2d6
```

The setup scripts resolve the tenant id from the active Azure subscription, so you do not need to pass it manually unless Azure CLI cannot determine it.

Normalize the main repo remote to SSH if this clone was originally set up over HTTPS:

```powershell
.\scripts\normalize-git-remotes.ps1 -EnsureMainUpstream
```

## Clone and Verify the Model Repositories

From the main repo root:

```powershell
.\scripts\setup-model-repos.ps1 -SshKeyPath C:\Users\Declan\.ssh\id_ed25519_personal -Fetch
```

This script:

- verifies GitHub SSH access
- clones `model-service-1` and `model-service-2` if they are missing
- verifies their `origin` remotes if they already exist
- optionally refreshes them with `git fetch --prune --tags origin`

## Create GitHub Environments and Azure OIDC Access

Create the GitHub `dev`, `pr-dev`, `uat`, and `prod` environments plus one Azure app registration per environment:

```powershell
.\scripts\setup-deployment-access.ps1 `
  -SubscriptionId ea9dd497-9980-40a6-9e63-024f2c54e2d6 `
  -AlertEmailAddress you@example.com
```

This script:

- creates or updates GitHub environments `dev`, `pr-dev`, `uat`, and `prod`
- creates one Azure app registration and service principal per environment
- creates federated credentials with GitHub environment subjects:
  - `repo:dcava30/Talenti_MVP:environment:dev`
  - `repo:dcava30/Talenti_MVP:environment:pr-dev`
  - `repo:dcava30/Talenti_MVP:environment:uat`
  - `repo:dcava30/Talenti_MVP:environment:prod`
- assigns `Contributor` and `User Access Administrator` on the matching resource group
- stores the GitHub environment variables and OIDC secrets required by the workflows

If you already know environment-specific runtime secrets, configure one environment at a time:

```powershell
.\scripts\setup-deployment-access.ps1 `
  -SubscriptionId ea9dd497-9980-40a6-9e63-024f2c54e2d6 `
  -EnvironmentNames dev `
  -AlertEmailAddress you@example.com `
  -PostgresAdminPassword "<password>" `
  -BackendDatabaseUrl "<database-url>" `
  -JwtSecret "<jwt-secret>" `
  -Model1ImageRef "acrtalentidev.azurecr.io/talenti/model-service-1@sha256:<digest>" `
  -Model2ImageRef "acrtalentidev.azurecr.io/talenti/model-service-2@sha256:<digest>"
```

## First-Time DEV Bootstrap

After local auth is in place, bootstrap DEV runtime resources:

```powershell
.\scripts\day1-dev-deploy.ps1 `
  -SubscriptionId ea9dd497-9980-40a6-9e63-024f2c54e2d6 `
  -AlertEmailAddress you@example.com `
  -Model1ImageRef "acrtalentidev.azurecr.io/talenti/model-service-1@sha256:<digest>" `
  -Model2ImageRef "acrtalentidev.azurecr.io/talenti/model-service-2@sha256:<digest>"
```

The DEV bootstrap script now:

- deploys `infra/dev/main.bicep`
- creates ACS, Speech, and Azure OpenAI resources if missing
- stores runtime secrets in Key Vault
- wires the Container Apps
- updates GitHub environment `dev` using environment-scoped secrets and OIDC

The `pr-dev` GitHub environment reuses the shared dev Azure resource group for ephemeral PR validation. It needs its own OIDC identity because GitHub environment subjects are environment-specific.

## Local Verification

Useful checks after setup:

```powershell
.\scripts\verify-codex-capability.ps1 `
  -SubscriptionId ea9dd497-9980-40a6-9e63-024f2c54e2d6 `
  -SshKeyPath C:\Users\Declan\.ssh\id_ed25519_personal
```

Then start the local stack:

```powershell
.\scripts\start-local.ps1
```
