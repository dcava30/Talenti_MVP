# Python Migration Checklist

> **Track your progress** when migrating from Supabase Edge Functions to Python FastAPI.

---

## Overview

This checklist helps teams systematically migrate the Talenti backend from Supabase Edge Functions to Python FastAPI. Each section includes specific tasks with checkboxes to track completion.

**Related Documentation:**
- [PYTHON_REBUILD_GUIDE.md](PYTHON_REBUILD_GUIDE.md) — Complete code examples and patterns
- [API_REFERENCE.md](API_REFERENCE.md) — Original Edge Function specifications
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) — Database structure reference

---

## Phase 1: Project Setup

### Environment & Dependencies

- [ ] Create Python project directory structure
- [ ] Initialize virtual environment (`python -m venv venv`)
- [ ] Create `requirements.txt` with all dependencies
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Create `.env.example` template
- [ ] Configure `.env` with all required variables

### Core Configuration

- [ ] Create `app/config.py` with pydantic-settings
- [ ] Configure environment variable loading
- [ ] Set up logging with structlog
- [ ] Create `app/main.py` FastAPI application

### Middleware Setup

- [ ] Implement CORS middleware
- [ ] Create JWT authentication middleware (`app/middleware/auth.py`)
- [ ] Implement rate limiting with slowapi (`app/middleware/rate_limit.py`)
- [ ] Add error handling middleware

### Service Clients

- [ ] Create Supabase client service (`app/services/supabase_client.py`)
- [ ] Create AI Gateway service (`app/services/ai_gateway.py`)
- [ ] Create Azure ACS service (`app/services/acs_service.py`)
- [ ] Create Azure Speech service (`app/services/speech_service.py`)
- [ ] Create Azure Storage service (`app/services/storage_service.py`)
- [ ] Create Email service with Resend (`app/services/email_service.py`)
- [ ] Create PDF parsing service (`app/services/pdf_service.py`)

---

## Phase 2: Edge Function Migration

### AI Endpoints (`/api/ai/*`)

#### 1. AI Interviewer
**Original:** `supabase/functions/ai-interviewer/index.ts`
**Target:** `app/api/routes/ai.py` → `POST /api/ai/interviewer`

- [ ] Create Pydantic request/response models
- [ ] Implement system prompt builder
- [ ] Implement non-streaming endpoint
- [ ] Implement streaming endpoint (`/api/ai/interviewer/stream`)
- [ ] Add transcript segment saving
- [ ] Add rate limiting (20/minute)
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Verify with frontend

#### 2. Score Interview
**Original:** `supabase/functions/score-interview/index.ts`
**Target:** `app/api/routes/ai.py` → `POST /api/ai/score`

- [ ] Create scoring request/response models
- [ ] Implement tool calling schema for structured output
- [ ] Implement transcript retrieval
- [ ] Implement multi-dimensional scoring logic
- [ ] Add custom rubric support
- [ ] Save scores to `interview_scores` table
- [ ] Save dimensions to `score_dimensions` table
- [ ] Add rate limiting (10/minute)
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Verify with frontend

#### 3. Parse Resume
**Original:** `supabase/functions/parse-resume/index.ts`
**Target:** `app/api/routes/ai.py` → `POST /api/ai/parse-resume`

- [ ] Create parsed resume response model
- [ ] Implement PDF text extraction (pdfplumber)
- [ ] Implement AI parsing with tool calling
- [ ] Handle file upload validation
- [ ] Add rate limiting (10/minute)
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Verify with frontend

#### 4. Extract Requirements
**Original:** `supabase/functions/extract-requirements/index.ts`
**Target:** `app/api/routes/ai.py` → `POST /api/ai/extract-requirements`

- [ ] Create requirements request/response models
- [ ] Implement tool calling schema
- [ ] Implement extraction logic
- [ ] Add rate limiting (20/minute)
- [ ] Write unit tests
- [ ] Verify with frontend

#### 5. Generate Shortlist
**Original:** `supabase/functions/generate-shortlist/index.ts`
**Target:** `app/api/routes/ai.py` → `POST /api/ai/generate-shortlist`

