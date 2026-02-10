# Post-Merge Audit Report

## 1. Architecture Integrity
- **Backend uses SQLite** via `DATABASE_URL` defaults and Alembic config; no Postgres drivers in backend dependencies. See `backend/app/core/config.py`, `backend/alembic.ini`, and `backend/pyproject.toml`.【F:backend/app/core/config.py†L1-L35】【F:backend/alembic.ini†L1-L3】【F:backend/pyproject.toml†L1-L26】
- **No Supabase SDKs** in application code; Supabase references remain in historical documentation (e.g., `PYTHON_REBUILD_GUIDE.md`, `ARCHITECTURE_DECISIONS.md`, `MONITORING.md`, `DISASTER_RECOVERY.md`). These docs contradict the target architecture and should be purged/updated.【F:PYTHON_REBUILD_GUIDE.md†L60-L112】【F:ARCHITECTURE_DECISIONS.md†L12-L18】【F:MONITORING.md†L392-L419】【F:DISASTER_RECOVERY.md†L96-L108】
- **No TypeScript source files** are present in `src/` or `backend/`; TypeScript references remain in docs and sample code blocks and must be cleaned if the “no TypeScript anywhere” rule is strict.【F:PYTHON_MIGRATION_PROMPT.md†L155-L173】【F:HANDOVER.md†L445-L474】
- **Azure integrations are environment-driven** and isolated in service modules for OpenAI, ACS, Speech, and Blob Storage. Missing configuration returns errors for Speech/ACS and controlled fallback for OpenAI in non-production environments.【F:backend/app/api/ai.py†L20-L68】【F:backend/app/api/speech.py†L13-L30】【F:backend/app/api/acs.py†L13-L28】【F:backend/app/services/blob_storage.py†L10-L37】

## 2. Backend Validation
- **Schema creation on cold start**: Alembic migration is executed at app startup, enabling cold-start schema creation (SQLite).【F:backend/app/main.py†L28-L37】
- **SQLite constraints**: FKs and unique indexes are defined in the initial migration; FK enforcement is explicitly enabled for SQLite connections.【F:backend/alembic/versions/0001_initial.py†L12-L231】【F:backend/app/db.py†L7-L23】
- **Validation gaps**:
  - Application creation does **not** validate existence of `job_role_id` or `candidate_profile_id`. This can create orphaned rows and breaks FK expectations in SQLite until commit fails at runtime.【F:backend/app/api/applications.py†L18-L48】
  - Invitation creation does **not** verify `application_id` existence and returns tokens regardless of business rules or email flows.【F:backend/app/api/invitations.py†L12-L37】
  - Interview creation does **not** validate `application_id` existence before insert, leading to FK violations or silent errors depending on SQLite settings.【F:backend/app/api/interviews.py†L45-L79】
- **Missing production hardening**:
  - No explicit rate limiting, security headers, or auth checks beyond JWT for high-cost endpoints (AI, scoring, storage).【F:backend/app/api/ai.py†L12-L68】【F:backend/app/api/scoring.py†L12-L43】【F:backend/app/api/storage.py†L12-L52】
  - CORS only enabled when `ALLOWED_ORIGINS` is set, but there is no validation of the env format; this is a known risk from the remediation list.【F:backend/app/main.py†L20-L27】【F:backend/app/core/config.py†L1-L20】
- **Hardcoded/weak secrets**: `python-acs-service` still ships with `JWT_SECRET = "change-me"`, which is production-dangerous if deployed as-is.【F:python-acs-service/app/config.py†L33-L63】

## 3. Frontend Validation
- **API route mismatches** (frontend expects endpoints that do not exist or have different prefixes):
  - Organisations: frontend calls `/api/v1/orgs/current`, `/api/v1/orgs/{id}/stats`, `/api/v1/orgs/{id}/retention`, but backend only exposes `/api/orgs` creation.【F:src/api/organisations.js†L1-L18】【F:backend/app/api/orgs.py†L10-L44】
  - Roles: frontend expects list/get/update/rubric routes under `/api/roles` and `/api/v1/roles`, but backend only exposes role creation at `/api/roles` and application listing at `/api/v1/roles/{id}/applications`.【F:src/api/roles.js†L1-L22】【F:backend/app/api/roles.py†L10-L36】【F:backend/app/api/applications.py†L80-L107】
  - Candidates: frontend expects a full CRUD surface (`/api/v1/candidates/*`) but backend only exposes `/api/v1/candidates/parse-resume`.【F:src/api/candidates.js†L1-L90】【F:backend/app/api/candidates.py†L8-L30】
  - Invitations: frontend expects validate/list/update under `/api/v1/invitations`, backend only exposes `/api/invitations` create.【F:src/api/invitations.js†L1-L15】【F:backend/app/api/invitations.py†L12-L37】
