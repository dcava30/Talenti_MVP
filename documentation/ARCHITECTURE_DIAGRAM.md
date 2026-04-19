# Talenti Architecture Views

> **Note:** For the canonical auditor-ready architecture documentation, see [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md). This diagram document is retained as a supporting visual reference and remains accurate.
>
> **Rendered output:** This file is the Mermaid source. If your Markdown viewer does not render Mermaid, generate the rendered outputs with `npm run docs:arch:html` or `npm run docs:arch:pdf`.

This document refreshes the Talenti diagrams around the Azure-first platform that is now encoded in the repository. It separates the system into four views:

- high-level system design
- runtime topology
- environment and infrastructure layout
- delivery and promotion flow

## Source Of Truth

These diagrams are based on:

- [`infra/modules/platform.bicep`](../infra/modules/platform.bicep)
- [`infra/dev/main.bicep`](../infra/dev/main.bicep)
- [`infra/uat/main.bicep`](../infra/uat/main.bicep)
- [`infra/prod/main.bicep`](../infra/prod/main.bicep)
- [`pr-fast-quality.yml`](../.github/workflows/pr-fast-quality.yml)
- [`pr-security-iac.yml`](../.github/workflows/pr-security-iac.yml)
- [`pr-ephemeral-deploy.yml`](../.github/workflows/pr-ephemeral-deploy.yml)
- [`ci-main.yml`](../.github/workflows/ci-main.yml)
- [`deploy-dev.yml`](../.github/workflows/deploy-dev.yml)
- [`release.yml`](../.github/workflows/release.yml)
- [`promote-release.yml`](../.github/workflows/promote-release.yml)
- [`backend/app/main.py`](../backend/app/main.py)
- [`backend/app/services/job_handlers.py`](../backend/app/services/job_handlers.py)

The older local `docker-compose` setup remains useful for development, but it is no longer the primary source of truth for deployed architecture.

## 1. High-Level System Design

This is the quickest view to use when we want to explain the platform in one diagram.

```mermaid
flowchart TB
    recruiter["Recruiters and hiring teams"]
    candidate["Candidates"]

    subgraph edge["Frontend and edge"]
        hosting["Frontend hosting<br/>DEV: Azure Static Web Apps<br/>UAT/PROD: Azure Front Door + Storage static website"]
        spa["React + Vite SPA<br/>recruiter portal<br/>candidate portal<br/>live interview UI"]
        browser["Browser runtime<br/>ACS calling, speech, avatar,<br/>file uploads"]
    end

    subgraph app["Application services"]
        backend["FastAPI backend API<br/>auth, invitations, interviews,<br/>scoring, storage URLs, reporting"]
        worker["backend-worker<br/>resume parsing, profile prefill,<br/>invite prep, auto-scoring"]
        acsworker["python-acs-service<br/>call automation and recording"]
    end

    subgraph ai["AI and model layer"]
        openai["Azure OpenAI<br/>AI interviewer chat"]
        model1["model-service-1<br/>culture and communication scoring"]
        model2["model-service-2<br/>technical and skills scoring"]
        speech["Azure Speech + avatar relay"]
        acs["Azure Communication Services"]
    end

    subgraph data["Data, storage, and operations"]
        pg["Azure Database for PostgreSQL"]
        blob["Azure Blob Storage"]
        kv["Azure Key Vault"]
        obs["Application Insights<br/>Log Analytics<br/>Azure Monitor alerts"]
    end

    recruiter --> hosting
    candidate --> hosting
    hosting --> spa
    candidate --> browser

    spa --> backend
    browser --> backend

    backend --> pg
    backend --> blob
    backend -. secret refs .-> kv
    worker --> pg
    worker --> blob
    worker -. secret refs .-> kv
    acsworker --> blob
    acsworker -. secret refs .-> kv

    backend --> openai
    backend --> model1
    backend --> model2
    backend --> speech
    backend --> acs
    backend --> acsworker

    worker --> model1
    worker --> model2
    worker --> acsworker
    acsworker --> acs

    browser --> speech
    browser --> acs

    obs -. monitors .-> backend
    obs -. monitors .-> worker
    obs -. monitors .-> model1
    obs -. monitors .-> model2
    obs -. monitors .-> acsworker
```

### System Design Notes

- The frontend is a single SPA, but the hosting pattern changes by environment: Static Web Apps in `dev`, Storage static website plus Front Door in `uat` and `prod`.
- The backend is the control plane for platform state, while `backend-worker` handles database-backed async orchestration.
- The model services remain separate runtime resources so scoring can evolve independently from the main backend.
- Azure Speech, avatar features, and Azure Communication Services are used both through backend-issued tokens and direct browser sessions.
- PostgreSQL, Blob Storage, Key Vault, and Azure-native monitoring form the shared platform foundation across all environments.