- [ ] Create shortlist request/response models
- [ ] Implement candidate query logic
- [ ] Implement score-based ranking
- [ ] Add rate limiting (5/minute)
- [ ] Write unit tests
- [ ] Verify with frontend

---

### Azure Communication Services (`/api/acs/*`)

#### 6. ACS Token Generator
**Original:** `supabase/functions/acs-token-generator/index.ts`
**Target:** `app/api/routes/acs.py` → `POST /api/acs/token`

- [ ] Create token request/response models
- [ ] Initialize ACS Identity Client
- [ ] Implement user identity creation
- [ ] Implement token generation with scopes
- [ ] Add rate limiting (60/minute)
- [ ] Write unit tests
- [ ] Verify with frontend video calling

#### 7. ACS Webhook Handler
**Original:** `supabase/functions/acs-webhook-handler/index.ts`
**Target:** `app/api/routes/acs.py` → `POST /api/acs/webhook`

- [ ] Implement Event Grid signature verification
- [ ] Handle subscription validation events
- [ ] Implement `CallStarted` event handler
- [ ] Implement `CallEnded` event handler
- [ ] Implement `RecordingFileStatusUpdated` handler
- [ ] Update interview status in database
- [ ] Use background tasks for async processing
- [ ] Write unit tests
- [ ] Configure Azure Event Grid subscription

---

### Azure Speech (`/api/azure/*`)

#### 8. Azure Speech Token
**Original:** `supabase/functions/azure-speech-token/index.ts`
**Target:** `app/api/routes/azure_speech.py` → `GET /api/azure/speech-token`

- [ ] Create token response model
- [ ] Implement Azure Speech token fetch
- [ ] Handle region configuration
- [ ] Add rate limiting (60/minute)
- [ ] Write unit tests
- [ ] Verify with frontend speech recognition

---

### Invitations (`/api/invitations/*`)

#### 9. Send Invitation
**Original:** `supabase/functions/send-invitation/index.ts`
**Target:** `app/api/routes/invitations.py` → `POST /api/invitations/send`

- [ ] Create invitation request/response models
- [ ] Implement secure token generation
- [ ] Implement invitation record creation
- [ ] Build HTML email template
- [ ] Integrate Resend email sending
- [ ] Handle email send failures gracefully
- [ ] Update invitation status
- [ ] Add rate limiting (30/minute)
- [ ] Write unit tests
- [ ] Test email delivery

---

### Organisations (`/api/organisations/*`)

#### 10. Create Organisation
**Original:** `supabase/functions/create-organisation/index.ts`
**Target:** `app/api/routes/organisations.py` → `POST /api/organisations`

- [ ] Create organisation request/response models
- [ ] Implement organisation creation
- [ ] Add user as org_admin
- [ ] Create user_roles entry
- [ ] Add rate limiting (10/minute)
- [ ] Write unit tests
- [ ] Verify with frontend onboarding

---

### Admin (`/api/admin/*`)

#### 11. Data Retention Cleanup
**Original:** `supabase/functions/data-retention-cleanup/index.ts`
**Target:** `app/api/routes/admin.py` → `POST /api/admin/data-cleanup`

- [ ] Create cleanup request/response models
- [ ] Implement expired recordings query
- [ ] Implement Azure Blob Storage deletion
- [ ] Implement database record updates
- [ ] Support org-specific retention settings
- [ ] Add async/background task support
- [ ] Require org_admin role
- [ ] Add rate limiting (1/minute)
- [ ] Write unit tests
- [ ] Set up scheduled job (optional)

---

## Phase 3: Testing

### Unit Tests

- [ ] Set up pytest configuration (`tests/conftest.py`)
- [ ] Create mock fixtures for Supabase
- [ ] Create mock fixtures for AI service
- [ ] Create mock fixtures for Azure services
- [ ] Achieve >80% code coverage

### Integration Tests

- [ ] Test AI interviewer with real AI gateway
- [ ] Test ACS token generation
- [ ] Test email sending (sandbox)
- [ ] Test database operations

### Load Testing

- [ ] Set up load testing tool (locust/k6)
- [ ] Test AI endpoints under load
- [ ] Test rate limiting behavior
- [ ] Identify bottlenecks

---

## Phase 4: Deployment

### Docker Configuration

