# Talenti Architecture Views

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
        hosting["Frontend hosting<br/>Current: Azure Static Web Apps in DEV<br/>Future: Storage static website<br/>plus App Gateway or Front Door in UAT/PROD"]
        spa["React + Vite SPA<br/>recruiter portal<br/>candidate portal<br/>live interview UI"]
        browser["Browser runtime<br/>ACS calling, speech, avatar,<br/>file uploads"]
    end

    subgraph app["Application services"]
        backend["FastAPI backend API<br/>auth, invitations, interviews,<br/>scoring, storage URLs, reporting"]
        worker["backend-worker<br/>local/on-demand async processing"]
        acsworker["python-acs-service<br/>local/on-demand call automation"]
    end

    subgraph ai["AI and model layer"]
        openai["Azure OpenAI<br/>AI interviewer chat"]
        model1["model-service-1<br/>local/on-demand culture scoring"]
        model2["model-service-2<br/>local/on-demand skills scoring"]
        speech["Azure Speech + avatar relay"]
        acs["Azure Communication Services"]
    end

    subgraph data["Data, storage, and operations"]
        pg["Azure Database for PostgreSQL"]
        blob["Azure Blob Storage"]
        kv["Azure Key Vault"]
        obs["Application Insights<br/>Log Analytics<br/>minimal DEV telemetry"]
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

- The currently active cloud environment is `dev`, exposed on raw Azure hostnames and hosted on Azure Static Web Apps plus one backend Container App.
- The backend is the cloud control plane for platform state, while `backend-worker` now runs locally/on demand when developers need queued async orchestration.
- The model services remain separate runtimes, but they are intentionally local/on-demand in the current cost-controlled phase.
- Azure Speech, avatar features, and Azure Communication Services are used both through backend-issued tokens and direct browser sessions.
- PostgreSQL, Blob Storage, Key Vault, and Azure-native monitoring form the shared platform foundation, with only the `dev` instance active today.

## 2. Runtime Topology

```mermaid
flowchart LR
    recruiter["Recruiter / hiring team"]
    candidate["Candidate"]

    subgraph experience["Frontend experience"]
        spa["React + Vite SPA<br/>recruiter portal, candidate portal,<br/>live interview, reporting"]
        browser["Browser runtime<br/>ACS Calling SDK<br/>Azure Speech SDK<br/>avatar renderer<br/>browser speech fallback"]
    end

    subgraph apps["Azure active DEV footprint"]
        backend["backend API<br/>FastAPI control plane<br/>public ingress via Azure Container Apps URL"]
    end

    subgraph local["Local/on-demand async services"]
        worker["backend-worker<br/>claims jobs from PostgreSQL<br/>when started locally"]
        model1["model-service-1<br/>culture / communication scoring"]
        model2["model-service-2<br/>technical / skills scoring"]
        acsworker["python-acs-service<br/>call automation and recording"]
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

- Only `backend` is always on in Azure today, exposed on its Azure Container Apps hostname.
- `backend-worker`, `model-service-1`, `model-service-2`, and `python-acs-service` are local/on-demand services in the current dev-only footprint.
- Async orchestration is database-backed through `background_jobs` and `domain_events`; there is no separate queue broker in the current platform.
- Blob Storage is the canonical deployed upload and recording store. `/api/v1/candidates/cv` remains only as a local fallback when blob configuration is absent.
- Lean cloud dev keeps live scoring and call automation disabled by default so missing local services fail fast with explicit `503` responses.

## 3. Environment And Infrastructure Topology

```mermaid
flowchart TB
    subgraph github["GitHub control plane"]
        envs["GitHub environments<br/>dev active<br/>uat/prod parked by default<br/>vars + secrets"]
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
        devapps["Azure Container Apps<br/>backend only"]
        devcore["Azure Container Registry<br/>Key Vault<br/>Storage account<br/>PostgreSQL"]
        devobs["Log Analytics<br/>Application Insights<br/>minimal telemetry"]
    end

    subgraph uat["UAT resource group"]
        uatedge["Future-state edge<br/>Storage static website<br/>App Gateway or Front Door"]
        uatapps["Parked future-state app stack"]
        uatcore["No active Azure spend intended"]
        uatobs["No active telemetry until enabled"]
    end

    subgraph prod["PROD resource group"]
        prodedge["Future-state edge<br/>Storage static website<br/>App Gateway or Front Door"]
        prodapps["Parked future-state app stack"]
        prodcore["No active Azure spend intended"]
        prodobs["No active telemetry until enabled"]
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