## 2. Runtime Topology

```mermaid
flowchart LR
    recruiter["Recruiter / hiring team"]
    candidate["Candidate"]

    subgraph experience["Frontend experience"]
        spa["React + Vite SPA<br/>recruiter portal, candidate portal,<br/>live interview, reporting"]
        browser["Browser runtime<br/>ACS Calling SDK<br/>Azure Speech SDK<br/>avatar renderer<br/>browser speech fallback"]
    end

    subgraph apps["Azure Container Apps environment"]
        backend["backend API<br/>FastAPI control plane<br/>public ingress"]
        worker["backend-worker<br/>claims jobs from PostgreSQL<br/>and persists async results"]
        model1["model-service-1<br/>culture / communication scoring<br/>internal ingress"]
        model2["model-service-2<br/>technical / skills scoring<br/>internal ingress"]
        acsworker["python-acs-service<br/>call automation and recording<br/>internal ingress"]
    end

    subgraph state["State, files, and secrets"]
        pg["Azure Database for PostgreSQL<br/>core entities<br/>background_jobs<br/>domain_events"]
        blob["Azure Blob Storage<br/>resume uploads, CVs,<br/>recordings, artifacts"]
        kv["Azure Key Vault<br/>runtime secrets"]
    end

    subgraph azure["Azure service integrations"]
        acs["Azure Communication Services<br/>identity, calling, webhook events"]
        speech["Azure Speech + avatar relay<br/>speech tokens, STT, TTS,<br/>avatar session setup"]
        openai["Azure OpenAI<br/>AI interviewer chat"]
    end

    recruiter --> spa
    candidate --> spa
    candidate --> browser

    spa --> backend
    browser --> backend

    backend -->|auth, CRUD, invitation state,<br/>interview lifecycle| pg
    backend -->|enqueue jobs + domain events| pg
    worker -->|claim jobs + persist outputs| pg

    backend -->|generate SAS upload URLs| blob
    spa -->|direct upload/download via SAS| blob
    worker -->|resume and recording IO| blob
    acsworker -->|recordings| blob

    backend -->|sync scoring| model1
    backend -->|sync scoring| model2
    worker -->|auto scoring| model1
    worker -->|auto scoring| model2

    backend -->|AI interviewer prompts| openai
    backend -->|ACS token issuance| acs
    backend -->|speech token issuance| speech
    browser -->|live call media| acs
    browser -->|speech + avatar session| speech

    backend -->|call automation requests| acsworker
    worker -->|server-managed call and recording orchestration| acsworker
    acs -->|webhook events| backend
    acsworker -->|worker-events callback| backend

    backend -. secret refs .-> kv
    worker -. secret refs .-> kv
    acsworker -. secret refs .-> kv
```

### Runtime Notes

- Only `backend` has public ingress in the deployed Container Apps environment.
- `backend-worker`, `model-service-1`, `model-service-2`, and `python-acs-service` are internal services.
- Async orchestration is database-backed through `background_jobs` and `domain_events`; there is no separate queue broker in the current platform.
- Blob Storage is the canonical deployed upload and recording store. `/api/v1/candidates/cv` remains only as a local fallback when blob configuration is absent.
- The backend can score interviews synchronously through `/api/v1/scoring/analyze`, while `backend-worker` can also run asynchronous scoring when `AUTO_SCORE_INTERVIEWS` is enabled.

## 3. Environment And Infrastructure Topology

```mermaid
flowchart TB
    subgraph github["GitHub control plane"]
        envs["GitHub environments<br/>dev, uat, prod<br/>vars + secrets"]
        infrawf["infra-dev / infra-uat / infra-prod"]
        deploydev["deploy-dev"]
        promote["promote-release"]
    end

    oidc["OIDC federation<br/>azure/login"]
    module["Shared Bicep platform module<br/>infra/modules/platform.bicep"]

    envs --> infrawf
    envs --> deploydev
    envs --> promote
    infrawf --> oidc
    deploydev --> oidc
    promote --> oidc
    oidc --> module

    subgraph dev["DEV resource group"]
        devedge["Frontend hosting<br/>Azure Static Web Apps"]
        devapps["Azure Container Apps<br/>backend<br/>backend-worker<br/>model1<br/>model2<br/>acs-worker"]
        devcore["Azure Container Registry<br/>Key Vault<br/>Storage account<br/>PostgreSQL"]
        devobs["Log Analytics<br/>Application Insights<br/>synthetic tests and alerts"]
    end

    subgraph uat["UAT resource group"]
        uatedge["Frontend hosting<br/>Storage static website<br/>Azure Front Door Standard<br/>WAF IP allowlist"]
        uatapps["Azure Container Apps<br/>backend<br/>backend-worker<br/>model1<br/>model2<br/>acs-worker"]
        uatcore["Azure Container Registry<br/>Key Vault<br/>Storage account<br/>PostgreSQL"]
        uatobs["Log Analytics<br/>Application Insights<br/>synthetic tests and alerts"]
    end

    subgraph prod["PROD resource group"]
        prodedge["Frontend hosting<br/>Storage static website<br/>Azure Front Door Standard"]
        prodapps["Azure Container Apps<br/>backend<br/>backend-worker<br/>model1<br/>model2<br/>acs-worker"]
        prodcore["Azure Container Registry<br/>Key Vault<br/>Storage account<br/>PostgreSQL"]
        prodobs["Log Analytics<br/>Application Insights<br/>synthetic tests and alerts"]
    end

    module --> devedge
    module --> devapps
    module --> devcore
    module --> devobs

    module --> uatedge
    module --> uatapps
    module --> uatcore
    module --> uatobs

    module --> prodedge
    module --> prodapps
    module --> prodcore
    module --> prodobs
```