- **AI payload/response mismatches**:
  - Frontend sends extended `cagContext` fields (companyName, orgValues, interviewQuestions, etc.) that are ignored by the backend schema, and expects response fields like `competencyCovered` that the backend does not return. This results in silent feature loss and inconsistent UI behaviors.【F:src/lib/pages/LiveInterview.jsx†L396-L466】【F:backend/app/schemas/ai.py†L1-L19】【F:backend/app/api/ai.py†L20-L68】
- **Error handling gaps**: React Query hooks and pages (e.g., Org Dashboard) do not render error states; failed API calls will silently render empty states or generic fallbacks without user guidance.【F:src/lib/hooks/useOrgData.js†L1-L129】【F:src/lib/pages/OrgDashboard.jsx†L10-L83】

## 4. Cross-System Compatibility
- **Auth strategy**: JWT-only authentication is used in backend. Frontend stores tokens in localStorage and attaches `Authorization` headers, but backend also relies on refresh cookies; there is no clear refresh flow wiring in frontend beyond basic API calls.【F:backend/app/api/auth.py†L22-L75】【F:src/api/http.js†L1-L86】【F:src/api/auth.js†L1-L26】
- **Storage layer**: backend uses Azure Blob SAS URLs; frontend still uploads CVs to `/api/v1/candidates/cv` which does not exist in backend, causing storage desync and broken uploads.【F:backend/app/api/storage.py†L10-L52】【F:src/api/candidates.js†L78-L90】
- **AI payload shapes**: frontend sends enriched interview context, while backend accepts only minimal fields. If the frontend expects the AI to incorporate org/candidate context, it will not happen today.【F:src/lib/pages/LiveInterview.jsx†L396-L466】【F:backend/app/schemas/ai.py†L1-L19】

## 5. Configuration & Deployment
- **DATABASE_URL** resolves to SQLite only (backend + ACS service), no Postgres fallback present in runtime config or migrations.【F:backend/app/core/config.py†L1-L12】【F:backend/alembic.ini†L1-L3】【F:python-acs-service/app/config.py†L56-L69】
- **Startup scripts**: backend relies on Alembic upgrade during FastAPI startup; this is adequate for single-node SQLite but risky for multi-process deployments (migration conflicts).【F:backend/app/main.py†L28-L37】
- **Environment variables documentation**: `.env.example` lists critical Azure + JWT settings, but repo docs still reference Supabase/Postgres, creating confusion and conflicting guidance.【F:.env.example†L1-L25】【F:DEPLOYMENT_GUIDE.md†L92-L99】【F:MONITORING.md†L302-L371】
- **Dockerfile**: only `python-acs-service` has a Dockerfile, backend lacks one (deployment instructions may be incomplete).【F:python-acs-service/Dockerfile†L1-L25】

## 6. Missing or Weak Areas
- **Tests**: backend has a single test file; frontend tests only cover API endpoint wiring. Coverage is insufficient for migrations, auth, and AI workflows.【F:backend/tests/test_api_routes.py†L1-L58】【F:src/api/__tests__/endpoints.test.js†L1-L63】
- **Schema constraints**: Several business rules (e.g., preventing duplicate invitations per application, validating job roles) are not enforced at API layer or in DB constraints beyond basic FKs.【F:backend/app/api/invitations.py†L12-L37】【F:backend/app/api/applications.py†L18-L48】
- **Dead code / stale docs**: Supabase and TypeScript references persist across architecture docs; they mislead and imply old runtime dependencies. Needs cleanup to avoid operational confusion.【F:PYTHON_REBUILD_GUIDE.md†L60-L112】【F:ARCHITECTURE_DECISIONS.md†L12-L18】【F:MONITORING.md†L392-L419】

---

## Compatibility Risk Table
| Area | Risk | Why It Matters | Evidence |
| --- | --- | --- | --- |
| Frontend ↔ Backend API surface | **High** | Core routes used by UI do not exist in backend; app flows break immediately. | Org/roles/candidates/invitations mismatches.【F:src/api/organisations.js†L1-L18】【F:backend/app/api/orgs.py†L10-L44】【F:src/api/candidates.js†L1-L90】【F:backend/app/api/candidates.py†L8-L30】 |
| AI payload contract | **High** | Frontend sends context fields that backend ignores; AI results won’t match UX expectations. | LiveInterview payload vs schema.【F:src/lib/pages/LiveInterview.jsx†L396-L466】【F:backend/app/schemas/ai.py†L1-L19】 |
| Documentation integrity | **Medium** | Supabase/Postgres references contradict target architecture; risks misconfiguration. | Supabase/Postgres docs.【F:PYTHON_REBUILD_GUIDE.md†L60-L112】【F:MONITORING.md†L302-L371】 |
| JWT secret hygiene | **Medium** | `change-me` default in ACS service risks production compromise. | ACS config default secret.【F:python-acs-service/app/config.py†L33-L63】 |
| CORS configuration | **Medium** | Env parsing is ambiguous; easy to misconfigure and block frontend. | ALLOWED_ORIGINS config + middleware.【F:backend/app/core/config.py†L1-L20】【F:backend/app/main.py†L20-L27】 |

