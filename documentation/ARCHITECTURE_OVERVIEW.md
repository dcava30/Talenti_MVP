# Talenti Platform Architecture Overview

> **Version:** 2.0.0
> **Date:** 19 April 2026
> **Status:** Audit-ready — aligned to implementation evidence from repository
> **Supersedes:** Portions of HANDOVER.md, ARCHITECTURE_DIAGRAM.md, and ARCHITECTURE_DECISIONS.md (those documents remain as supporting references)
> **Author:** Architecture audit, April 2026

---

## Table of Contents

1. [Document Purpose and Scope](#1-document-purpose-and-scope)
2. [System Overview](#2-system-overview)
3. [Business Purpose](#3-business-purpose)
4. [Architectural Principles](#4-architectural-principles)
5. [System Context](#5-system-context)
6. [High-Level Architecture](#6-high-level-architecture)
7. [Component Architecture](#7-component-architecture)
8. [Frontend Architecture](#8-frontend-architecture)
9. [Backend Architecture](#9-backend-architecture)
10. [Data Architecture](#10-data-architecture)
11. [Integration Architecture](#11-integration-architecture)
12. [Authentication and Authorization](#12-authentication-and-authorization)
13. [Security Architecture and Controls](#13-security-architecture-and-controls)
14. [Configuration and Secrets Management](#14-configuration-and-secrets-management)
15. [Environments and Deployment Architecture](#15-environments-and-deployment-architecture)
16. [CI/CD and Release Approach](#16-cicd-and-release-approach)
17. [Logging, Monitoring, and Operational Support](#17-logging-monitoring-and-operational-support)
18. [Error Handling and Resilience Considerations](#18-error-handling-and-resilience-considerations)
19. [Architecture Decision Records](#19-architecture-decision-records)
20. [Known Limitations, Technical Debt, and Risks](#20-known-limitations-technical-debt-and-risks)
21. [Assumptions and Unresolved Questions](#21-assumptions-and-unresolved-questions)
22. [Appendix A: Repository Evidence Summary](#appendix-a-repository-evidence-summary)
23. [Appendix B: Audit Findings — Contradictions and Stale Documentation](#appendix-b-audit-findings--contradictions-and-stale-documentation)
24. [Appendix C: Gap Register for Auditors](#appendix-c-gap-register-for-auditors)

---

## 1. Document Purpose and Scope

This document provides a comprehensive, evidence-based description of the Talenti platform architecture as it exists in the repository at the time of writing. It is intended for use by:

- Engineering leadership and platform owners
- Security and compliance auditors
- Delivery and governance stakeholders
- New team members requiring architectural onboarding

Every significant claim in this document is traceable to repository evidence (file paths, configuration, code, infrastructure definitions, CI/CD workflows). Where evidence is incomplete, this is explicitly marked as a gap, assumption, or unresolved item.

**Scope:** This document covers the full Talenti platform including frontend, backend API, background worker, two ML model scoring services, an Azure Communication Services worker, infrastructure-as-code, CI/CD pipelines, data storage, authentication, security controls, and operational patterns.

**Out of scope:** Business requirements documentation, user research, commercial contracts, and Azure subscription-level governance (network security groups, Azure AD tenant configuration, subscription policies).

---

## 2. System Overview

Talenti is a B2B AI-powered interview platform that enables organisations to conduct, record, transcribe, score, and report on candidate interviews. The platform provides:

- A recruiter portal for managing job roles, candidates, applications, and interview results
- A candidate portal for profile management, interview preparation, and live AI-assisted interviews
- Automated dual-scorecard assessment combining culture/behavioural fit and skills/technical fit
- Azure-integrated video calling, recording, speech services, and AI interviewer capabilities
- Bulk resume ingestion with automated parsing and candidate invitation workflows

### Service Inventory

| Service | Technology | Port | Ingress | Repository Path |
|---------|-----------|------|---------|----------------|
| Frontend SPA | React 18 + Vite + Tailwind CSS | 8080 (dev) | Public | `/src/`, `/public/`, `/index.html` |
| Backend API | FastAPI (Python 3.11) | 8000 | Public | `/backend/app/` |
| Backend Worker | Same codebase as Backend API | — | None (internal process) | `/backend/app/worker_main.py` |
| model-service-1 | FastAPI (Python 3.11) | 8001 | Internal | `/model-service-1/` |
| model-service-2 | FastAPI (Python 3.11) | 8002 | Internal | `/model-service-2/` |
| python-acs-service | FastAPI (Python 3.11) | 8000 (internal) | Internal | `/python-acs-service/` |
| PostgreSQL | PostgreSQL 16 | 5432 | Internal | Managed (Azure) / Container (local) |

**Evidence:** Service definitions in `docker-compose.yml`, `infra/modules/platform.bicep`, individual `Dockerfile` files per service, `backend/app/main.py`, `model-service-1/app/main.py`, `model-service-2/app/main.py`, `python-acs-service/app/main.py`.

---

## 3. Business Purpose

Talenti is a hiring assessment platform designed for B2B use by recruiting teams and hiring managers. Its core proposition is:

1. **Structured AI interviews** — candidates interact with an AI interviewer powered by Azure OpenAI, with real-time speech and optional avatar rendering.
2. **Dual-scorecard assessment** — every interview produces two independent scores: culture/behavioural fit (5 canonical dimensions) and skills/technical fit (JD-driven competencies). These scores are never merged into a single composite.
3. **Recruiter decision support** — recruiters receive per-dimension scores, risk flags, confidence levels, and shortlist rankings to inform (not replace) hiring decisions.
4. **Compliance-oriented design** — deterministic scoring rules, audit logging, GDPR data deletion requests, and recording retention controls are built into the platform.

**Evidence:** Frontend pages (`src/lib/pages/`), backend API endpoints (`backend/app/api/`), model service scoring logic (`model-service-1/app/model.py`, `model-service-2/app/model.py`), database models for `audit_log`, `data_deletion_requests`, `recording_retention_days` on organisations.

---

## 4. Architectural Principles

The following principles are evident from the implementation:

| Principle | Evidence |
|-----------|----------|
| **Separation of scoring concerns** | Culture fit and skills fit are independent services with independent schemas, never merged (ADR-006) |
| **Deterministic decision-making** | ML extracts signals; deterministic rules with configurable thresholds produce all scoring decisions (ADR-007) |
| **Immutable artifact promotion** | Container images are built once on main, signed, attested, and promoted through environments without rebuilding (ADR-009, `ci-main.yml`, `promote-release.yml`) |
| **Database-backed orchestration** | Background jobs use a PostgreSQL table with polling rather than an external message broker (ADR-005, `background_jobs` model) |
| **Azure-first infrastructure** | All cloud services are Azure-native: Container Apps, PostgreSQL Flexible Server, Blob Storage, Communication Services, Speech, OpenAI, Key Vault, Front Door (Bicep templates in `infra/`) |
| **Internal-only model and worker services** | Only the backend API has public ingress; all other services are internal (`platform.bicep` ingress configuration) |
| **Trunk-based development** | All work merges to `main`; release-please manages versioning (ADR-009, `.release-please-manifest.json`) |

---

## 5. System Context

### External Actors

| Actor | Interaction |
|-------|------------|
| **Recruiters / Hiring Teams** | Access recruiter portal via browser; manage roles, candidates, invitations, and interview results |
| **Candidates** | Access candidate portal via browser; manage profiles, join live interviews, complete practice sessions |
| **Azure Communication Services** | Provides identity tokens, video calling, call recording, and webhook events |
| **Azure OpenAI** | Powers the AI interviewer chat during live interviews |
| **Azure Speech Services** | Provides speech-to-text, text-to-speech, and avatar rendering tokens |
| **Azure Blob Storage** | Stores resumes, CVs, recordings, and upload artifacts |
| **Azure Key Vault** | Stores runtime secrets referenced by Container Apps |
| **GitHub Actions** | CI/CD platform for build, test, scan, sign, deploy, and promote workflows |

### System Boundary

The Talenti platform boundary encompasses:
- The React SPA (served from Azure Static Web Apps or Azure Storage + Front Door)
- The Backend API and Worker (Azure Container Apps)
- The two model services (Azure Container Apps, internal)
- The ACS worker service (Azure Container Apps, internal)
- The PostgreSQL database (Azure Database for PostgreSQL Flexible Server)
- Azure Blob Storage containers (`uploads`, `recordings`)

External to the boundary:
- Azure AD / identity provider for Azure subscription access (not used for application auth)
- Azure Communication Services control plane
- Azure OpenAI service endpoints
- Azure Speech service endpoints
- GitHub (source control and CI/CD)

---

## 6. High-Level Architecture

The system follows a microservices pattern with a central backend API as the control plane.

```
Recruiters / Candidates
        |
        v
  [Frontend SPA]  ------>  [Azure Speech + ACS (browser-direct)]
        |
        v
  [Backend API]  --------->  [Azure OpenAI]
   |    |    |
   |    |    +------------>  [model-service-1: Culture Fit]
   |    |    +------------>  [model-service-2: Skills Fit]
   |    |    +------------>  [python-acs-service: Call Automation]
   |    |
   |    +----------------->  [Azure Blob Storage]
   |
   v
  [PostgreSQL]  <---------  [Backend Worker]
```

### Key Architectural Boundaries

1. **Public ingress:** Only the frontend hosting and backend API are publicly accessible.
2. **Internal services:** Model services, ACS worker, and backend worker are internal only.
3. **Async orchestration:** The backend enqueues jobs in PostgreSQL; the worker claims and processes them.
4. **Dual scoring:** Culture fit and skills fit are structurally independent — different request schemas, different scoring engines, different output formats.

**Evidence:** `infra/modules/platform.bicep` (ingress configuration per Container App), `docker-compose.yml` (network topology), `backend/app/main.py` (router registration), `backend/app/services/ml_client.py` (HTTP client to model services).

---

## 7. Component Architecture

### 7.1 Frontend SPA

| Attribute | Value |
|-----------|-------|
| Framework | React 18, JavaScript (JSX, not TypeScript) |
| Build tool | Vite 6.0.5 |
| Styling | Tailwind CSS 3.4.17 + shadcn/ui (Radix UI primitives) |
| State management | TanStack React Query 5 (server state), React Hook Form + Zod (forms) |
| Routing | React Router DOM 6.30.1 |
| API client | Custom fetch-based HTTP client (`src/api/http.js`) |
| Key integrations | Azure Communication Services Calling SDK, Azure Speech SDK, jsPDF |

**Evidence:** `package.json`, `src/lib/App.jsx`, `src/api/http.js`, `vite.config.js`, `tailwind.config.js`.

### 7.2 Backend API

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI 0.111+ |
| Language | Python 3.11 |
| ORM | SQLAlchemy 2.0 with psycopg 3.2+ |
| Migrations | Alembic 1.13+ (auto-run on startup) |
| Auth | JWT (HS256) via python-jose, bcrypt password hashing |
| Validation | Pydantic 2.8+ |
| API routers | 18 routers, ~91 endpoints |

**Evidence:** `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/security.py`, `backend/app/api/`.

### 7.3 Backend Worker

| Attribute | Value |
|-----------|-------|
| Runtime | Same Python codebase as Backend API |
| Entry point | `python -m app.worker_main` |
| Pattern | Long-running async process polling `background_jobs` table |
| Job types | Resume parsing, auto-scoring, invitation prep, recording processing |
| Retry | Configurable max attempts with retry scheduling |

**Evidence:** `backend/app/worker_main.py`, `backend/app/services/background_jobs.py`, `backend/app/services/job_handlers.py`, `docker-compose.yml` (backend-worker service).

### 7.4 Model Service 1 — Culture/Behavioural Fit

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Model version | 2.0.0 |
| Engine | DecisionDominantEngine with KeywordSignalClassifier |
| Canonical dimensions | ownership, execution, challenge, ambiguity, feedback |
| Input | Interview transcript + operating environment + taxonomy |
| Output | Per-dimension scores, confidence, rationale, overall alignment, risk level, recommendation |

**Evidence:** `model-service-1/app/main.py`, `model-service-1/app/model.py`, `model-service-1/app/schemas.py`, `model-service-1/requirements.txt`.

### 7.5 Model Service 2 — Skills/Technical Fit

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Model version | 3.0.0 |
| Engine | DeterministicInterviewScorer (JD-driven) |
| Input | Job description + resume text + interview answers/transcript |
| Output | Overall score, per-competency scores (0-1), must-have pass/fail, gaps, outcome (PASS/REVIEW/FAIL) |

**Evidence:** `model-service-2/app/main.py`, `model-service-2/app/model.py`, `model-service-2/app/schemas.py`, `model-service-2/requirements.txt`.

### 7.6 Python ACS Service

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Purpose | Azure Communication Services call automation and recording |
| Auth | Shared secret (`ACS_WORKER_SHARED_SECRET`) for internal API |
| Endpoints | Call create/answer/hangup, recording start/pause/resume/stop, health checks |
| Dependencies | azure-communication-callautomation, azure-storage-blob, pydub (audio), ffmpeg |

**Evidence:** `python-acs-service/app/main.py`, `python-acs-service/app/config.py`, `python-acs-service/app/api/routes/`, `python-acs-service/Dockerfile` (installs ffmpeg).

---

## 8. Frontend Architecture

### 8.1 Routing Structure

The SPA uses React Router v6 with the following route groups:

| Route Pattern | Page Component | Purpose |
|---------------|---------------|---------|
| `/` | Index | Landing page |
| `/auth` | Auth | Login and registration |
| `/org/*` | OrgDashboard, OrgOnboarding, OrgSettings, NewRole, RoleDetails, EditRoleRubric, InterviewReport | Recruiter portal |
| `/candidate/*` | CandidatePortal, CandidateProfile, PracticeInterview, InterviewLobby, LiveInterview, InterviewComplete | Candidate portal |
| `/invite/:token` | InviteValidation | Invitation claim flow |

**Evidence:** `src/lib/App.jsx`.

### 8.2 API Client Pattern

The frontend uses a custom fetch-based HTTP client (`src/api/http.js`) with:
- Bearer token injection from `localStorage` (key: `talenti_auth_token`)
- Automatic Content-Type handling (JSON vs FormData)
- Custom `ApiError` class with status and error details
- Credentials: `include` for cookie-based refresh token support
- Snake_case/camelCase field mapping on specific API modules

Separate API modules exist for each domain: `auth.js`, `candidates.js`, `interviews.js`, `invitations.js`, `roles.js`, `organisations.js`, `scoring.js`, `resumeBatches.js`, `acs.js`, `speech.js`, `storage.js`, `audit.js`, `requirements.js`, `shortlist.js`.

**Evidence:** `src/api/http.js`, `src/api/auth.js`, and other files in `src/api/`.

### 8.3 State Management

- **Server state:** TanStack React Query 5 with domain-specific query keys (e.g., `["candidate-profile"]`, `["current-org"]`, `["job-roles", orgId]`).
- **Form state:** React Hook Form with Zod schema validation.
- **Local UI state:** React `useState` for toggles, loading indicators, and transient UI state.
- **No global auth context:** Auth state is derived from localStorage token and on-demand `authApi.me()` calls.

Custom hooks centralise data access: `useCandidateData.js`, `useOrgData.js`, `useInterviewPersistence.js`, `useAcsCall.js`, `useAzureSpeech.js`, `useAuditLog.js`.

**Evidence:** `src/lib/hooks/`, `package.json` (tanstack/react-query, react-hook-form, zod).

### 8.4 Browser-Direct Integrations

The frontend establishes direct connections to Azure services using backend-issued tokens:
- **Azure Communication Services Calling SDK** for video interview media
- **Azure Speech SDK** for speech-to-text and text-to-speech during interviews
- **Azure Speech Avatar** for visual avatar rendering

**Evidence:** `src/lib/hooks/useAcsCall.js`, `src/lib/hooks/useAzureSpeech.js`, `src/lib/hooks/useAzureAvatar.js`, `package.json` (@azure/communication-calling, microsoft-cognitiveservices-speech-sdk).

---

## 9. Backend Architecture

### 9.1 Application Structure

```
backend/
  app/
    main.py              # FastAPI app with lifespan, middleware, router registration
    worker_main.py       # Background worker entry point
    db.py                # SQLAlchemy engine and session factory
    core/
      config.py          # Pydantic Settings from environment
      security.py        # JWT creation, password hashing (bcrypt)
      logging.py         # JSON structured logging
      migrations.py      # Alembic auto-migration on startup
    api/
      deps.py            # Dependency injection (DB session, auth, org membership)
      auth.py            # Auth endpoints
      orgs.py            # Organisation endpoints
      roles.py           # Job role endpoints
      candidates.py      # Candidate profile endpoints
      applications.py    # Application endpoints
      interviews.py      # Interview lifecycle endpoints
      interview_scores.py
      scoring.py         # Dual-scorecard analysis endpoint
      resume_batches.py  # Bulk resume ingestion
      invitations.py     # Invitation management
      acs.py             # ACS token and webhook endpoints
      call_automation.py # Call control endpoints
      ai.py              # AI interviewer chat (Azure OpenAI)
      speech.py          # Speech token endpoint
      storage.py         # Blob storage SAS URL generation
      shortlist.py       # Candidate shortlisting
      retention.py       # Data retention cleanup
      audit_log.py       # Audit trail
      requirements.py    # JD parsing
    models/              # 27 SQLAlchemy ORM models
    schemas/             # Pydantic request/response schemas
    services/            # Business logic and external service clients
  alembic/               # Database migrations (8 versions)
  tests/                 # Pytest test suite
```

### 9.2 Middleware

The backend applies the following middleware (registered in `backend/app/main.py`):

1. **CORS Middleware** — Configurable origins from `ALLOWED_ORIGINS` environment variable; credentials enabled.
2. **Request Logging Middleware** — Generates `X-Request-ID` per request; logs method, path, status, and duration in structured JSON.

**Evidence:** `backend/app/main.py`.

### 9.3 Database Migrations

Alembic migrations run automatically on application startup via `run_startup_migrations()` in `backend/app/core/migrations.py`. The migration environment uses PostgreSQL advisory locking to prevent concurrent migration execution during multi-instance startups.

Migration history (8 versions):
1. `0001_initial.py` — Base schema
2. `0002_recording_lifecycle_fields.py` — Recording fields
3. `0003_blob_jobs_and_interview_lifecycle.py` — Blob jobs and interview management
4. `0004_resume_ingestion_and_claim_flow.py` — Resume parsing and invitation claim
5. `0005_scoring_canonical_dimensions.py` — Canonical scoring dimensions
6. `0006_org_environment_inputs.py` — Organisation environment configuration
7. `0007_post_hire_outcomes.py` — Post-hire outcome tracking
8. `0008_dual_scorecard_columns.py` — Dual scorecard support

**Evidence:** `backend/alembic/versions/`, `backend/alembic/env.py`, `backend/app/core/migrations.py`.

### 9.4 Key Runtime Flows

**Interview Lifecycle:**
1. `POST /api/v1/interviews/start` — Creates interview record, enqueues orchestration jobs
2. `POST /api/v1/interviews/{id}/transcripts` — Streams transcript segments during interview
3. `POST /api/v1/interviews/{id}/complete` — Marks interview complete, enqueues post-interview jobs
4. `POST /api/v1/scoring/analyze` — Backend calls model-service-1 and model-service-2, stores results in `interview_scores` and `score_dimensions`

**Resume Batch Ingestion:**
1. `POST /api/v1/resume-batches/` — Creates batch for a job role
2. `POST /api/v1/resume-batches/{id}/items/upload-url` — Generates SAS URL for direct-to-blob upload
3. `POST /api/v1/resume-batches/{id}/process` — Enqueues parsing jobs for all items
4. Backend worker parses resumes, creates parsed profile snapshots
5. `POST /api/v1/resume-batches/{id}/invite` — Sends invitations to parsed candidates

**Invitation Claim Flow:**
1. Candidate receives email with invitation link containing token
2. `GET /api/auth/claim-context?token=...` — Validates token, returns prefilled profile data
3. `POST /api/auth/claim-invite` — Claims account, sets up credentials, returns access token

---

## 10. Data Architecture

### 10.1 Database

| Attribute | Value |
|-----------|-------|
| Engine | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (declarative base) |
| Driver | psycopg 3.2+ (async-capable) |
| Migrations | Alembic with auto-run on startup |
| Local dev | Docker container (postgres:16-alpine) or external |
| Deployed | Azure Database for PostgreSQL Flexible Server (Burstable B1ms, 32GB storage, 7-day backup) |

### 10.2 Core Entity Groups

**Users and Organisations:**
- `users` — Authentication accounts (email, password_hash, full_name, is_active)
- `organisations` — Tenant accounts with culture framework, retention settings
- `org_users` — Organisation membership with role (member/admin)
- `user_roles` — User role assignments

**Candidates:**
- `candidate_profiles` — Personal details, contact info, CV references, profile completion
- `employment_history`, `education`, `candidate_skills` — Profile components
- `candidate_dei` — Optional diversity/equity/inclusion data
- `parsed_profile_snapshots` — Resume parsing results

**Recruitment:**
- `job_roles` — Title, description, requirements, scoring rubric, interview structure
- `applications` — Links candidates to job roles with status tracking
- `invitations` — Token-based invitation with expiration and claim tracking
- `resume_ingestion_batches` / `resume_ingestion_items` — Bulk resume upload processing

**Interviews and Scoring:**
- `interviews` — Status, scheduling, call IDs, recording details, transcript status, anti-cheat signals
- `transcript_segments` — Speaker, content, timestamps per interview
- `interview_scores` — Scoring summary per interview
- `score_dimensions` — Per-dimension scores (culture and skills)
- `post_hire_outcomes` — Employment outcomes for future predictive analytics

**Operations:**
- `background_jobs` — Job queue (type, status, payload, attempts, retry scheduling)
- `domain_events` — Event outbox with JSON payloads
- `audit_log` — Action tracking for compliance
- `data_deletion_requests` — GDPR deletion request tracking
- `org_environment_inputs` — Culture/environment questionnaire responses

**Evidence:** `backend/app/models/`, `backend/alembic/versions/`, `documentation/DATABASE_SCHEMA.md`.

### 10.3 File Storage

| Store | Purpose | Access Pattern |
|-------|---------|---------------|
| Azure Blob Storage (`uploads` container) | Resumes, CVs, profile documents | SAS URL upload from browser; backend/worker read |
| Azure Blob Storage (`recordings` container) | Interview call recordings | ACS worker writes; backend/worker reads |
| Local filesystem (fallback) | CV uploads when blob not configured | `POST /api/v1/candidates/cv` (local dev only) |

**Evidence:** `infra/modules/platform.bicep` (storage containers), `backend/app/services/blob_storage.py`, `backend/app/core/config.py` (azure_storage_* settings), `python-acs-service/app/config.py` (RECORDING_CONTAINER).

### 10.4 Multi-Tenancy Model

The platform implements application-level multi-tenancy:
- Organisation isolation is enforced at the API layer via `require_org_member()` dependency injection
- Resources (job roles, applications, batches) are scoped to organisations via foreign keys
- There is no database-level row-level security (RLS) implemented despite documentation references

**Note for auditors:** The DATABASE_SCHEMA.md references RLS policies, but no RLS implementation was found in the Alembic migrations or model definitions. Multi-tenancy isolation relies entirely on application-layer checks in `backend/app/api/deps.py`.

**Evidence:** `backend/app/api/deps.py` (require_org_member), `backend/app/models/` (organisation_id foreign keys), `backend/alembic/versions/` (no RLS migration found).

---

## 11. Integration Architecture

### 11.1 Azure Service Integrations

| Azure Service | Purpose | Integration Point | Credential Type |
|---------------|---------|-------------------|----------------|
| Azure Communication Services | Video calling, identity tokens, call recording | Backend API + ACS worker + browser SDK | Connection string |
| Azure OpenAI | AI interviewer chat responses | Backend API (`/api/v1/interview/chat`) | API key + endpoint |
| Azure Speech Services | Speech-to-text, text-to-speech, avatar | Backend API (token issuance) + browser SDK | API key + region |
| Azure Blob Storage | File uploads, recordings | Backend API (SAS URL generation), ACS worker, browser (direct upload) | Account key |
| Azure Key Vault | Runtime secret storage | Container Apps secret references | Managed identity (RBAC) |
| Azure Container Registry | Container image storage | CI/CD pipelines, Container Apps | Managed identity (AcrPull) |
| Azure Application Insights | Telemetry and diagnostics | Container Apps environment | Instrumentation key |
| Azure Log Analytics | Log aggregation and querying | Container Apps environment | Workspace ID |
| Azure Front Door | CDN and WAF for frontend (UAT/PROD) | Static website hosting | N/A |

### 11.2 Inter-Service Communication

| From | To | Protocol | Auth | Purpose |
|------|----|----------|------|---------|
| Backend API | model-service-1 | HTTP POST `/predict` | None (internal network) | Culture fit scoring |
| Backend API | model-service-2 | HTTP POST `/predict` or `/predict/transcript` | None (internal network) | Skills fit scoring |
| Backend API | python-acs-service | HTTP (various `/internal/*` endpoints) | Shared secret header | Call and recording management |
| Backend Worker | model-service-1 | HTTP POST `/predict` | None (internal network) | Auto-scoring |
| Backend Worker | model-service-2 | HTTP POST `/predict` or `/predict/transcript` | None (internal network) | Auto-scoring |
| Backend Worker | python-acs-service | HTTP | Shared secret header | Recording orchestration |
| python-acs-service | Backend API | HTTP callback (`/api/v1/acs/worker-events`) | Shared secret | Recording status updates |
| Azure ACS | Backend API | HTTP webhook (`/api/v1/acs/webhook`) | EventGrid subscription | Call lifecycle events |
| Browser | Azure ACS | WebRTC (via SDK) | ACS token (backend-issued) | Live call media |
| Browser | Azure Speech | WebSocket (via SDK) | Speech token (backend-issued) | Real-time speech |

**Note for auditors:** Model services (model-service-1 and model-service-2) have no authentication on their `/predict` endpoints. They rely entirely on internal-only network ingress in the deployed Container Apps environment. In the local Docker Compose environment, these endpoints are accessible on localhost ports 8001 and 8002 without authentication.

**Evidence:** `backend/app/services/ml_client.py`, `backend/app/services/acs_worker_client.py`, `python-acs-service/app/security/internal.py`, `model-service-1/app/main.py`, `model-service-2/app/main.py`, `infra/modules/platform.bicep`.

---

## 12. Authentication and Authorization

### 12.1 Authentication Mechanism

| Attribute | Value |
|-----------|-------|
| Token type | JWT (JSON Web Tokens) |
| Algorithm | HS256 (symmetric) |
| Signing key | `JWT_SECRET` environment variable |
| Access token TTL | 60 minutes (configurable) |
| Refresh token TTL | 30 days (configurable) |
| Refresh token delivery | httpOnly cookie |
| Access token delivery | JSON response body, stored in `localStorage` on frontend |
| Password hashing | bcrypt via passlib |
| Token claims | `sub` (user ID), `iss`, `aud`, `exp`, optional extra claims |

### 12.2 Authentication Flows

1. **Registration:** `POST /api/auth/register` — Creates user, returns access token
2. **Login:** `POST /api/auth/login` — Validates credentials, returns access token, sets refresh cookie
3. **Token refresh:** `POST /api/auth/refresh` — Uses refresh token cookie, returns new access token
4. **Invitation claim:** `POST /api/auth/claim-invite` — Claims invitation token, creates/updates user, returns access token
5. **Session check:** `GET /api/auth/me` — Returns current user from JWT

### 12.3 Authorization Model

- **JWT validation:** Every authenticated endpoint uses `get_current_user()` dependency which decodes and validates the JWT, then loads the user from the database.
- **Organisation membership:** Endpoints requiring org context use `require_org_member()` which checks the `org_users` table.
- **Role-based access:** The `org_users.role` field supports `member` and `admin` roles, though the enforcement granularity of admin-vs-member permissions at the endpoint level is limited in evidence.
- **No RBAC framework:** There is no explicit role-based access control middleware or permission decorator system. Authorization checks are implemented inline in route handlers.

**Evidence:** `backend/app/core/security.py`, `backend/app/api/deps.py`, `backend/app/api/auth.py`.

### 12.4 Internal Service Authentication

The python-acs-service uses a shared secret (`ACS_WORKER_SHARED_SECRET`) for authenticating requests from the backend. This is validated in `python-acs-service/app/security/internal.py`.

Model services have no authentication — they rely on network-level isolation (internal-only ingress in Container Apps).

---

## 13. Security Architecture and Controls

### 13.1 Implemented Controls

| Control | Implementation | Evidence |
|---------|---------------|----------|
| JWT authentication | HS256 tokens with issuer/audience validation | `backend/app/core/security.py`, `backend/app/api/deps.py` |
| Password hashing | bcrypt via passlib | `backend/app/core/security.py` |
| CORS | Configurable allowed origins | `backend/app/main.py`, `backend/app/core/config.py` |
| HTTPS | Enforced at infrastructure level (Front Door, App Service) | `infra/modules/platform.bicep` |
| Secret scanning | Gitleaks in PR pipeline | `.github/workflows/pr-security-iac.yml` |
| Dependency scanning | npm audit, pip-audit, Trivy | `.github/workflows/pr-security-iac.yml`, `.github/workflows/ci-main.yml` |
| Container scanning | Trivy vulnerability scan (high/critical gate) | `.github/workflows/ci-main.yml` |
| IaC scanning | Checkov policy scan on Bicep templates | `.github/workflows/pr-security-iac.yml` |
| CodeQL | Static analysis for JS/TS, Python, Actions | `.github/workflows/codeql.yml` |
| Image signing | Cosign keyless signing via OIDC | `.github/workflows/ci-main.yml` |
| Build attestation | GitHub build provenance attestation | `.github/workflows/ci-main.yml` |
| SBOM generation | Syft (SPDX format) for built images | `.github/workflows/ci-main.yml` |
| Dockerfile linting | Hadolint | `.github/workflows/pr-security-iac.yml` |
| WAF | Azure Front Door WAF policy (UAT/PROD) | `infra/uat/main.bicep`, `infra/prod/main.bicep` |
| Audit logging | `audit_log` table with action tracking | `backend/app/api/audit_log.py`, `backend/app/models/` |
| GDPR deletion | `data_deletion_requests` table and candidate deletion endpoint | `backend/app/api/candidates.py` |
| Recording retention | Configurable per-organisation retention period | `organisations.recording_retention_days`, `backend/app/api/retention.py` |
| Non-root containers | All Dockerfiles create and run as non-root users | `backend/Dockerfile`, `model-service-1/Dockerfile`, etc. |
| Internal-only services | Model services and ACS worker have internal-only ingress | `infra/modules/platform.bicep` |
| Shared secret auth | ACS worker endpoints require shared secret | `python-acs-service/app/security/internal.py` |
| SAS URL expiry | Blob storage SAS tokens expire after configurable TTL (default 15 min) | `backend/app/core/config.py` |

### 13.2 Security Considerations and Gaps

| Item | Status | Notes |
|------|--------|-------|
| Access token in localStorage | **Risk** | Vulnerable to XSS; httpOnly cookie would be more secure for the access token |
| HS256 JWT algorithm | **Acceptable for single-service** | Symmetric key shared by backend only; asymmetric (RS256) would be needed for multi-party verification |
| Model service no-auth | **Mitigated by network** | Relies entirely on Container Apps internal ingress; no defence-in-depth |
| No rate limiting | **Gap** | No evidence of rate limiting on authentication or API endpoints |
| No CSRF protection | **Partial** | Refresh token in httpOnly cookie but no CSRF token mechanism observed |
| No IP allowlisting on backend | **Gap** | Backend API is publicly accessible; only frontend has WAF/Front Door in UAT/PROD |
| RLS not implemented | **Gap** | Documentation references RLS but no implementation found; relies on application-layer isolation |
| `datetime.utcnow()` usage | **Minor** | Deprecated in Python 3.12+; should use `datetime.now(UTC)` |

**Evidence:** Source code files listed above, CI/CD workflow files, infrastructure templates.

---

## 14. Configuration and Secrets Management

### 14.1 Configuration Approach

The backend uses Pydantic `BaseSettings` to load configuration from environment variables with `.env` file fallback. The settings class is defined in `backend/app/core/config.py`.

### 14.2 Key Environment Variables

| Variable | Service | Purpose | Sensitivity |
|----------|---------|---------|-------------|
| `DATABASE_URL` | Backend, ACS worker | PostgreSQL connection string | High (contains credentials) |
| `JWT_SECRET` | Backend | JWT signing key | Critical |
| `AZURE_STORAGE_ACCOUNT_KEY` | Backend | Blob storage access | High |
| `AZURE_ACS_CONNECTION_STRING` | Backend, ACS worker | Communication Services | High |
| `AZURE_OPENAI_API_KEY` | Backend | AI service access | High |
| `AZURE_SPEECH_KEY` | Backend | Speech service access | High |
| `ACS_WORKER_SHARED_SECRET` | Backend, ACS worker | Inter-service auth | High |
| `MODEL_SERVICE_1_URL` | Backend | Model service endpoint | Low |
| `MODEL_SERVICE_2_URL` | Backend | Model service endpoint | Low |
| `ALLOWED_ORIGINS` | Backend, ACS worker | CORS configuration | Low |
| `AUTO_SCORE_INTERVIEWS` | Backend worker | Feature flag | Low |
| `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS` | Backend worker | Worker tuning | Low |

### 14.3 Secrets in Deployed Environments

In Azure Container Apps, secrets are referenced from Azure Key Vault via managed identity with `Key Vault Secrets User` RBAC role assignment. This is configured in the infrastructure deployment workflows.

**Evidence:** `backend/app/core/config.py`, `.env.example`, `infra/modules/platform.bicep` (Key Vault resource), `.github/workflows/infra-dev.yml` (role assignments).

### 14.4 Local Development

Local development uses `.env` files at the repository root and in `/backend/`. The `.env.example` template provides the required variable list. Default `DATABASE_URL` points to `localhost:5432`.

---

## 15. Environments and Deployment Architecture

### 15.1 Environment Matrix

| Environment | Frontend Hosting | Backend Hosting | Database | Ingress | Network |
|-------------|-----------------|----------------|----------|---------|---------|
| **Local** | Vite dev server (8080) | Uvicorn (8000) | Docker PostgreSQL | localhost | Docker bridge network |
| **DEV** | Azure Static Web Apps | Azure Container Apps | Azure PostgreSQL Flexible Server | Public (backend), internal (services) | Container Apps environment |
| **UAT** | Azure Storage + Front Door (WAF + IP allowlist) | Azure Container Apps | Azure PostgreSQL Flexible Server | Public (backend), internal (services) | Container Apps environment |
| **PROD** | Azure Storage + Front Door (WAF) | Azure Container Apps | Azure PostgreSQL Flexible Server | Public (backend), internal (services) | Container Apps environment |

### 15.2 Azure Resource Inventory per Environment

Each environment deploys the following Azure resources (defined in `infra/modules/platform.bicep`):

| Resource | SKU/Tier |
|----------|----------|
| Container Apps Environment | Managed (with Log Analytics) |
| Container Apps (5) | 0.5 CPU / 1Gi memory per container, scale 1-2 replicas |
| Azure Container Registry | Basic |
| Azure Key Vault | Standard (RBAC enabled) |
| Azure Storage Account | Standard_LRS, StorageV2, TLS 1.2 |
| Azure Database for PostgreSQL Flexible Server | Burstable B1ms, 32GB storage, 7-day backup |
| Log Analytics Workspace | PerGB2018, 30-day retention |
| Application Insights | Web type |
| Azure Monitor Action Group | Email alerts |

Additionally for UAT/PROD:
| Resource | Details |
|----------|---------|
| Azure Front Door Standard | With WAF policy |
| Storage static website hosting | Enabled via workflow |

### 15.3 Container App Configuration

| Container App | Image Source | Ingress | Replicas | Health Probes |
|--------------|-------------|---------|----------|---------------|
| backend | ACR (SHA-tagged) | External, port 8000 | 1-2 | Liveness + Readiness on `/health` |
| backend-worker | Same image as backend | None | 1 | Liveness + Readiness |
| model-service-1 | ACR (pinned digest) | Internal, port 8001 | 1-2 | Liveness + Readiness on `/health` |
| model-service-2 | ACR (pinned digest) | Internal, port 8002 | 1-2 | Liveness + Readiness on `/health` |
| acs-worker | ACR (SHA-tagged) | Internal, port 8000 | 1 | Liveness + Readiness |

**Evidence:** `infra/modules/platform.bicep`, `infra/dev/parameters.dev.json`, `infra/uat/parameters.uat.json`, `infra/prod/parameters.prod.json`.

---

## 16. CI/CD and Release Approach

### 16.1 Pipeline Overview

The platform uses GitHub Actions with 11 workflow files implementing a trunk-based development model with immutable artifact promotion.

```
Feature PR
  |-- pr-fast-quality (lint, test, build, coverage gates)
  |-- pr-security-iac (secrets, dependencies, containers, IaC)
  |-- pr-ephemeral-deploy (isolated PR environment + smoke tests)
  |-- codeql (static analysis)
  v
Merge to main
  |-- ci-main (build, scan, sign, attest images)
  |-- infra-dev (validate + deploy infrastructure if changed)
  v
deploy-dev (deploy to DEV, smoke test)
  v
release (release-please versioning, manifest creation)
  v
promote-release -> UAT (automatic on release publish)
  v
promote-release -> PROD (manual workflow_dispatch by tag)
```

### 16.2 PR Quality Gates

| Workflow | Checks |
|----------|--------|
| `pr-fast-quality.yml` | Conventional Commit title format, frontend lint + test + build, backend tests (60% coverage gate), ACS service tests (40% coverage gate), migration execution check |
| `pr-security-iac.yml` | Gitleaks secret scanning, npm audit (high/critical), pip-audit (strict), Dockerfile linting (hadolint), Trivy container scan, Bicep compilation, Checkov IaC policy scan |
| `pr-ephemeral-deploy.yml` | Builds PR-specific image, creates isolated database and Container App, runs migrations, smoke tests, auto-cleanup on PR close |
| `codeql.yml` | GitHub CodeQL analysis for JavaScript/TypeScript, Python, and Actions |

### 16.3 Immutable Image Pipeline

1. `ci-main.yml` builds backend and ACS worker images tagged with the Git SHA
2. Generates SBOMs using Syft (SPDX format)
3. Scans images with Trivy (high/critical vulnerability gate)
4. Signs images with cosign (keyless OIDC)
5. Attests build provenance via GitHub `actions/attest-build-provenance`
6. Uploads CI evidence artifacts (manifests, SBOMs, signatures)

### 16.4 Release and Promotion

- **release-please** manages `VERSION` file and `CHANGELOG.md` via conventional commit parsing
- `release-manifest.json` is the promotion contract: contains version, git SHA, all image digests, frontend source SHA
- UAT auto-promotes from published GitHub Releases
- PROD requires manual `workflow_dispatch` specifying a release tag
- `promote-release.yml` imports images into target ACR, verifies signatures with cosign, deploys without rebuilding

### 16.5 Infrastructure as Code

- Bicep templates in `infra/modules/platform.bicep` (shared module) with per-environment parameter files
- Separate infra workflows per environment (`infra-dev.yml`, `infra-uat.yml`, `infra-prod.yml`)
- `deploy-dev.yml` gates on `infra-dev` success when infrastructure files change
- OIDC federation for Azure authentication in workflows

**Evidence:** All files in `.github/workflows/`, `infra/`, `.release-please-manifest.json`, `VERSION`, `CHANGELOG.md`.

---

## 17. Logging, Monitoring, and Operational Support

### 17.1 Logging

| Aspect | Implementation |
|--------|---------------|
| Format | Structured JSON to stdout |
| Request tracing | `X-Request-ID` generated per request, included in all log entries |
| Worker logging | `correlation_id`, `job_type`, `job_id` context variables |
| Log aggregation | Azure Log Analytics via Container Apps environment |
| Framework | Python `logging` with custom `JsonFormatter` |

**Evidence:** `backend/app/core/logging.py`, `backend/app/main.py` (middleware), `python-acs-service/app/logging_utils.py`.

### 17.2 Monitoring

| Component | Health Endpoint | Monitoring |
|-----------|----------------|------------|
| Backend API | `GET /health` | Application Insights, synthetic availability |
| model-service-1 | `GET /health` | Container restart count, prediction latency |
| model-service-2 | `GET /health` | Container restart count, prediction latency |
| python-acs-service | `GET /health`, `/health/ready`, `/health/live` | Readiness checks (ACS, storage, callback connectivity) |
| Backend Worker | N/A (no HTTP endpoint) | Queue metrics: `pending_jobs`, `oldest_pending_job_age_seconds` |
| PostgreSQL | `pg_isready` | Azure managed server health, disk usage |

### 17.3 Alerting Baseline

The infrastructure provisions Azure Monitor resources per environment:
- Log Analytics workspace
- Application Insights component
- Azure Monitor Action Group (email-based)

Documented alert targets (configuration details not found in IaC):
- Synthetic availability checks for frontend and backend
- 5xx spike metric alerts
- Latency regression alerts
- Container restart count alerts
- Background job backlog and age query alerts

**Note for auditors:** Alert rule definitions are documented in `MONITORING.md` but the actual Azure Monitor alert rules are not defined in the Bicep templates. Alert configuration may exist as manual Azure portal configuration or in a separate operational runbook.

**Evidence:** `infra/modules/platform.bicep` (Log Analytics, App Insights, Action Group resources), `documentation/MONITORING.md`.

---

## 18. Error Handling and Resilience Considerations

### 18.1 Implemented Patterns

| Pattern | Implementation |
|---------|---------------|
| Database connection retry | Alembic advisory locking prevents concurrent migration failures |
| Background job retry | Configurable max attempts with retry scheduling in `background_jobs` |
| Health checks | All services expose health endpoints; Container Apps use liveness/readiness probes |
| Graceful degradation | Blob storage falls back to local file system when not configured |
| Domain event outbox | `domain_events` table ensures events survive worker restarts |

### 18.2 Resilience Gaps

| Gap | Risk |
|-----|------|
| No circuit breaker for external Azure service calls | Azure service outages could cascade to all endpoints |
| No request timeout configuration on inter-service HTTP calls | Slow model service responses could exhaust backend connections |
| Single-instance backend worker | Worker failure stops all async processing until restart |
| No dead-letter queue | Failed jobs after max retries remain in `failed` status but have no automated alerting or reprocessing |
| No database connection pooling configuration | Default SQLAlchemy pool settings may not be optimal for production concurrency |

---

## 19. Architecture Decision Records

### ADR-001: FastAPI + PostgreSQL Backend

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | The platform needed a lightweight, Python-based web framework with strong async support and a reliable relational database. |
| **Decision** | Use FastAPI for the backend API layer and PostgreSQL as the primary datastore. |
| **Rationale** | Simple local development experience. Consistent with Python ML ecosystem for model services. PostgreSQL provides ACID transactions for job queue and audit trail. |
| **Implications** | All services use Python 3.11. Single database for all backend state. No separate caching layer. |
| **Evidence** | `backend/pyproject.toml`, `backend/app/main.py`, `docker-compose.yml`, `infra/modules/platform.bicep`. |

### ADR-002: JWT Authentication with Local User Table

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | The platform needed authentication that works in local development without third-party providers. |
| **Decision** | Use JWTs issued and validated by the FastAPI service with a local `users` table. HS256 algorithm with configurable TTL. |
| **Rationale** | Keeps auth within the service boundary. Enables standalone operation. Refresh tokens in httpOnly cookies provide session continuity. |
| **Implications** | No SSO/SAML/OIDC support for enterprise customers. JWT secret must be securely managed. No token revocation mechanism beyond expiry. |
| **Evidence** | `backend/app/core/security.py`, `backend/app/api/auth.py`, `backend/app/api/deps.py`. |

### ADR-003: Azure-First Cloud Services

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | The platform requires video calling, recording, speech services, AI capabilities, and object storage. |
| **Decision** | Use Azure Communication Services, Azure Speech, Azure OpenAI, and Azure Blob Storage as managed services. |
| **Rationale** | Provides scalable managed services with consistent SDK experience. Aligns with organisational cloud strategy. |
| **Implications** | Strong Azure lock-in. All credentials managed via environment variables, with Key Vault in production. |
| **Evidence** | `backend/app/core/config.py` (Azure config variables), `infra/modules/platform.bicep`, `python-acs-service/`, `src/lib/hooks/useAcsCall.js`. |

### ADR-004: REST API with Versioned Prefixes

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | The frontend needs a stable API contract with the backend. |
| **Decision** | Use REST endpoints under `/api` and `/api/v1` prefixes. |
| **Rationale** | Clear versioning enables API evolution. Compatible with frontend fetch-based client. |
| **Implications** | Some endpoints use `/api` (auth, orgs, invitations) and some use `/api/v1` (candidates, interviews, scoring). This split is historical rather than intentional versioning. |
| **Evidence** | `backend/app/main.py` (router prefix registration). |

### ADR-005: Database-Backed Background Jobs

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | Async operations (resume parsing, scoring, invitation prep, recording processing) need reliable execution without introducing an external message broker. |
| **Decision** | Use a `background_jobs` table polled by `backend-worker` instead of RabbitMQ, Azure Service Bus, or similar. |
| **Rationale** | Avoids external broker dependency. Jobs are transactionally consistent with the state changes that produce them. The `domain_events` outbox ensures events are not lost. Retry logic with exponential backoff is built into the worker. |
| **Implications** | Polling introduces latency (configurable, default 2s). Single-instance worker is a scaling constraint. No native dead-letter or fan-out patterns. |
| **Evidence** | `backend/app/models/` (BackgroundJob model), `backend/app/worker_main.py`, `backend/app/services/background_jobs.py`, `docker-compose.yml` (backend-worker service). |

### ADR-006: Dual Scorecard Architecture

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | Interview assessment needs to evaluate both culture fit and skills fit, but these are fundamentally different types of assessment. |
| **Decision** | Split scoring into two independent model services. model-service-1 handles culture/behavioural fit (5 canonical dimensions). model-service-2 handles skills/technical fit (JD-driven competencies). Scores are never merged into a single composite. |
| **Rationale** | Culture fit and skills fit are orthogonal assessments. Independent services can evolve, retrain, or be replaced independently. Recruiters can weight each dimension on its own terms. |
| **Implications** | Frontend must display two independent scorecards. Backend orchestrates calls to both services. Interview reports show dual perspectives. |
| **Evidence** | `model-service-1/app/schemas.py`, `model-service-2/app/schemas.py`, `backend/app/api/scoring.py`, `backend/alembic/versions/0008_dual_scorecard_columns.py`. |

### ADR-007: Decision-Dominant Scoring Logic

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | Hiring decisions based on AI scoring must be auditable and legally defensible. |
| **Decision** | ML classifiers extract signals from interview transcripts, but all scoring decisions are made by deterministic rules with configurable thresholds. |
| **Rationale** | Deterministic decisions are auditable and explainable. Scoring rules can be described to candidates and recruiters. Confidence gating flags uncertainty. Fatal risk flags override all other signals. |
| **Implications** | Scoring accuracy is bounded by rule quality, not model capability. Rules must be maintained and version-controlled alongside the model. |
| **Evidence** | `model-service-1/app/model.py` (DecisionDominantEngine), `model-service-2/app/model_draft.py` (DeterministicInterviewScorer). |

### ADR-008: Python ACS Service Separation

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | Azure Communication Services call automation has different scaling characteristics and failure modes from the main API. |
| **Decision** | Run ACS call automation as a separate microservice (`python-acs-service`) with internal-only ingress. |
| **Rationale** | Isolates call-related failures from core API. Enables independent scaling. Reduces attack surface via internal-only ingress. |
| **Implications** | Requires shared-secret authentication for inter-service calls. Adds deployment complexity (separate image, separate Container App). |
| **Evidence** | `python-acs-service/`, `infra/modules/platform.bicep` (internal ingress), `docker-compose.yml` (acs-worker service). |

### ADR-009: Trunk-Based Release with Immutable Promotion

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Context** | The platform needs a reliable release process that eliminates environment-specific build differences. |
| **Decision** | Use trunk-based development on `main` with release-please for versioning. Container images are built once, signed, attested, and promoted immutably through DEV -> UAT -> PROD. |
| **Rationale** | Build-once-promote-many eliminates environment-specific build issues. Image signing and attestation provide supply-chain integrity. `release-manifest.json` captures exact digests for reproducible deployments. |
| **Implications** | All environment-specific configuration must be external (env vars, Key Vault). Model service images are pinned by digest, not built in this pipeline. Frontend is rebuilt per environment from source (not promoted as an image). |
| **Evidence** | `.github/workflows/ci-main.yml`, `.github/workflows/deploy-dev.yml`, `.github/workflows/release.yml`, `.github/workflows/promote-release.yml`, `.release-please-manifest.json`. |

---

## 20. Known Limitations, Technical Debt, and Risks

### 20.1 Technical Debt

| Item | Description | Severity |
|------|------------|----------|
| **Deprecated API client files** | `src/lib/lib/apiClient.js` and `src/lib/lib/authClient.js` appear to be legacy predecessors of the current `src/api/` modules | Low |
| **Mixed API prefix convention** | Some endpoints use `/api` and others use `/api/v1` without clear versioning strategy | Low |
| **`datetime.utcnow()` usage** | Used in JWT creation; deprecated in Python 3.12+ | Low |
| **Frontend TypeScript absence** | Project uses JavaScript (JSX) without TypeScript, relying on Zod for runtime validation only | Medium |
| **No OpenAPI documentation** | FastAPI auto-generates OpenAPI docs, but no evidence of custom documentation or schema validation tests | Low |

### 20.2 Architectural Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **Single-instance worker** | Async job processing stops if worker crashes | Medium | High | Container Apps restart policy; consider scaling to multiple instances with job claiming |
| **No rate limiting** | Authentication and API endpoints vulnerable to brute force | High | Medium | Implement rate limiting at API gateway or middleware level |
| **Access token in localStorage** | XSS vulnerability could expose tokens | High | Low-Medium | Migrate to httpOnly cookie for access token |
| **No token revocation** | Compromised tokens valid until expiry (60 min) | Medium | Low | Implement token blocklist or reduce TTL |
| **Azure service dependency** | Multiple critical paths depend on Azure availability | High | Low | Azure SLA provides some protection; no multi-cloud fallback |
| **Model service no-auth** | Compromised network could allow unauthorized scoring | Medium | Low | Add shared secret or mTLS for model services |

### 20.3 Known Limitations

- No offline or degraded-mode operation — the platform requires all Azure services to be available
- No horizontal scaling of the background worker beyond a single instance
- No WebSocket or server-sent events — the frontend polls for updates
- No internationalisation (i18n) support
- No accessibility (a11y) audit evidence

---

## 21. Assumptions and Unresolved Questions

### Assumptions

1. **Azure AD tenant governance** is managed outside this repository at the subscription level.
2. **Network security groups and VNet peering** for UAT/PROD are configured outside the Bicep templates (the `platform.bicep` module references VNet parameters but does not create network security rules).
3. **Model service images** are built and published in separate repositories and pinned by digest in the deployment environment variables.
4. **Alert rule configuration** exists in Azure portal or a separate operational repository, as the Bicep templates provision monitoring resources but not alert rules.
5. **SSL/TLS certificates** are managed by Azure (Static Web Apps, Front Door, Container Apps provide automatic TLS).

### Unresolved Questions

1. **RLS implementation status:** DATABASE_SCHEMA.md documents Row-Level Security policies, but no RLS implementation was found in migrations. Is this planned or abandoned?
2. **Admin vs Member permission enforcement:** The `org_users.role` field supports roles, but how granularly are admin-only operations enforced at the endpoint level?
3. **Model service repository locations:** The integration guide references external git repositories for model services, but the actual repository URLs are not documented.
4. **Data retention automation:** The `/api/v1/retention/cleanup` endpoint exists, but is retention enforcement automated (scheduled job) or manual?
5. **Post-hire outcome data collection:** The `post_hire_outcomes` table exists but the ingestion mechanism (API endpoint, manual import, integration) is not clear.
6. **Practice interview scoring:** Practice interviews are stored, but whether they use the same model scoring pipeline or a separate mechanism is unclear.

---

## Appendix A: Repository Evidence Summary

### Directory Structure

```
/
  .github/workflows/     # 11 CI/CD workflow files
  backend/
    app/
      api/               # 18 API router modules + deps.py
      core/              # config, security, logging, migrations
      models/            # 27 SQLAlchemy ORM models
      schemas/           # Pydantic request/response schemas
      services/          # Business logic and external service clients
    alembic/versions/    # 8 migration files
    tests/               # 8 test modules
  model-service-1/
    app/                 # FastAPI app, model, schemas, utils
    models/              # Decision engine and classifier
    prompts/             # Prompt templates
    schemas/             # Taxonomy definitions
    tests/               # 4 test modules
  model-service-2/
    app/                 # FastAPI app, model, schemas
    models/              # Scorer and JD parser
    tests/               # 6 test modules
  python-acs-service/
    app/                 # FastAPI app, routes, config, security
    alembic/             # Service-specific migrations
    tests/               # 4 test modules
  src/
    api/                 # 14 API client modules
    lib/
      components/        # UI and domain components
      hooks/             # 16 custom React hooks
      pages/             # 19 page components
      lib/               # Utility modules
  infra/
    modules/             # platform.bicep (shared module)
    dev/                 # Dev environment Bicep + parameters
    uat/                 # UAT environment Bicep + parameters
    prod/                # Prod environment Bicep + parameters
  documentation/         # 12 markdown documentation files
  scripts/               # Automation and setup scripts
  tools/                 # Additional tooling
```

### Key Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | Frontend dependencies and scripts |
| `backend/pyproject.toml` | Backend Python dependencies |
| `model-service-1/requirements.txt` | Culture fit service dependencies |
| `model-service-2/requirements.txt` | Skills fit service dependencies |
| `python-acs-service/requirements.txt` | ACS service dependencies |
| `docker-compose.yml` | Local development orchestration |
| `.env.example` | Environment variable template |
| `infra/modules/platform.bicep` | Shared infrastructure module |
| `.release-please-manifest.json` | Release versioning manifest |
| `VERSION` | Current version (0.2.0) |

### Test Coverage

| Service | Test Directory | Test Files | Coverage Gate |
|---------|---------------|------------|---------------|
| Backend | `backend/tests/` | 8 modules | 60% (CI enforced) |
| model-service-1 | `model-service-1/tests/` | 4 modules | Not enforced in CI |
| model-service-2 | `model-service-2/tests/` | 6 modules | Not enforced in CI |
| python-acs-service | `python-acs-service/tests/` | 4 modules | 40% (CI enforced) |
| Frontend | N/A | Referenced in CI but location unclear | Referenced but not enforced |

---

## Appendix B: Audit Findings — Contradictions and Stale Documentation

### B.1 Contradictions Between Documentation and Implementation

| # | Document | Claim | Reality | Severity |
|---|----------|-------|---------|----------|
| 1 | `DATABASE_SCHEMA.md` | References RLS (Row-Level Security) policies for multi-tenancy | No RLS implementation found in any Alembic migration or model definition. Multi-tenancy relies on application-layer checks in `deps.py`. | High — misleading for auditors |
| 2 | `DATABASE_SCHEMA.md` | References `auth_users` table in ER diagram context | The actual table is `users` based on model definitions | Medium — naming inconsistency |
| 3 | `FRONTEND_GUIDE.md` (v1.1.0) | References `.tsx` file extensions in some places | All frontend files use `.jsx` (JavaScript, not TypeScript) | Low — cosmetic |
| 4 | `DEPLOYMENT_DEV_V2.md` | States "all core DEV infra remains in australiaeast" | DEV frontend uses Azure Static Web Apps which may be in `eastasia` (closest available region) | Low — region ambiguity for non-critical service |
| 5 | `API_REFERENCE.md` | Documents `POST /api/storage/upload-url` | Actual route is `POST /api/v1/storage/upload-url` based on router registration | Low — prefix mismatch |

### B.2 Stale or Incomplete Documentation

| # | Document | Issue |
|---|----------|-------|
| 1 | `AZURE_DEV_UAT_PROD_SETUP.txt` | Plain text file with manual Azure portal setup notes. Superseded by Bicep IaC and GitHub Actions workflows. Should be marked as legacy. |
| 2 | `CODEX_CAPABILITY_SETUP.md` | References GitHub Codex/Copilot setup and OIDC bootstrapping. Operational setup doc, not architecture. Content validity not verified. |
| 3 | `INTEGRATION_GUIDE.md` | References git submodule approach for model services, but current deployment uses pinned ACR image digests. The integration approach has evolved. |
| 4 | `old/` directory | Contains archived documents (FRONTEND_MIGRATION_PLAN.md, MODEL_SERVICE_SETUP_PROMPT.md). Correctly moved to old/ but their existence should be noted. |
| 5 | `model-service-1/IMPLEMENTATION_CHECKLIST.md`, `SETUP_COMPLETE.md` | Setup-phase documents that are no longer relevant post-implementation |
| 6 | Various `PROMPT_*.txt` and `PROMPT_*.md` files at root | AI prompt engineering documents used during development; not architecture documentation |

### B.3 Documentation Gaps

| # | Gap | Impact |
|---|-----|--------|
| 1 | No single canonical architecture document existed before this audit | Auditors would need to piece together architecture from 12+ documents |
| 2 | No data flow diagram showing PII handling | Required for privacy/GDPR compliance review |
| 3 | No threat model or security architecture diagram | Required for security audit |
| 4 | No disaster recovery or business continuity documentation | Required for operational risk assessment |
| 5 | No capacity planning or performance baseline documentation | Required for scalability review |
| 6 | No API authentication/authorization matrix | Required for access control review |
| 7 | Alert rule definitions not in IaC | Monitoring configuration not reproducible from repository |

---

## Appendix C: Gap Register for Auditors

### C.1 Documentation Gaps

| ID | Gap | Priority | Recommendation |
|----|-----|----------|---------------|
| DOC-01 | No canonical architecture document | **Resolved** | This document serves as the canonical reference |
| DOC-02 | No PII data flow diagram | High | Create a data flow diagram showing PII collection, storage, processing, and retention paths |
| DOC-03 | No threat model | High | Conduct threat modelling (STRIDE or equivalent) for the platform |
| DOC-04 | No disaster recovery documentation | Medium | Document RPO/RTO targets, backup/restore procedures, and failover processes |
| DOC-05 | No API authorization matrix | Medium | Create a matrix mapping endpoints to required roles/permissions |
| DOC-06 | DATABASE_SCHEMA.md claims RLS that does not exist | High | Remove RLS references or implement RLS |
| DOC-07 | AZURE_DEV_UAT_PROD_SETUP.txt is stale | Low | Mark as superseded by IaC |
| DOC-08 | INTEGRATION_GUIDE.md partially stale | Low | Update to reflect current ACR digest-based integration |

### C.2 Implementation Gaps

| ID | Gap | Priority | Recommendation |
|----|-----|----------|---------------|
| IMP-01 | No rate limiting on API endpoints | High | Implement rate limiting on auth endpoints at minimum |
| IMP-02 | No CSRF protection for cookie-based refresh | Medium | Add CSRF token for state-changing requests that use cookies |
| IMP-03 | RLS not implemented despite documentation | Medium | Implement database-level RLS or explicitly document application-layer-only isolation as a design decision |
| IMP-04 | Model services have no authentication | Medium | Add shared-secret or mTLS authentication as defence-in-depth |
| IMP-05 | No circuit breaker for external service calls | Medium | Implement circuit breaker pattern for Azure service integrations |
| IMP-06 | No request timeout on inter-service HTTP calls | Medium | Configure explicit timeouts on `ml_client.py` and `acs_worker_client.py` |
| IMP-07 | Alert rules not defined in IaC | Medium | Add Azure Monitor alert rules to Bicep templates |
| IMP-08 | Frontend test coverage not enforced in CI | Low | Add frontend test coverage gate to `pr-fast-quality.yml` |

### C.3 Security/Control Gaps

| ID | Gap | Priority | Recommendation |
|----|-----|----------|---------------|
| SEC-01 | Access token stored in localStorage (XSS risk) | Medium | Evaluate migration to httpOnly cookie for access token |
| SEC-02 | No token revocation mechanism | Medium | Implement token blocklist or reduce access token TTL |
| SEC-03 | HS256 JWT algorithm (symmetric key) | Low | Acceptable for single-service, but document the decision. Consider RS256 if multi-party token verification is needed. |
| SEC-04 | No penetration test evidence | High | Conduct and document penetration testing |
| SEC-05 | No DAST (Dynamic Application Security Testing) in pipeline | Medium | Add DAST scanning to CI/CD |
| SEC-06 | Backend API publicly accessible without WAF | Medium | Route backend traffic through Front Door WAF in UAT/PROD |
| SEC-07 | `datetime.utcnow()` deprecated | Low | Update to `datetime.now(datetime.UTC)` for Python 3.12+ compatibility |

### C.4 Operational Gaps

| ID | Gap | Priority | Recommendation |
|----|-----|----------|---------------|
| OPS-01 | Single-instance backend worker | Medium | Document scaling strategy or implement multi-instance job claiming |
| OPS-02 | No dead-letter handling for failed jobs | Medium | Implement alerting and reprocessing for permanently failed jobs |
| OPS-03 | No documented incident response procedure | Medium | Create runbook for common failure scenarios |
| OPS-04 | No backup/restore testing evidence | Medium | Document and test database restore procedures |
| OPS-05 | No capacity planning baseline | Low | Establish performance baselines and scaling triggers |
| OPS-06 | Model service coverage not enforced in CI | Low | Add coverage gates for model-service-1 and model-service-2 |

### C.5 Governance Gaps

| ID | Gap | Priority | Recommendation |
|----|-----|----------|---------------|
| GOV-01 | No change advisory board process documented | Medium | Document change approval process for production deployments |
| GOV-02 | No data classification policy | Medium | Classify data types (PII, sensitive, public) and document handling requirements |
| GOV-03 | No third-party dependency governance | Low | Document policy for evaluating and approving third-party dependencies |
| GOV-04 | No model governance / ML lifecycle documentation | Medium | Document model versioning, validation, and deployment approval process |
| GOV-05 | No accessibility compliance evidence | Low | Conduct WCAG audit if required by target markets |

---

*This document was generated from a comprehensive repository audit conducted on 19 April 2026. All claims are traceable to repository evidence as noted throughout. This document should be reviewed and updated whenever significant architectural changes are made to the platform.*