### Environment Notes

- Each stage is a separate Azure resource group with its own Container Apps environment, ACR, Key Vault, Storage account, PostgreSQL server, Log Analytics workspace, Application Insights component, and alert rules.
- `dev` serves the SPA from Azure Static Web Apps.
- `uat` and `prod` serve the SPA from Azure Storage static website hosting behind Azure Front Door Standard.
- `uat` adds a Front Door WAF IP allowlist so promotion and smoke checks must run from an allowlisted network.
- After infra deployment, the workflows assign `AcrPull` and `Key Vault Secrets User` to the five Container Apps so images and secret references work without embedded credentials.

## 4. Delivery And Promotion Architecture

```mermaid
flowchart LR
    pr["Feature PR"] --> fast["pr-fast-quality<br/>lint, tests, build, migrations"]
    pr --> sec["pr-security-iac<br/>CodeQL, CVE, IaC and image scans"]
    pr --> eph["pr-ephemeral-deploy<br/>isolated PR runtime + smoke + teardown"]
    fast --> main["Merge to main"]
    sec --> main
    eph --> main

    main --> cimai["ci-main<br/>build, scan, sign, attest"]
    cimai --> devacr["DEV ACR"]
    cimai --> evidence["SBOM + provenance evidence"]

    main --> infrawf["infra-dev<br/>validate + what-if + deploy"]

    cimai --> deploydev["deploy-dev"]
    deploydev --> modelrefs["Use pinned model digests<br/>from GitHub dev environment"]
    deploydev --> infragate["Require infra-dev success<br/>for infra-touching SHAs"]
    infrawf --> infragate
    deploydev --> migdev["Run migrations once"]
    deploydev --> devapps["Update DEV Container Apps"]
    deploydev --> devfront["Deploy frontend to Static Web Apps"]
    deploydev --> devsmoke["DEV smoke tests"]

    deploydev --> release["release<br/>release-please"]
    release --> tag["Git tag + GitHub Release"]
    tag --> assets["Release assets<br/>release-manifest.json<br/>frontend-dist.tgz"]

    assets --> uatpromo["Automatic UAT promotion<br/>self-hosted allowlisted runner"]
    assets --> prodpromo["Manual PROD promotion<br/>workflow_dispatch by release tag"]

    uatpromo --> import["Import pinned digests into target ACR"]
    prodpromo --> import
    import --> mig["Run migrations"]
    mig --> targetapps["Update target Container Apps"]
    targetapps --> web["Publish frontend-dist.tgz<br/>to Storage static website"]
    web --> purge["Purge Azure Front Door cache"]
    purge --> origins["Update backend ALLOWED_ORIGINS"]
    origins --> smoke["Environment smoke tests"]
```

### Pipeline Notes

- Required PR gates are `pr-fast-quality`, `pr-security-iac`, and `pr-ephemeral-deploy`.
- `ci-main` builds backend and ACS worker images once per `main` SHA, then scans, signs, and attests those immutable artifacts.
- `deploy-dev` deploys immutable backend/ACS digests for the source SHA and enforces `infra-dev` success for infra-touching commits.
- `release.yml` is triggered only after successful `deploy-dev` on `main`, so release creation starts after DEV deployment validation.
- `release-manifest.json` is the promotion handoff. It captures backend, ACS worker, and model image digests plus the frontend source SHA.
- `promote-release.yml` does not rebuild application artifacts for UAT or PROD. It imports pinned images into the target ACR, verifies signatures, and reuses the packaged frontend artifact.
- UAT is auto-promoted from a published release. PROD is promoted manually by release tag.

## Summary

The platform is now best understood as an Azure Container Apps control plane with PostgreSQL-backed orchestration, Blob-backed file storage, and GitHub Actions-managed promotion between isolated Azure environments. The key architectural distinction from the older diagrams is that deployment automation, environment isolation, and immutable release promotion are now first-class parts of the system design, not side notes.