---

## Concrete File-Level Issues
1. `src/api/organisations.js` calls routes not implemented in `backend/app/api/orgs.py` (missing current membership, stats, retention).【F:src/api/organisations.js†L1-L18】【F:backend/app/api/orgs.py†L10-L44】
2. `src/api/roles.js` expects list/get/update/rubric routes not implemented in backend (only create exists).【F:src/api/roles.js†L1-L22】【F:backend/app/api/roles.py†L10-L36】
3. `src/api/candidates.js` expects extensive candidate CRUD and CV upload endpoints; backend only has parse-resume endpoint.【F:src/api/candidates.js†L1-L90】【F:backend/app/api/candidates.py†L8-L30】
4. `src/api/invitations.js` expects validate/list/update endpoints not in backend. Backend only has create under a different prefix.【F:src/api/invitations.js†L1-L15】【F:backend/app/api/invitations.py†L12-L37】
5. `src/lib/pages/LiveInterview.jsx` sends extra AI payload fields and expects `competencyCovered` in response which backend doesn’t return.【F:src/lib/pages/LiveInterview.jsx†L396-L466】【F:backend/app/api/ai.py†L20-L68】
6. `python-acs-service/app/config.py` uses a weak JWT secret default (`change-me`).【F:python-acs-service/app/config.py†L33-L63】

## Missing Features / Unfinished Migration Remnants
- Missing org membership endpoints and stats/retention APIs expected by frontend (org dashboard, settings, onboarding).【F:src/api/organisations.js†L1-L18】【F:backend/app/api/orgs.py†L10-L44】
- Missing candidate profile CRUD, education/employment, deletion requests, and CV upload APIs (entire candidate flows).【F:src/api/candidates.js†L1-L90】【F:backend/app/api/candidates.py†L8-L30】
- Missing invitation validation/status update endpoints; frontend assumes an invite lifecycle not in backend.【F:src/api/invitations.js†L1-L15】【F:backend/app/api/invitations.py†L12-L37】
- Documentation still includes Supabase/Edge Functions references that should be removed to avoid “shadow architecture.”【F:PYTHON_REBUILD_GUIDE.md†L60-L112】【F:MONITORING.md†L392-L419】

## Production Readiness Verdict
**Not Ready** — The API contract mismatch between frontend and backend alone is a ship-stopper. Documentation still references Supabase/Postgres, and the ACS service ships with a weak JWT secret default. The system is not deployable without significant remediation.

---

## Prioritized Remediation Checklist (Ruthless)
1. **Fix ALLOWED_ORIGINS parsing**: enforce JSON list or implement comma-separated parsing (backend + ACS service).【F:backend/app/core/config.py†L1-L20】【F:backend/app/main.py†L20-L27】【F:python-acs-service/app/config.py†L33-L63】
2. **Replace weak JWT defaults**: remove `change-me` and require secret validation in deployment pipelines.【F:python-acs-service/app/config.py†L33-L63】
3. **Align AI payload contracts**: either support `companyName`, `interviewQuestions`, etc. in backend schema or strip them from the frontend; add explicit response fields if the UI expects them.【F:src/lib/pages/LiveInterview.jsx†L396-L466】【F:backend/app/schemas/ai.py†L1-L19】
4. **Implement missing org/candidate/role/invitation endpoints** or remove frontend calls. Breaks core UI flows today.【F:src/api/organisations.js†L1-L18】【F:src/api/candidates.js†L1-L90】【F:src/api/roles.js†L1-L22】【F:src/api/invitations.js†L1-L15】
5. **Harden AI misconfiguration**: ensure 500 errors in production (already present) and align frontend error UX to prevent silent fallbacks.【F:backend/app/api/ai.py†L20-L68】【F:src/lib/pages/LiveInterview.jsx†L396-L520】
6. **Stabilize test dependencies**: ensure `email-validator` and `vitest` are present in CI; expand coverage for auth, migrations, and API contract tests.【F:backend/pyproject.toml†L10-L25】【F:package.json†L5-L26】