- `dev` is the only active Azure environment right now: Static Web Apps for the frontend, one backend Container App, PostgreSQL, Storage, Key Vault, ACR, Log Analytics, and Application Insights.
- Current public demo access uses the Azure-generated hostnames rather than Cloudflare or custom domains.
- `uat` and `prod` stay in the repo as future-state templates, but their workflows are gated off by `ENABLE_NON_DEV_DEPLOYS=false` by default.
- The future `uat`/`prod` edge can still use Azure Application Gateway or Azure Front Door when the project is ready to pay for and operate that layer.
- After infra deployment, the workflows assign `AcrPull` and `Key Vault Secrets User` to the active Container App identity so images and secret references work without embedded credentials.

## 4. Delivery And Promotion Architecture

```mermaid
flowchart LR
    pr["Feature PR"] --> validate["pr-validate<br/>title policy, tests, build"]
    validate --> main["Merge to main"]

    main --> ci["ci<br/>frontend + backend checks"]
    main --> release["release<br/>release-please"]

    ci --> deploydev["deploy-dev"]
    deploydev --> build["Build backend image<br/>tag with commit SHA"]
    build --> devacr["DEV ACR"]
    deploydev --> migdev["Run migrations once"]
    deploydev --> devapps["Update DEV backend Container App<br/>with current Azure runtime URLs"]
    deploydev --> devfront["Deploy frontend to Static Web Apps"]
    deploydev --> devsmoke["Smoke test via Azure public URLs"]

    release --> tag["Git tag + GitHub Release"]
    tag --> waitdigests["Wait for backend and acs-worker digests<br/>for the release SHA in DEV ACR"]
    devacr --> waitdigests
    waitdigests --> assets["Release assets<br/>release-manifest.json<br/>frontend-dist.tgz"]

    assets --> uatpromo["Future UAT promotion<br/>gated by ENABLE_NON_DEV_DEPLOYS"]
    assets --> prodpromo["Future PROD promotion<br/>gated by ENABLE_NON_DEV_DEPLOYS"]

    uatpromo --> import["Import pinned digests into target ACR"]
    prodpromo --> import
    import --> mig["Run migrations"]
    mig --> targetapps["Update target Container Apps"]
    targetapps --> web["Publish frontend-dist.tgz<br/>to Storage static website"]
    web --> purge["Purge Front Door cache<br/>when Front Door mode is active"]
    purge --> origins["Update backend ALLOWED_ORIGINS"]
    origins --> smoke["Environment smoke tests"]
```

### Pipeline Notes

- `deploy-dev` now builds and deploys only the backend from this repository, then repoints runtime URLs to the current Azure public hostnames.
- `release.yml` still creates release assets, but non-dev promotion remains parked until `ENABLE_NON_DEV_DEPLOYS` is explicitly enabled for the target environment.
- `release-manifest.json` is the promotion handoff. It captures backend, ACS worker, and model image digests plus the frontend source SHA.
- `promote-release.yml` does not rebuild application artifacts for UAT or PROD. It imports pinned images into the target ACR and reuses the packaged frontend artifact.
- UAT and PROD promotion stay dormant by default in the current dev-only operating mode.

## Summary

The platform is now best understood as a lean Azure dev control plane: Static Web Apps plus a single backend Container App in Azure, PostgreSQL-backed orchestration, Blob-backed file storage, and optional local/on-demand async services. The future multi-environment promotion path is still represented in the repo, but it is intentionally parked until the product is ready for that spend and operating model.
