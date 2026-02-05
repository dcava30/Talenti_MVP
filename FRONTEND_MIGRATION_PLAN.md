# Frontend Migration Plan (React → FastAPI + Azure + SQLite)

## Purpose
Provide a concrete migration plan for the React UI under `src/lib/` to align with the FastAPI backend, Azure Cognitive Services integrations, and a Python + SQLite data layer. This plan assumes the existing `apiClient` and `authClient` remain the canonical integration points. 

## Current Frontend Layout (Active UI Paths)
- `src/lib/App.tsx`, `src/lib/main.tsx`
- `src/lib/pages/*`
- `src/lib/hooks/*`
- `src/lib/components/*`
- Integration helpers:
  - `src/lib/apiClient.ts`
  - `src/lib/authClient.ts`

## Target Integration Pattern
### API Client Usage (Default)
- Use `apiClient` for all REST requests to FastAPI.
- Use `authClient` for login, refresh, logout, and `me` calls.
- Keep access token in memory per `authClient`, with optional hydration from secure storage once backend session handling is finalized.

### Token Handling
- `authClient.login(...)` returns `access_token` and configures `apiClient` headers.
- `authClient.refresh()` runs on app boot or route load to rehydrate sessions.
- Remove all direct Supabase calls in UI components and hooks.

## Hook Migration (Representative Examples)
| Hook | Current Integration | Target FastAPI Endpoint |
|------|----------------------|-------------------------|
| `src/lib/hooks/useAcsToken` | Edge function token fetch | `POST /api/acs/token` |
| `src/lib/hooks/useInvitations` | Supabase table + function calls | `GET /api/invitations`, `POST /api/invitations` |
| `src/lib/hooks/useCandidateData` | Supabase CRUD | `GET /api/candidates/:id`, `POST /api/candidates` |
| `src/lib/hooks/useAzureSpeech` | Edge function token | `POST /api/azure/speech/token` |
| `src/lib/hooks/useAzureAvatar` | Edge function session | `POST /api/azure/avatar/session` |

## Page-Level Migration (Representative Examples)
| Page | Current Integration | Target FastAPI Endpoint |
|------|----------------------|-------------------------|
| `src/lib/pages/CandidateInterview` | `/ai-interviewer` edge function | `POST /api/interviews/:id/start` or `POST /api/interviews/:id/stream` |
| `src/lib/pages/InterviewReport` | `score-interview` edge function | `POST /api/interviews/:id/score` |
| `src/lib/pages/InviteValidation` | invitation validation edge | `POST /api/invitations/validate` |
| `src/lib/pages/PracticeInterview` | practice edge function | `POST /api/interviews/practice` |

## Frontend Interaction Inventory (All Bases)
Use this as a coverage checklist to ensure FastAPI exposes every UI dependency currently in the React app.

### Core Hooks (Data/Identity/Azure)
- `useAcsCall`, `useAcsToken`: ACS call lifecycle and token issuance.
- `useAzureSpeech`, `useAzureAvatar`: Azure Speech and Avatar session/token endpoints.
- `useCandidateData`: candidate CRUD + profile data.
- `useInvitations`: invitation create/list/validate.
- `useInterviewContext`, `useInterviewPersistence`: interview session state, autosave, and resume.
- `useOrgData`: org/tenant data, settings, and admin meta.
- `useShortlist`: shortlist creation, list, and removal.
- `useAuditLog`: audit trail list/filter.
- `useDeletionRequests`: data retention + delete requests flow.

### UI Pages (Expected Backend Touchpoints)
- **Auth** (`src/lib/pages/Auth.tsx`): login/register, refresh, logout, `me`.
- **Org** (`OrgDashboard`, `OrgOnboarding`, `OrgSettings`): org profile, configuration, plan/limits.
- **Roles** (`NewRole`, `RoleDetails`, `EditRoleRubric`): role CRUD, rubric/rating scales.
- **Candidates** (`CandidatePortal`, `CandidateProfile`): candidate profile, status updates, history.
- **Invitations** (`InviteValidation`): invitation validation and accept flow.
- **Interviews** (`InterviewLobby`, `LiveInterview`, `CandidateInterview`, `InterviewComplete`, `PracticeInterview`, `PracticeInterviewComplete`): create/start/stream/complete/score, transcript retrieval.
- **Reports** (`InterviewReport`): scoring details + recommendations.
- **NotFound/Index** (`Index`, `NotFound`): minimal backend usage (routing only).