- [ ] Create `Dockerfile`
- [ ] Create `docker-compose.yml`
- [ ] Create `.dockerignore`
- [ ] Test local Docker build
- [ ] Test local Docker run

### Azure Container Apps

- [ ] Create Azure resource group
- [ ] Create Container Apps environment
- [ ] Create Azure Container Registry
- [ ] Push Docker image to ACR
- [ ] Deploy Container App
- [ ] Configure environment variables
- [ ] Configure secrets
- [ ] Configure custom domain (optional)
- [ ] Configure SSL certificate

### CI/CD Pipeline

- [ ] Create GitHub Actions workflow
- [ ] Add automated testing stage
- [ ] Add Docker build stage
- [ ] Add ACR push stage
- [ ] Add Container Apps deployment stage
- [ ] Configure environment secrets
- [ ] Test full pipeline

---

## Phase 5: Cutover

### Pre-Cutover

- [ ] Run parallel testing (both backends)
- [ ] Verify all endpoints match behavior
- [ ] Document any API changes
- [ ] Update frontend API base URL configuration
- [ ] Prepare rollback plan

### Cutover

- [ ] Update DNS/routing to Python backend
- [ ] Monitor error rates
- [ ] Monitor latency
- [ ] Verify all features work
- [ ] Keep Edge Functions as fallback

### Post-Cutover

- [ ] Monitor for 24-48 hours
- [ ] Address any issues
- [ ] Disable Edge Functions (after stability confirmed)
- [ ] Update documentation
- [ ] Archive Edge Function code

---

## Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| 1. Project Setup | ⬜ Not Started | 0/20 |
| 2. Edge Functions | ⬜ Not Started | 0/11 endpoints |
| 3. Testing | ⬜ Not Started | 0/12 |
| 4. Deployment | ⬜ Not Started | 0/18 |
| 5. Cutover | ⬜ Not Started | 0/10 |

**Overall Progress:** 0/71 tasks (0%)

---

## Endpoint Migration Status

| # | Endpoint | Edge Function | Python Route | Status |
|---|----------|---------------|--------------|--------|
| 1 | AI Interviewer | `ai-interviewer` | `/api/ai/interviewer` | ⬜ |
| 2 | Score Interview | `score-interview` | `/api/ai/score` | ⬜ |
| 3 | Parse Resume | `parse-resume` | `/api/ai/parse-resume` | ⬜ |
| 4 | Extract Requirements | `extract-requirements` | `/api/ai/extract-requirements` | ⬜ |
| 5 | Generate Shortlist | `generate-shortlist` | `/api/ai/generate-shortlist` | ⬜ |
| 6 | ACS Token | `acs-token-generator` | `/api/acs/token` | ⬜ |
| 7 | ACS Webhook | `acs-webhook-handler` | `/api/acs/webhook` | ⬜ |
| 8 | Speech Token | `azure-speech-token` | `/api/azure/speech-token` | ⬜ |
| 9 | Send Invitation | `send-invitation` | `/api/invitations/send` | ⬜ |
| 10 | Create Org | `create-organisation` | `/api/organisations` | ⬜ |
| 11 | Data Cleanup | `data-retention-cleanup` | `/api/admin/data-cleanup` | ⬜ |

**Legend:** ⬜ Not Started | 🟡 In Progress | ✅ Complete | ❌ Blocked

---

## Notes & Decisions

Use this section to document decisions, blockers, and learnings during migration.

### Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| | | |

### Blockers

| Date | Blocker | Status | Resolution |
|------|---------|--------|------------|
| | | | |

### Learnings

| Date | Learning |
|------|----------|
| | |

---

## Team Assignments

| Endpoint | Assigned To | Due Date | Status |
|----------|-------------|----------|--------|
| AI Interviewer | | | ⬜ |
| Score Interview | | | ⬜ |
| Parse Resume | | | ⬜ |
| Extract Requirements | | | ⬜ |
| Generate Shortlist | | | ⬜ |
| ACS Token | | | ⬜ |
| ACS Webhook | | | ⬜ |
| Speech Token | | | ⬜ |
| Send Invitation | | | ⬜ |
| Create Org | | | ⬜ |
| Data Cleanup | | | ⬜ |

---

*Last updated: January 2025*