### UI Components With Backend Dependencies
- **Audit Trail** (`AuditTrailViewer`): audit log listing/filtering.
- **Retention & Deletion** (`DataRetentionSettings`, `OrgDataRetentionSettings`): retention policies and deletion requests.
- **Shortlists** (`ShortlistView`): shortlist CRUD.
- **Profile** (`ProfileManagement`): org/user profile update.
- **Invites** (`SendInvitationDialog`): invitation create.

### Integration Guarantees (Frontend ↔ Backend Contract)
- **Consistency**: align request/response payload shapes with existing UI expectations.
- **Errors**: standardize error envelopes and HTTP status codes for UI to render messages consistently.
- **Pagination & Filters**: define for list endpoints (audit logs, candidates, invitations, interviews).
- **Real-time/Streaming**: document SSE/WebSocket usage for interview streaming or transcript updates.
- **File/Blob Uploads**: if avatars/media/transcripts require upload, define multipart endpoints.
- **CORS & Auth**: allow the UI origin, ensure token refresh doesn’t break client boot.

## Backend API Contracts (Frontend-Visible)
### Auth
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
```

### Core Interview Flow
```
POST /api/interviews
GET  /api/interviews/:id
POST /api/interviews/:id/start
POST /api/interviews/:id/complete
POST /api/interviews/:id/score
```

### Candidates & Invitations
```
GET  /api/candidates/:id
POST /api/candidates
GET  /api/invitations
POST /api/invitations
POST /api/invitations/validate
```

### Azure Integrations
```
POST /api/azure/speech/token
POST /api/azure/avatar/session
POST /api/acs/token
POST /api/acs/call/start
POST /api/acs/call/end
```

## Additional API Surfaces (Derived from UI Features)
These should be validated against the existing hooks/pages and added to FastAPI contracts as needed.

### Orgs & Roles
```
GET  /api/orgs/:id
PATCH /api/orgs/:id
GET  /api/roles
POST /api/roles
GET  /api/roles/:id
PATCH /api/roles/:id
DELETE /api/roles/:id
```

### Shortlists, Audit Logs, Deletions
```
GET  /api/shortlists
POST /api/shortlists
DELETE /api/shortlists/:id
GET  /api/audit-logs
POST /api/deletion-requests
GET  /api/deletion-requests
```

### Interview Session State & Reporting
```
GET  /api/interviews/:id/transcript
GET  /api/interviews/:id/report
PATCH /api/interviews/:id
```

## SQLite Data Layer Expectations
- Preserve existing payload shapes and field names to minimize frontend churn (snake_case where applicable).
- Use SQLite + SQLAlchemy for core entities: `candidates`, `invitations`, `roles`, `interviews`, `interview_responses`, `reports`.
- Pydantic response models should mirror the payloads expected by existing hooks/pages.

## Sequenced Migration Plan
1. **Confirm frontend tree location**: keep working in `src/lib/pages`, `src/lib/hooks`, `src/lib/components`.
2. **Establish baseline API contracts** in FastAPI (even if mocked with in-memory responses) to unblock frontend refactors.
3. **Refactor hooks** to use `apiClient` + `authClient` for all data/identity operations.
4. **Replace edge function calls** in pages with FastAPI endpoints.
5. **Validate flows**: auth, interview creation, invitations, interview live session, scoring, reporting.
6. **Lock API schemas** and add integration tests (frontend contract tests / MSW).

## Open Items / Confirmations Needed
- **API base path**: confirm `/api` vs `/api/v1`.
- **SQLite usage**: confirm if SQLite is production or local-dev only.
- **Auth token storage**: decide in-memory vs secure cookie.
- **WebRTC/ACS**: confirm client requirements vs backend-generated tokens.
- **AI scoring & transcript streaming**: finalize response formats to keep UI stable.
