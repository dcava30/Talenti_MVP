# Talenti AI Interview Platform - Python Migration Guide

## Migration Prompt for Software Engineering Team

**Document Version:** 1.0  
**Created:** January 2026  
**Target Completion:** TBD  
**Classification:** Technical Implementation Guide

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current System Inventory](#2-current-system-inventory)
3. [Azure Services Architecture](#3-azure-services-architecture)
4. [Python Application Architecture](#4-python-application-architecture)
5. [API Endpoint Specifications](#5-api-endpoint-specifications)
6. [Azure OpenAI Integration](#6-azure-openai-integration)
7. [Azure Speech Services](#7-azure-speech-services)
8. [Azure Communication Services Integration](#8-azure-communication-services-integration)
9. [Document Processing](#9-document-processing)
10. [Data Retention & GDPR Compliance](#10-data-retention--gdpr-compliance)
11. [Authentication & Security](#11-authentication--security)
12. [Deployment Configuration](#12-deployment-configuration)
- [Appendix A: Environment Variables](#appendix-a-environment-variables)
- [Appendix B: Requirements](#appendix-b-requirements)
- [Appendix C: Database Pydantic Models](#appendix-c-database-pydantic-models)
- [Appendix D: Frontend Integration Guide](#appendix-d-frontend-integration-guide)

---

# 1. Executive Summary

## 1.1 Project Overview

Talenti is an AI-powered interview platform that conducts automated video interviews with candidates, provides real-time transcription, scores responses using custom rubrics, and generates comprehensive interview reports. The platform serves Australian enterprise clients with strict data residency and GDPR compliance requirements.

## 1.2 Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CURRENT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐     ┌──────────────────────────────────────┐  │
│  │   React 18 SPA   │────▶│     Supabase Edge Functions (Deno)   │  │
│  │   TypeScript     │     │                                      │  │
│  │   Vite           │     │  • ai-interviewer (273 lines)        │  │
│  │   Tailwind CSS   │     │  • score-interview (262 lines)       │  │
│  │   shadcn/ui      │     │  • parse-resume (354 lines)          │  │
│  └────────┬─────────┘     │  • extract-requirements (186 lines)  │  │
│           │               │  • generate-shortlist (402 lines)    │  │
│           │               │  • send-invitation (175 lines)       │  │
│           ▼               │  • azure-speech-token (115 lines)    │  │
│  ┌──────────────────┐     │  • acs-token-generator (284 lines)   │  │
│  │  Custom Hooks    │     │  • acs-webhook-handler (217 lines)   │  │
│  │  • useAzureSpeech│     │  • data-retention-cleanup (429 lines)│  │
│  │  • useAzureAvatar│     │  • create-organisation (122 lines)   │  │
│  │  • useAcsCall    │     └──────────────────────────────────────┘  │
│  │  • useAcsToken   │                      │                        │
│  └──────────────────┘                      ▼                        │
│           │               ┌──────────────────────────────────────┐  │
│           │               │         Supabase PostgreSQL          │  │
│           │               │         17 Tables + RLS              │  │
│           ▼               └──────────────────────────────────────┘  │
│  ┌──────────────────┐                      │                        │
│  │ Azure Services   │◀─────────────────────┘                        │
│  │ • Speech SDK     │                                               │
│  │ • Avatar API     │     ┌──────────────────────────────────────┐  │
│  │ • ACS Calling    │     │     Python ACS Service (Existing)    │  │
│  └──────────────────┘     │     FastAPI + Call Automation        │  │
│                           └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 1.3 Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TARGET ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐     ┌──────────────────────────────────────┐  │
│  │   React 18 SPA   │────▶│     Python FastAPI Backend           │  │
│  │   (Unchanged)    │     │     (Azure Container Apps)           │  │
│  │                  │     │                                      │  │
│  │                  │     │  ┌────────────────────────────────┐  │  │
│  └────────┬─────────┘     │  │         API Routes             │  │  │
│           │               │  │  /api/v1/interview/*           │  │  │
│           │               │  │  /api/v1/scoring/*             │  │  │
│           │               │  │  /api/v1/resume/*              │  │  │
│           ▼               │  │  /api/v1/speech/*              │  │  │
│  ┌──────────────────┐     │  │  /api/v1/acs/*                 │  │  │
│  │  Custom Hooks    │     │  │  /api/v1/webhooks/*            │  │  │
│  │  (Updated URLs)  │     │  └────────────────────────────────┘  │  │
│  └──────────────────┘     │                 │                    │  │
│           │               │                 ▼                    │  │
│           │               │  ┌────────────────────────────────┐  │  │
│           │               │  │       Azure Services           │  │  │
│           │               │  │  • Azure OpenAI (GPT-4o)       │  │  │
│           │               │  │  • Azure Speech SDK            │  │  │
│           │               │  │  • Azure Document Intelligence │  │  │
│           │               │  │  • Azure Blob Storage          │  │  │
│           │               │  │  • Azure Communication Services│  │  │
│           │               │  └────────────────────────────────┘  │  │
│           │               └──────────────────────────────────────┘  │
│           │                                │                        │
│           │                                ▼                        │
│           │               ┌──────────────────────────────────────┐  │
│           └──────────────▶│    Supabase PostgreSQL (Unchanged)   │  │
│                           │    OR Azure SQL Database             │  │
│                           └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 1.4 Migration Scope

| Component | Action | Effort |
|-----------|--------|--------|
| React Frontend | Minimal changes (API URLs) | Low |
| 12 Edge Functions | Migrate to FastAPI | High |
| Existing Python Service | Extend and integrate | Medium |
| Database Schema | Preserve (add Python models) | Low |
| Azure Integrations | Native Python SDK | Medium |
| Authentication | Supabase JWT validation | Low |

## 1.5 Key Migration Drivers

1. **Azure-Native Deployment**: Enterprise clients require Azure-hosted solutions
2. **Team Skillset**: Python expertise available for maintenance
3. **Performance**: Direct Azure SDK integration for lower latency
4. **Compliance**: Australian data residency with Azure Australia East
5. **Scalability**: Azure Container Apps for enterprise workloads

## 1.6 Success Criteria

- [ ] All 12 edge functions migrated to Python endpoints
- [ ] Interview turn latency maintained at <800ms
- [ ] Full GDPR compliance with data retention automation
- [ ] Zero downtime migration with feature parity
- [ ] Comprehensive test coverage (>80%)
- [ ] Production deployment to Azure Container Apps

---

# 2. Current System Inventory

## 2.1 Frontend Components (Preserve As-Is)

### Pages (24 total)

| Page | Route | Purpose |
|------|-------|---------|
| `Index.tsx` | `/` | Landing page |
| `Auth.tsx` | `/auth` | Authentication |
| `CandidatePortal.tsx` | `/candidate` | Candidate dashboard |
| `CandidateProfile.tsx` | `/candidate/profile` | Profile management |
| `CandidateInterview.tsx` | `/candidate/interview/:id` | Interview entry |
| `InterviewLobby.tsx` | `/interview/:id/lobby` | Pre-interview setup |
| `LiveInterview.tsx` | `/interview/:id/live` | Active interview |
| `InterviewComplete.tsx` | `/interview/:id/complete` | Post-interview |
| `PracticeInterview.tsx` | `/practice` | Practice mode |
| `PracticeInterviewComplete.tsx` | `/practice/complete` | Practice results |
| `InviteValidation.tsx` | `/invite/:token` | Invitation validation |
| `OrgDashboard.tsx` | `/org` | Organization dashboard |
| `OrgSettings.tsx` | `/org/settings` | Organization settings |
| `OrgOnboarding.tsx` | `/org/onboarding` | Organization setup |
| `NewRole.tsx` | `/org/roles/new` | Create job role |
| `RoleDetails.tsx` | `/org/roles/:id` | View job role |
| `EditRoleRubric.tsx` | `/org/roles/:id/rubric` | Edit scoring rubric |
| `InterviewReport.tsx` | `/org/interviews/:id/report` | Interview report |
| `NotFound.tsx` | `*` | 404 page |

### Custom Hooks (Azure Integration)

```typescript
// These hooks call the backend - update URLs to Python endpoints

// src/hooks/useAzureSpeech.ts
// - Fetches speech tokens from /api/v1/speech/token
// - Configures Azure Speech SDK for STT/TTS

// src/hooks/useAzureAvatar.ts  
// - Manages Azure AI Avatar WebRTC connection
// - Handles ICE negotiation and synthesis

// src/hooks/useAcsToken.ts
// - Fetches ACS tokens from /api/v1/acs/token
// - Returns CommunicationUserIdentifier

// src/hooks/useAcsCall.ts
// - Manages ACS call lifecycle
// - Handles call state and events

// src/hooks/useSpeechRecognition.ts
// - Real-time speech-to-text
// - Transcript segment management

// src/hooks/useSpeechSynthesis.ts
// - Text-to-speech for AI responses
// - Voice selection and SSML
```

## 2.2 Edge Functions to Migrate

### 2.2.1 AI Interviewer (`supabase/functions/ai-interviewer/index.ts`)

**Purpose**: Manages real-time AI conversation during interviews

**Current Implementation**:
```typescript
// Key interfaces
interface InterviewMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface CAGContext {
  jobTitle: string;
  jobDescription: string;
  requirements: {
    skills: string[];
    experience: string[];
    qualifications: string[];
    responsibilities: string[];
    interviewQuestions: string[];
  };
  companyValues: string[];
  candidateContext: {
    name: string;
    resumeSummary: string;
    applicationId: string;
  };
  interviewProgress: {
    questionsAsked: number;
    competenciesCovered: string[];
    currentPhase: "introduction" | "technical" | "behavioral" | "closing";
  };
}
```

**Migration Target**: `POST /api/v1/interview/chat`

**Key Features to Preserve**:
- Streaming response support
- Competency detection from responses
- Phase-aware questioning (introduction → technical → behavioral → closing)
- Rate limiting (10 requests/minute per IP)

---

### 2.2.2 Score Interview (`supabase/functions/score-interview/index.ts`)

**Purpose**: Analyzes interview transcripts and generates scores

**Current Implementation**:
```typescript
interface TranscriptSegment {
  speaker: "interviewer" | "candidate";
  content: string;
  timestamp: number;
}

interface ScoringDimension {
  name: string;
  description: string;
  weight: number;
}

interface ScoringRequest {
  transcript: TranscriptSegment[];
  rubric?: ScoringDimension[];
  jobTitle: string;
  jobDescription: string;
}

// Default scoring dimensions
const DEFAULT_DIMENSIONS = [
  { name: "Technical Competency", description: "...", weight: 0.25 },
  { name: "Problem Solving", description: "...", weight: 0.20 },
  { name: "Communication", description: "...", weight: 0.20 },
  { name: "Cultural Fit", description: "...", weight: 0.15 },
  { name: "Leadership Potential", description: "...", weight: 0.10 },
  { name: "Adaptability", description: "...", weight: 0.10 }
];
```

**Migration Target**: `POST /api/v1/scoring/analyze`

**Key Features to Preserve**:
- Custom rubric support
- Weighted scoring calculation
- Evidence citation with quotes
- Narrative summary generation
- Anti-cheat risk assessment

---

### 2.2.3 Parse Resume (`supabase/functions/parse-resume/index.ts`)

**Purpose**: Extracts structured data from PDF resumes

**Current Implementation**:
```typescript
interface ParsedResume {
  personalInfo: {
    fullName: string;
    email: string;
    phone: string;
    location: string;
    linkedIn?: string;
    portfolio?: string;
  };
  employment: Array<{
    company: string;
    title: string;
    startDate: string;
    endDate: string | null;
    description: string;
    achievements: string[];
  }>;
  education: Array<{
    institution: string;
    degree: string;
    field: string;
    graduationDate: string;
    gpa?: number;
  }>;
  skills: {
    technical: string[];
    soft: string[];
    languages: string[];
    certifications: string[];
  };
  summary: string;
}
```

**Migration Target**: `POST /api/v1/resume/parse`

**Key Features to Preserve**:
- PDF to base64 conversion
- Supabase Storage integration
- AI-powered extraction with tool calling
- Structured output validation

---

### 2.2.4 Extract Requirements (`supabase/functions/extract-requirements/index.ts`)

**Purpose**: Parses job descriptions to extract structured requirements

**Current Implementation**:
```typescript
interface ExtractedRequirements {
  skills: string[];
  experience: string[];
  qualifications: string[];
  responsibilities: string[];
  interviewQuestions: string[];
}
```

**Migration Target**: `POST /api/v1/jobs/extract`

**Key Features to Preserve**:
- Natural language processing of JDs
- Interview question generation
- Skill categorization

---

### 2.2.5 Generate Shortlist (`supabase/functions/generate-shortlist/index.ts`)

**Purpose**: Ranks candidates using semantic matching

**Migration Target**: `POST /api/v1/shortlist/generate`

**Key Features to Preserve**:
- Multi-candidate comparison
- Requirement matching scores
- Explanation generation
- Ranking with justification

---

### 2.2.6 Send Invitation (`supabase/functions/send-invitation/index.ts`)

**Purpose**: Sends interview invitation emails

**Current Implementation**:
```typescript
interface SendInvitationRequest {
  applicationId: string;
  candidateEmail: string;
  roleTitle: string;
  companyName: string;
  expiresInDays?: number;
}
```

**Migration Target**: `POST /api/v1/invitations/send`

**Key Features to Preserve**:
- Secure token generation
- Expiration management
- HTML email templates
- Status tracking (pending → sent → opened)

---

### 2.2.7 Azure Speech Token (`supabase/functions/azure-speech-token/index.ts`)

**Purpose**: Generates Azure Speech authentication tokens

**Migration Target**: `GET /api/v1/speech/token`

**Key Features to Preserve**:
- Token caching (10-minute expiry)
- Rate limiting per IP
- Region configuration

---

### 2.2.8 ACS Token Generator (`supabase/functions/acs-token-generator/index.ts`)

**Purpose**: Creates ACS identities and access tokens

**Current Implementation**:
```typescript
interface CommunicationIdentityToken {
  token: string;
  expiresOn: string;
  user: {
    communicationUserId: string;
  };
}
```

**Migration Target**: `POST /api/v1/acs/token`

**Key Features to Preserve**:
- Identity creation
- VOIP scope tokens
- HMAC-SHA256 authentication
- Connection string parsing

---

### 2.2.9 ACS Webhook Handler (`supabase/functions/acs-webhook-handler/index.ts`)

**Purpose**: Processes Azure Communication Services events

**Event Types Handled**:
- `Microsoft.EventGrid.SubscriptionValidationEvent`
- `Microsoft.Communication.CallStarted`
- `Microsoft.Communication.CallEnded`
- `Microsoft.Communication.ParticipantJoined`
- `Microsoft.Communication.ParticipantLeft`
- `Microsoft.Communication.RecordingFileStatusUpdated`
- `Microsoft.Communication.PlayCompleted`
- `Microsoft.Communication.RecognizeCompleted`

**Migration Target**: `POST /api/v1/webhooks/acs`

**Key Features to Preserve**:
- EventGrid validation handshake
- Interview status updates
- Recording URL capture
- Correlation ID tracking

---

### 2.2.10 Data Retention Cleanup (`supabase/functions/data-retention-cleanup/index.ts`)

**Purpose**: GDPR-compliant data lifecycle management

**Actions Supported**:
1. `cleanup` - Delete old recordings per org retention policy
2. `process_deletions` - Handle user deletion requests

**Deletion Types**:
- `full_deletion` - Remove all user data
- `recording_only` - Delete only recordings
- `anonymize` - Anonymize personal data

**Migration Target**: `POST /api/v1/admin/cleanup`

**Key Features to Preserve**:
- Organization-specific retention days
- Cascade deletion logic
- Audit trail logging
- Storage file cleanup

---

### 2.2.11 Create Organisation (`supabase/functions/create-organisation/index.ts`)

**Purpose**: Onboards new organizations

**Migration Target**: `POST /api/v1/organisations`

**Key Features to Preserve**:
- Admin user assignment
- Default settings initialization
- Billing setup

---

## 2.3 Database Schema

### Tables (17 total)

```sql
-- Core Entities
organisations (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  industry TEXT,
  logo_url TEXT,
  website TEXT,
  billing_email TEXT,
  billing_address TEXT,
  recording_retention_days INTEGER DEFAULT 60,
  values_framework JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

org_users (
  id UUID PRIMARY KEY,
  organisation_id UUID REFERENCES organisations(id),
  user_id UUID NOT NULL,
  role TEXT DEFAULT 'viewer', -- admin, recruiter, viewer
  created_at TIMESTAMPTZ
)

job_roles (
  id UUID PRIMARY KEY,
  organisation_id UUID REFERENCES organisations(id),
  title TEXT NOT NULL,
  description TEXT,
  department TEXT,
  location TEXT,
  industry TEXT,
  employment_type TEXT,
  work_type TEXT,
  salary_range_min INTEGER,
  salary_range_max INTEGER,
  requirements JSONB,
  scoring_rubric JSONB,
  interview_structure JSONB,
  status job_role_status DEFAULT 'draft',
  created_by UUID,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

applications (
  id UUID PRIMARY KEY,
  job_role_id UUID REFERENCES job_roles(id),
  candidate_id UUID NOT NULL,
  status TEXT DEFAULT 'pending',
  match_score DECIMAL,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

interviews (
  id UUID PRIMARY KEY,
  application_id UUID REFERENCES applications(id),
  status interview_status DEFAULT 'invited',
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,
  recording_url TEXT,
  recording_deleted_at TIMESTAMPTZ,
  anti_cheat_signals JSONB,
  metadata JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- Candidate Data
candidate_profiles (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  phone TEXT,
  suburb TEXT,
  state TEXT,
  postcode TEXT,
  country TEXT,
  linkedin_url TEXT,
  portfolio_url TEXT,
  cv_file_path TEXT,
  cv_uploaded_at TIMESTAMPTZ,
  availability TEXT,
  work_mode TEXT,
  work_rights TEXT,
  gpa_wam DECIMAL,
  profile_visibility TEXT,
  visibility_settings JSONB,
  paused_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

candidate_skills (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  skill_name TEXT NOT NULL,
  skill_type TEXT NOT NULL, -- technical, soft
  proficiency_level TEXT,
  created_at TIMESTAMPTZ
)

education (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  institution TEXT NOT NULL,
  degree TEXT NOT NULL,
  field_of_study TEXT,
  start_date DATE,
  end_date DATE,
  is_current BOOLEAN,
  created_at TIMESTAMPTZ
)

employment_history (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  company_name TEXT NOT NULL,
  job_title TEXT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE,
  is_current BOOLEAN,
  description TEXT,
  created_at TIMESTAMPTZ
)

candidate_dei (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE,
  gender TEXT,
  ethnicity TEXT,
  disability_status TEXT,
  veteran_status TEXT,
  created_at TIMESTAMPTZ
)

-- Interview Scoring
interview_scores (
  id UUID PRIMARY KEY,
  interview_id UUID REFERENCES interviews(id) UNIQUE,
  overall_score DECIMAL,
  narrative_summary TEXT,
  candidate_feedback TEXT,
  anti_cheat_risk_level TEXT,
  scored_by TEXT,
  model_version TEXT,
  prompt_version TEXT,
  rubric_version TEXT,
  human_override BOOLEAN,
  human_override_by UUID,
  human_override_reason TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

score_dimensions (
  id UUID PRIMARY KEY,
  interview_id UUID REFERENCES interviews(id),
  dimension TEXT NOT NULL,
  score DECIMAL NOT NULL,
  weight DECIMAL,
  evidence TEXT,
  cited_quotes JSONB,
  created_at TIMESTAMPTZ
)

transcript_segments (
  id UUID PRIMARY KEY,
  interview_id UUID REFERENCES interviews(id),
  speaker TEXT NOT NULL, -- interviewer, candidate
  content TEXT NOT NULL,
  start_time_ms INTEGER NOT NULL,
  end_time_ms INTEGER,
  confidence DECIMAL,
  created_at TIMESTAMPTZ
)

-- Invitations
invitations (
  id UUID PRIMARY KEY,
  application_id UUID REFERENCES applications(id),
  token TEXT NOT NULL UNIQUE,
  status invitation_status DEFAULT 'pending',
  expires_at TIMESTAMPTZ NOT NULL,
  sent_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  email_template TEXT,
  created_at TIMESTAMPTZ
)

-- Practice Mode
practice_interviews (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  sample_role_type TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,
  feedback JSONB,
  created_at TIMESTAMPTZ
)

-- System
user_roles (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  role app_role NOT NULL,
  created_at TIMESTAMPTZ
)

audit_log (
  id UUID PRIMARY KEY,
  user_id UUID,
  organisation_id UUID REFERENCES organisations(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  old_values JSONB,
  new_values JSONB,
  ip_address TEXT,
  created_at TIMESTAMPTZ
)

data_deletion_requests (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  request_type TEXT DEFAULT 'full_deletion',
  status TEXT DEFAULT 'pending',
  reason TEXT,
  notes TEXT,
  requested_at TIMESTAMPTZ,
  processed_at TIMESTAMPTZ,
  processed_by UUID
)
```

### Enums

```sql
CREATE TYPE app_role AS ENUM ('org_admin', 'org_recruiter', 'org_viewer', 'candidate');

CREATE TYPE interview_status AS ENUM (
  'invited', 'scheduled', 'in_progress', 'completed', 'cancelled', 'expired'
);

CREATE TYPE invitation_status AS ENUM (
  'pending', 'sent', 'delivered', 'opened', 'bounced', 'expired'
);

CREATE TYPE job_role_status AS ENUM ('draft', 'active', 'paused', 'closed');
```

### Helper Functions

```sql
-- Check if user belongs to organization
CREATE FUNCTION user_belongs_to_org(_org_id UUID, _user_id UUID) 
RETURNS BOOLEAN AS $$
  SELECT EXISTS(
    SELECT 1 FROM org_users 
    WHERE organisation_id = _org_id AND user_id = _user_id
  );
$$ LANGUAGE sql SECURITY DEFINER;

-- Get user's role in organization
CREATE FUNCTION user_org_role(_org_id UUID, _user_id UUID)
RETURNS TEXT AS $$
  SELECT role FROM org_users 
  WHERE organisation_id = _org_id AND user_id = _user_id;
$$ LANGUAGE sql SECURITY DEFINER;

-- Get user's organization ID
CREATE FUNCTION get_user_org_id(_user_id UUID)
RETURNS UUID AS $$
  SELECT organisation_id FROM org_users 
  WHERE user_id = _user_id 
  LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER;

-- Check if user has specific app role
CREATE FUNCTION has_role(_role app_role, _user_id UUID)
RETURNS BOOLEAN AS $$
  SELECT EXISTS(
    SELECT 1 FROM user_roles 
    WHERE user_id = _user_id AND role = _role
  );
$$ LANGUAGE sql SECURITY DEFINER;
```

---

# 3. Azure Services Architecture

## 3.1 Service Mapping

| Current Service | Azure Replacement | Python SDK | Purpose |
|-----------------|-------------------|------------|---------|
| Lovable AI Gateway | Azure OpenAI | `openai` (azure config) | AI conversations, scoring, parsing |
| Browser Speech API | Azure Speech SDK | `azure-cognitiveservices-speech` | STT/TTS |
| Avatar WebRTC | Azure AI Avatar | Same SDK + ICE | Animated interviewer |
| Supabase Edge Functions | FastAPI | `fastapi` | API endpoints |
| Supabase Storage | Azure Blob Storage | `azure-storage-blob` | File storage |
| ACS Calling | Azure Communication Services | `azure-communication-*` | VoIP calls |
| Resend | Azure Communication Email | `azure-communication-email` | Transactional email |

## 3.2 Azure Resource Requirements

### Resource Group: `talenti-prod-rg`

| Resource | SKU | Region | Purpose |
|----------|-----|--------|---------|
| Azure OpenAI | S0 | Australia East | GPT-4o deployment |
| Azure Speech | S0 | Australia East | STT/TTS/Avatar |
| Azure Communication Services | Standard | Australia East | VoIP |
| Azure Container Apps | Consumption | Australia East | API hosting |
| Azure Container Registry | Basic | Australia East | Docker images |
| Azure Key Vault | Standard | Australia East | Secrets |
| Azure Blob Storage | Standard LRS | Australia East | File storage |
| Azure Cache for Redis | Basic C0 | Australia East | Rate limiting |
| Application Insights | Standard | Australia East | Monitoring |

### Azure OpenAI Deployments

| Deployment Name | Model | TPM | Purpose |
|-----------------|-------|-----|---------|
| `gpt-4o` | gpt-4o (2024-05-13) | 150K | Interview & scoring |
| `gpt-4o-mini` | gpt-4o-mini | 300K | Resume parsing |

---

# 4. Python Application Architecture

## 4.1 Directory Structure

```
talenti-python-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Pydantic settings
│   ├── dependencies.py            # Dependency injection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # API router aggregation
│   │   │   ├── interview.py       # /api/v1/interview/*
│   │   │   ├── scoring.py         # /api/v1/scoring/*
│   │   │   ├── resume.py          # /api/v1/resume/*
│   │   │   ├── jobs.py            # /api/v1/jobs/*
│   │   │   ├── shortlist.py       # /api/v1/shortlist/*
│   │   │   ├── invitations.py     # /api/v1/invitations/*
│   │   │   ├── speech.py          # /api/v1/speech/*
│   │   │   ├── acs.py             # /api/v1/acs/*
│   │   │   ├── webhooks.py        # /api/v1/webhooks/*
│   │   │   ├── admin.py           # /api/v1/admin/*
│   │   │   └── organisations.py   # /api/v1/organisations/*
│   │   │
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py            # Supabase JWT validation
│   │       ├── rate_limit.py      # Redis-backed rate limiting
│   │       └── cors.py            # CORS configuration
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── azure_openai.py        # GPT-4o streaming client
│   │   ├── azure_speech.py        # Speech SDK wrapper
│   │   ├── azure_avatar.py        # Avatar synthesis
│   │   ├── azure_acs.py           # ACS identity & calling
│   │   ├── azure_document.py      # Document Intelligence
│   │   ├── azure_storage.py       # Blob storage operations
│   │   ├── supabase_client.py     # Database client
│   │   └── email_service.py       # Email sending
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── interview.py           # Interview Pydantic models
│   │   ├── candidate.py           # Candidate models
│   │   ├── job.py                 # Job role models
│   │   ├── scoring.py             # Scoring models
│   │   └── common.py              # Shared models
│   │
│   └── prompts/
│       ├── __init__.py
│       ├── interviewer.py         # AI interviewer system prompt
│       ├── scoring.py             # Scoring analysis prompt
│       ├── resume.py              # Resume parsing prompt
│       ├── requirements.py        # Job extraction prompt
│       └── shortlist.py           # Candidate matching prompt
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_interview.py
│   ├── test_scoring.py
│   ├── test_resume.py
│   └── test_acs.py
│
├── scripts/
│   ├── migrate_storage.py         # Supabase → Blob migration
│   └── seed_test_data.py          # Test data generation
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 4.2 FastAPI Main Application

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.api.v1.router import api_router
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.services.azure_openai import AzureOpenAIService
from app.services.azure_speech import AzureSpeechService
from app.services.azure_acs import AzureACSService
from app.services.supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    logger.info("Starting Talenti API...")
    
    # Initialize services
    app.state.openai = AzureOpenAIService()
    app.state.speech = AzureSpeechService()
    app.state.acs = AzureACSService()
    app.state.supabase = SupabaseClient()
    
    # Verify connections
    await app.state.openai.health_check()
    await app.state.supabase.health_check()
    
    logger.info("Talenti API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Talenti API...")
    await app.state.supabase.close()
    logger.info("Talenti API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Talenti AI Interview API",
    description="Python backend for Talenti AI-powered interview platform",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "version": "1.0.0"}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
```

## 4.3 Configuration

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    
    # Azure Speech
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str = "australiaeast"
    
    # Azure Communication Services
    ACS_CONNECTION_STRING: str
    ACS_ENDPOINT: str
    ACS_CALLBACK_URL: str
    
    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER: str = "interview-recordings"
    
    # Azure Document Intelligence
    AZURE_DOCUMENT_ENDPOINT: str
    AZURE_DOCUMENT_KEY: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # Redis (for rate limiting)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Email
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@talenti.ai"
    
    # Application
    ALLOWED_ORIGINS: str = "http://localhost:5173,https://talenti.lovable.app"
    API_BASE_URL: str = "https://api.talenti.ai"
    FRONTEND_URL: str = "https://talenti.lovable.app"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
```

## 4.4 API Router Aggregation

```python
# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1 import (
    interview,
    scoring,
    resume,
    jobs,
    shortlist,
    invitations,
    speech,
    acs,
    webhooks,
    admin,
    organisations
)

api_router = APIRouter()

# Include all route modules
api_router.include_router(
    interview.router,
    prefix="/interview",
    tags=["Interview"]
)
api_router.include_router(
    scoring.router,
    prefix="/scoring",
    tags=["Scoring"]
)
api_router.include_router(
    resume.router,
    prefix="/resume",
    tags=["Resume"]
)
api_router.include_router(
    jobs.router,
    prefix="/jobs",
    tags=["Jobs"]
)
api_router.include_router(
    shortlist.router,
    prefix="/shortlist",
    tags=["Shortlist"]
)
api_router.include_router(
    invitations.router,
    prefix="/invitations",
    tags=["Invitations"]
)
api_router.include_router(
    speech.router,
    prefix="/speech",
    tags=["Speech"]
)
api_router.include_router(
    acs.router,
    prefix="/acs",
    tags=["ACS"]
)
api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"]
)
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)
api_router.include_router(
    organisations.router,
    prefix="/organisations",
    tags=["Organisations"]
)
```

---

# 5. API Endpoint Specifications

## 5.1 Interview Endpoints

### POST /api/v1/interview/chat

**Purpose**: Process a conversation turn with the AI interviewer

```python
# app/api/v1/interview.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel

from app.api.middleware.auth import get_current_user
from app.services.azure_openai import AzureOpenAIService
from app.models.interview import InterviewMessage, CAGContext

router = APIRouter()


class InterviewChatRequest(BaseModel):
    """Request body for interview chat."""
    messages: List[InterviewMessage]
    context: CAGContext
    stream: bool = True


class InterviewChatResponse(BaseModel):
    """Response for non-streaming chat."""
    message: str
    detected_competencies: List[str]
    turn_number: int


@router.post("/chat")
async def interview_chat(
    request: InterviewChatRequest,
    current_user: dict = Depends(get_current_user),
    openai: AzureOpenAIService = Depends(lambda: AzureOpenAIService())
):
    """
    Process an interview conversation turn.
    
    Supports both streaming and non-streaming responses.
    Detects competencies covered in candidate responses.
    """
    try:
        if request.stream:
            return StreamingResponse(
                openai.stream_interview_response(
                    messages=request.messages,
                    context=request.context
                ),
                media_type="text/event-stream"
            )
        else:
            response = await openai.generate_interview_response(
                messages=request.messages,
                context=request.context
            )
            return InterviewChatResponse(**response)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_interview(
    interview_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Initialize an interview session."""
    # Update interview status to in_progress
    # Return initial context
    pass


@router.post("/end")
async def end_interview(
    interview_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Complete an interview session."""
    # Update interview status to completed
    # Trigger scoring
    pass


@router.get("/{interview_id}/transcript")
async def get_transcript(
    interview_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve interview transcript."""
    pass
```

## 5.2 Scoring Endpoints

### POST /api/v1/scoring/analyze

```python
# app/api/v1/scoring.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()


class TranscriptSegment(BaseModel):
    speaker: str  # "interviewer" or "candidate"
    content: str
    timestamp: int


class ScoringDimension(BaseModel):
    name: str
    description: str
    weight: float


class ScoreAnalysisRequest(BaseModel):
    interview_id: str
    transcript: List[TranscriptSegment]
    rubric: Optional[List[ScoringDimension]] = None
    job_title: str
    job_description: str


class DimensionScore(BaseModel):
    dimension: str
    score: float
    weight: float
    evidence: str
    cited_quotes: List[str]


class ScoreAnalysisResponse(BaseModel):
    overall_score: float
    dimension_scores: List[DimensionScore]
    narrative_summary: str
    candidate_feedback: str
    anti_cheat_risk: str
    model_version: str


@router.post("/analyze", response_model=ScoreAnalysisResponse)
async def analyze_interview(
    request: ScoreAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze interview transcript and generate scores.
    
    Uses custom rubric if provided, otherwise defaults to standard dimensions.
    """
    pass


@router.get("/{interview_id}/results")
async def get_scoring_results(
    interview_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve existing scoring results for an interview."""
    pass
```

## 5.3 Resume Endpoints

### POST /api/v1/resume/parse

```python
# app/api/v1/resume.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class PersonalInfo(BaseModel):
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    linkedin: Optional[str]
    portfolio: Optional[str]


class Employment(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: Optional[str]
    description: str
    achievements: List[str]


class Education(BaseModel):
    institution: str
    degree: str
    field: str
    graduation_date: Optional[str]
    gpa: Optional[float]


class Skills(BaseModel):
    technical: List[str]
    soft: List[str]
    languages: List[str]
    certifications: List[str]


class ParsedResume(BaseModel):
    personal_info: PersonalInfo
    employment: List[Employment]
    education: List[Education]
    skills: Skills
    summary: str


class ParseResumeRequest(BaseModel):
    file_path: str
    user_id: str


@router.post("/parse", response_model=ParsedResume)
async def parse_resume(
    request: ParseResumeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Parse a resume PDF and extract structured data.
    
    Uses Azure Document Intelligence for OCR and Azure OpenAI for extraction.
    """
    pass


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload resume to Azure Blob Storage."""
    pass
```

## 5.4 Jobs Endpoints

### POST /api/v1/jobs/extract

```python
# app/api/v1/jobs.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

router = APIRouter()


class ExtractRequirementsRequest(BaseModel):
    job_description: str
    job_title: str


class ExtractedRequirements(BaseModel):
    skills: List[str]
    experience: List[str]
    qualifications: List[str]
    responsibilities: List[str]
    interview_questions: List[str]


@router.post("/extract", response_model=ExtractedRequirements)
async def extract_requirements(
    request: ExtractRequirementsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Extract structured requirements from a job description.
    
    Generates relevant interview questions based on the role.
    """
    pass
```

## 5.5 Shortlist Endpoints

### POST /api/v1/shortlist/generate

```python
# app/api/v1/shortlist.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

router = APIRouter()


class CandidateInput(BaseModel):
    application_id: str
    name: str
    resume_summary: str
    skills: List[str]
    experience_years: int


class ShortlistRequest(BaseModel):
    job_role_id: str
    candidates: List[CandidateInput]
    top_n: int = 10


class RankedCandidate(BaseModel):
    application_id: str
    rank: int
    match_score: float
    strengths: List[str]
    gaps: List[str]
    explanation: str


class ShortlistResponse(BaseModel):
    job_role_id: str
    ranked_candidates: List[RankedCandidate]
    total_evaluated: int


@router.post("/generate", response_model=ShortlistResponse)
async def generate_shortlist(
    request: ShortlistRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate ranked shortlist of candidates for a job role.
    
    Uses semantic matching against job requirements.
    """
    pass
```

## 5.6 Speech Endpoints

### GET /api/v1/speech/token

```python
# app/api/v1/speech.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class SpeechTokenResponse(BaseModel):
    token: str
    region: str
    expires_on: datetime


@router.get("/token", response_model=SpeechTokenResponse)
async def get_speech_token(
    current_user: dict = Depends(get_current_user)
):
    """
    Get Azure Speech authentication token.
    
    Token valid for 10 minutes. Cache on client side.
    """
    pass
```

## 5.7 ACS Endpoints

### POST /api/v1/acs/token

```python
# app/api/v1/acs.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()


class AcsTokenRequest(BaseModel):
    scopes: List[str] = ["voip"]


class AcsUser(BaseModel):
    communication_user_id: str


class AcsTokenResponse(BaseModel):
    token: str
    expires_on: datetime
    user: AcsUser


@router.post("/token", response_model=AcsTokenResponse)
async def generate_acs_token(
    request: AcsTokenRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate Azure Communication Services token.
    
    Creates new identity and issues token with requested scopes.
    """
    pass
```

## 5.8 Webhook Endpoints

### POST /api/v1/webhooks/acs

```python
# app/api/v1/webhooks.py
from fastapi import APIRouter, Request, BackgroundTasks
from typing import List, Any

router = APIRouter()


@router.post("/acs")
async def handle_acs_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Azure Communication Services webhook events.
    
    Processes call lifecycle events and recording updates.
    """
    events: List[dict] = await request.json()
    
    for event in events:
        event_type = event.get("eventType", "")
        
        # EventGrid subscription validation
        if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = event.get("data", {}).get("validationCode")
            return {"validationResponse": validation_code}
        
        # Process other events in background
        background_tasks.add_task(process_acs_event, event)
    
    return {"status": "accepted"}


async def process_acs_event(event: dict):
    """Background task to process ACS events."""
    event_type = event.get("eventType", "")
    data = event.get("data", {})
    
    if event_type == "Microsoft.Communication.CallStarted":
        await handle_call_started(data)
    elif event_type == "Microsoft.Communication.CallEnded":
        await handle_call_ended(data)
    elif event_type == "Microsoft.Communication.RecordingFileStatusUpdated":
        await handle_recording_ready(data)
```

## 5.9 Admin Endpoints

### POST /api/v1/admin/cleanup

```python
# app/api/v1/admin.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Literal

router = APIRouter()


class CleanupRequest(BaseModel):
    action: Literal["cleanup", "process_deletions"]


class CleanupResponse(BaseModel):
    processed: int
    deleted: int
    errors: int
    details: list


@router.post("/cleanup", response_model=CleanupResponse)
async def run_cleanup(
    request: CleanupRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Run data retention cleanup tasks.
    
    Requires admin role. Actions:
    - cleanup: Delete old recordings per org retention policy
    - process_deletions: Process pending deletion requests
    """
    pass
```

## 5.10 Organisation Endpoints

### POST /api/v1/organisations

```python
# app/api/v1/organisations.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CreateOrganisationRequest(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None


class OrganisationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    industry: Optional[str]
    website: Optional[str]
    created_at: str


@router.post("/", response_model=OrganisationResponse)
async def create_organisation(
    request: CreateOrganisationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new organisation.
    
    The authenticated user becomes the organisation admin.
    """
    pass
```

---

# 6. Azure OpenAI Integration

## 6.1 Service Implementation

```python
# app/services/azure_openai.py
from openai import AsyncAzureOpenAI
from typing import AsyncGenerator, List, Optional
import json
import logging

from app.config import settings
from app.models.interview import InterviewMessage, CAGContext
from app.prompts.interviewer import build_interviewer_prompt
from app.prompts.scoring import build_scoring_prompt

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Azure OpenAI service for AI-powered features."""
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION
        )
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT
    
    async def health_check(self) -> bool:
        """Verify Azure OpenAI connectivity."""
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"Azure OpenAI health check failed: {e}")
            raise
    
    async def stream_interview_response(
        self,
        messages: List[InterviewMessage],
        context: CAGContext
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI interviewer response.
        
        Yields Server-Sent Events for real-time display.
        """
        system_prompt = build_interviewer_prompt(context)
        
        formatted_messages = [
            {"role": "system", "content": system_prompt}
        ] + [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.deployment,
                messages=formatted_messages,
                max_tokens=800,
                temperature=0.7,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Interview streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    async def generate_interview_response(
        self,
        messages: List[InterviewMessage],
        context: CAGContext
    ) -> dict:
        """
        Generate non-streaming AI interviewer response.
        
        Returns response with detected competencies.
        """
        system_prompt = build_interviewer_prompt(context)
        
        formatted_messages = [
            {"role": "system", "content": system_prompt}
        ] + [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=formatted_messages,
            max_tokens=800,
            temperature=0.7
        )
        
        message = response.choices[0].message.content
        
        # Detect covered competencies from conversation
        competencies = await self._detect_competencies(messages, context)
        
        return {
            "message": message,
            "detected_competencies": competencies,
            "turn_number": len([m for m in messages if m.role == "assistant"]) + 1
        }
    
    async def score_interview(
        self,
        transcript: List[dict],
        rubric: List[dict],
        job_title: str,
        job_description: str
    ) -> dict:
        """
        Score interview transcript using rubric.
        
        Uses function calling for structured output.
        """
        prompt = build_scoring_prompt(transcript, rubric, job_title, job_description)
        
        tools = [{
            "type": "function",
            "function": {
                "name": "score_interview",
                "description": "Score the interview transcript",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "overall_score": {
                            "type": "number",
                            "description": "Overall score 0-100"
                        },
                        "dimension_scores": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "dimension": {"type": "string"},
                                    "score": {"type": "number"},
                                    "evidence": {"type": "string"},
                                    "cited_quotes": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "narrative_summary": {"type": "string"},
                        "candidate_feedback": {"type": "string"},
                        "anti_cheat_risk": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        }
                    },
                    "required": [
                        "overall_score",
                        "dimension_scores",
                        "narrative_summary",
                        "candidate_feedback",
                        "anti_cheat_risk"
                    ]
                }
            }
        }]
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": "You are an expert interview evaluator."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "score_interview"}}
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments)
    
    async def parse_resume(self, resume_text: str) -> dict:
        """
        Extract structured data from resume text.
        
        Uses function calling for consistent schema.
        """
        tools = [{
            "type": "function",
            "function": {
                "name": "extract_resume_data",
                "description": "Extract structured data from resume",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "personal_info": {
                            "type": "object",
                            "properties": {
                                "full_name": {"type": "string"},
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                                "location": {"type": "string"},
                                "linkedin": {"type": "string"},
                                "portfolio": {"type": "string"}
                            }
                        },
                        "employment": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "company": {"type": "string"},
                                    "title": {"type": "string"},
                                    "start_date": {"type": "string"},
                                    "end_date": {"type": "string"},
                                    "description": {"type": "string"},
                                    "achievements": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "education": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "institution": {"type": "string"},
                                    "degree": {"type": "string"},
                                    "field": {"type": "string"},
                                    "graduation_date": {"type": "string"},
                                    "gpa": {"type": "number"}
                                }
                            }
                        },
                        "skills": {
                            "type": "object",
                            "properties": {
                                "technical": {"type": "array", "items": {"type": "string"}},
                                "soft": {"type": "array", "items": {"type": "string"}},
                                "languages": {"type": "array", "items": {"type": "string"}},
                                "certifications": {"type": "array", "items": {"type": "string"}}
                            }
                        },
                        "summary": {"type": "string"}
                    }
                }
            }
        }]
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume parser. Extract all relevant information accurately."
                },
                {"role": "user", "content": f"Parse this resume:\n\n{resume_text}"}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_resume_data"}}
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments)
    
    async def extract_job_requirements(
        self,
        job_description: str,
        job_title: str
    ) -> dict:
        """Extract structured requirements from job description."""
        tools = [{
            "type": "function",
            "function": {
                "name": "extract_job_requirements",
                "description": "Extract requirements from job description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required and preferred skills"
                        },
                        "experience": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Experience requirements"
                        },
                        "qualifications": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Education and certifications"
                        },
                        "responsibilities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Key job responsibilities"
                        },
                        "interview_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Relevant interview questions"
                        }
                    },
                    "required": [
                        "skills",
                        "experience",
                        "qualifications",
                        "responsibilities",
                        "interview_questions"
                    ]
                }
            }
        }]
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "Extract structured requirements from job descriptions."
                },
                {
                    "role": "user",
                    "content": f"Job Title: {job_title}\n\nJob Description:\n{job_description}"
                }
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_job_requirements"}}
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        return json.loads(tool_call.function.arguments)
    
    async def _detect_competencies(
        self,
        messages: List[InterviewMessage],
        context: CAGContext
    ) -> List[str]:
        """Detect which competencies have been covered in conversation."""
        # Simple keyword matching for now
        # Could be enhanced with AI classification
        covered = set()
        all_text = " ".join([m.content.lower() for m in messages])
        
        competency_keywords = {
            "technical": ["code", "programming", "system", "architecture", "design"],
            "problem-solving": ["solve", "approach", "challenge", "solution"],
            "communication": ["explain", "collaborate", "team", "stakeholder"],
            "leadership": ["lead", "mentor", "guide", "decision"],
            "adaptability": ["change", "learn", "adapt", "flexible"]
        }
        
        for competency, keywords in competency_keywords.items():
            if any(kw in all_text for kw in keywords):
                covered.add(competency)
        
        return list(covered)
```

## 6.2 AI Interviewer Prompt Template

```python
# app/prompts/interviewer.py
from app.models.interview import CAGContext


def build_interviewer_prompt(context: CAGContext) -> str:
    """
    Build the system prompt for the AI interviewer.
    
    This is the critical prompt that defines interview behavior.
    Migrated from: supabase/functions/ai-interviewer/index.ts
    """
    
    # Format requirements
    requirements_text = ""
    if context.requirements:
        req = context.requirements
        if req.skills:
            requirements_text += f"Required Skills: {', '.join(req.skills)}\n"
        if req.experience:
            requirements_text += f"Experience: {', '.join(req.experience)}\n"
        if req.qualifications:
            requirements_text += f"Qualifications: {', '.join(req.qualifications)}\n"
    
    # Format company values
    values_text = ""
    if context.company_values:
        values_text = f"Company Values: {', '.join(context.company_values)}"
    
    # Format candidate context
    candidate_text = ""
    if context.candidate_context:
        cc = context.candidate_context
        candidate_text = f"""
Candidate Information:
- Name: {cc.name}
- Resume Summary: {cc.resume_summary}
"""
    
    # Format interview progress
    progress_text = ""
    if context.interview_progress:
        ip = context.interview_progress
        progress_text = f"""
Interview Progress:
- Questions Asked: {ip.questions_asked}
- Competencies Covered: {', '.join(ip.competencies_covered) or 'None yet'}
- Current Phase: {ip.current_phase}
"""
    
    return f"""You are an expert AI interviewer conducting a professional job interview for the position of {context.job_title}.

Your role is to:
1. Ask relevant, insightful questions to assess the candidate's fit for the role
2. Listen actively and ask appropriate follow-up questions
3. Maintain a professional, friendly, and conversational tone
4. Evaluate responses against the job requirements
5. Cover all key competency areas throughout the interview

Job Details:
Title: {context.job_title}
Description: {context.job_description or 'Not provided'}

{requirements_text}
{values_text}
{candidate_text}
{progress_text}

Interview Guidelines:
- INTRODUCTION PHASE: Start with a warm welcome and brief overview of the interview process. Ask about the candidate's background and interest in the role.
- TECHNICAL PHASE: Ask role-specific technical questions. Probe for depth with follow-up questions. Ask for specific examples and past experiences.
- BEHAVIORAL PHASE: Use STAR method (Situation, Task, Action, Result) questions. Focus on past behaviors as predictors of future performance.
- CLOSING PHASE: Allow candidate to ask questions. Summarize next steps. Thank them for their time.

Response Guidelines:
- Keep responses concise (2-4 sentences typically)
- Ask ONE question at a time
- Wait for candidate responses before proceeding
- Acknowledge good answers and probe deeper when needed
- If a response is vague, ask for specific examples
- Transition smoothly between topics
- Be encouraging but maintain objectivity

DO NOT:
- Reveal the scoring criteria
- Make hiring decisions or promises
- Discuss salary or benefits unless asked
- Ask illegal or inappropriate questions
- Interrupt or rush the candidate

Remember: You are evaluating fit for {context.job_title}. Focus on gathering evidence for all key competencies."""
```

## 6.3 Scoring Prompt Template

```python
# app/prompts/scoring.py
from typing import List


DEFAULT_DIMENSIONS = [
    {
        "name": "Technical Competency",
        "description": "Demonstrates required technical skills, knowledge, and problem-solving abilities for the role",
        "weight": 0.25
    },
    {
        "name": "Problem Solving",
        "description": "Shows analytical thinking, logical reasoning, and ability to approach complex challenges",
        "weight": 0.20
    },
    {
        "name": "Communication",
        "description": "Articulates ideas clearly, listens actively, and engages in effective dialogue",
        "weight": 0.20
    },
    {
        "name": "Cultural Fit",
        "description": "Aligns with company values, demonstrates adaptability, and shows team orientation",
        "weight": 0.15
    },
    {
        "name": "Leadership Potential",
        "description": "Shows initiative, ability to influence others, and potential for growth",
        "weight": 0.10
    },
    {
        "name": "Adaptability",
        "description": "Demonstrates flexibility, learning agility, and comfort with change",
        "weight": 0.10
    }
]


def build_scoring_prompt(
    transcript: List[dict],
    rubric: List[dict] = None,
    job_title: str = "",
    job_description: str = ""
) -> str:
    """
    Build the prompt for interview scoring.
    
    Migrated from: supabase/functions/score-interview/index.ts
    """
    
    dimensions = rubric or DEFAULT_DIMENSIONS
    
    # Format transcript
    transcript_text = "\n".join([
        f"[{seg['speaker'].upper()}]: {seg['content']}"
        for seg in transcript
    ])
    
    # Format dimensions
    dimensions_text = "\n".join([
        f"- {d['name']} (Weight: {d['weight']*100}%): {d['description']}"
        for d in dimensions
    ])
    
    return f"""Analyze this interview transcript for the position of {job_title}.

Job Description:
{job_description}

Scoring Dimensions:
{dimensions_text}

Interview Transcript:
{transcript_text}

Instructions:
1. Evaluate the candidate's responses for each dimension
2. Provide a score from 0-100 for each dimension
3. Cite specific quotes as evidence for each score
4. Calculate weighted overall score
5. Write a narrative summary of the candidate's performance
6. Provide constructive feedback for the candidate
7. Assess anti-cheat risk based on response patterns

Scoring Guidelines:
- 90-100: Exceptional - Exceeds all expectations
- 80-89: Strong - Meets all expectations, exceeds some
- 70-79: Good - Meets expectations
- 60-69: Adequate - Meets most expectations
- 50-59: Developing - Some gaps in expectations
- Below 50: Needs Improvement - Significant gaps

Anti-Cheat Indicators:
- Overly rehearsed or generic responses
- Inconsistencies in claimed experience
- Unable to provide specific examples
- Responses that don't match resume claims
- Unusual response timing patterns

Provide your evaluation using the score_interview function."""
```

---

# 7. Azure Speech Services

## 7.1 Speech Service Implementation

```python
# app/services/azure_speech.py
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime, timedelta
import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class AzureSpeechService:
    """Azure Speech Services wrapper for STT/TTS."""
    
    def __init__(self):
        self.region = settings.AZURE_SPEECH_REGION
        self.key = settings.AZURE_SPEECH_KEY
        self._token_cache = None
        self._token_expiry = None
    
    async def get_auth_token(self) -> dict:
        """
        Get authentication token for browser SDK.
        
        Token valid for 10 minutes. Cached to reduce API calls.
        """
        # Check cache
        if self._token_cache and self._token_expiry > datetime.utcnow():
            return {
                "token": self._token_cache,
                "region": self.region,
                "expires_on": self._token_expiry.isoformat()
            }
        
        # Fetch new token
        token_url = f"https://{self.region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.key,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()
            
            token = response.text
            expiry = datetime.utcnow() + timedelta(minutes=9)  # 10 min validity, 1 min buffer
            
            # Cache token
            self._token_cache = token
            self._token_expiry = expiry
            
            return {
                "token": token,
                "region": self.region,
                "expires_on": expiry.isoformat()
            }
    
    def create_speech_config(self) -> speechsdk.SpeechConfig:
        """Create Speech SDK configuration."""
        config = speechsdk.SpeechConfig(
            subscription=self.key,
            region=self.region
        )
        
        # Default voice
        config.speech_synthesis_voice_name = "en-AU-WilliamNeural"
        
        # Enable detailed results
        config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse,
            "true"
        )
        
        return config
    
    async def synthesize_speech(
        self,
        text: str,
        voice: str = "en-AU-WilliamNeural",
        output_format: str = "audio-16khz-32kbitrate-mono-mp3"
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Returns MP3 audio bytes.
        """
        config = self.create_speech_config()
        config.speech_synthesis_voice_name = voice
        config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=config,
            audio_config=None  # Synthesize to memory
        )
        
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            logger.error(f"Speech synthesis canceled: {cancellation.reason}")
            raise Exception(f"Speech synthesis failed: {cancellation.error_details}")
    
    async def synthesize_ssml(self, ssml: str) -> bytes:
        """
        Synthesize speech from SSML.
        
        Allows fine-grained control over prosody, emphasis, etc.
        """
        config = self.create_speech_config()
        config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=config,
            audio_config=None
        )
        
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        else:
            raise Exception("SSML synthesis failed")
```

## 7.2 Real-time Transcription WebSocket

```python
# app/api/v1/speech.py (additional WebSocket endpoint)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import azure.cognitiveservices.speech as speechsdk
import asyncio
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/transcribe")
async def transcribe_audio(websocket: WebSocket):
    """
    Real-time speech transcription via WebSocket.
    
    Receives audio chunks from client, returns transcript segments.
    """
    await websocket.accept()
    
    try:
        # Create push audio stream
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        
        # Configure speech recognition
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )
        speech_config.speech_recognition_language = "en-AU"
        speech_config.enable_dictation()
        
        # Create recognizer
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        # Event handlers
        transcript_queue = asyncio.Queue()
        
        def recognized_handler(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                segment = {
                    "type": "final",
                    "text": evt.result.text,
                    "offset": evt.result.offset,
                    "duration": evt.result.duration
                }
                asyncio.run_coroutine_threadsafe(
                    transcript_queue.put(segment),
                    asyncio.get_event_loop()
                )
        
        def recognizing_handler(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
                segment = {
                    "type": "interim",
                    "text": evt.result.text
                }
                asyncio.run_coroutine_threadsafe(
                    transcript_queue.put(segment),
                    asyncio.get_event_loop()
                )
        
        recognizer.recognized.connect(recognized_handler)
        recognizer.recognizing.connect(recognizing_handler)
        
        # Start continuous recognition
        recognizer.start_continuous_recognition()
        
        # Handle bidirectional communication
        async def receive_audio():
            try:
                while True:
                    data = await websocket.receive_bytes()
                    push_stream.write(data)
            except WebSocketDisconnect:
                push_stream.close()
        
        async def send_transcripts():
            try:
                while True:
                    segment = await transcript_queue.get()
                    await websocket.send_json(segment)
            except WebSocketDisconnect:
                pass
        
        # Run both tasks concurrently
        await asyncio.gather(
            receive_audio(),
            send_transcripts()
        )
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        await websocket.close(code=1011, reason=str(e))
    finally:
        recognizer.stop_continuous_recognition()
```

## 7.3 Avatar Integration

```python
# app/services/azure_avatar.py
import httpx
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class AzureAvatarService:
    """Azure AI Speech Avatar service."""
    
    def __init__(self):
        self.region = settings.AZURE_SPEECH_REGION
        self.key = settings.AZURE_SPEECH_KEY
        self.endpoint = f"https://{self.region}.api.cognitive.microsoft.com"
    
    async def get_ice_servers(self) -> dict:
        """
        Get ICE server configuration for WebRTC.
        
        Required for avatar video streaming.
        """
        url = f"{self.endpoint}/cognitiveservices/avatar/relay/token/v1"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.key
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def create_avatar_session(
        self,
        avatar_character: str = "lisa",
        avatar_style: str = "casual-sitting"
    ) -> dict:
        """
        Initialize avatar synthesis session.
        
        Returns WebRTC connection details.
        """
        url = f"{self.endpoint}/cognitiveservices/avatar/connect/v1"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.key,
                    "Content-Type": "application/json"
                },
                json={
                    "avatarCharacter": avatar_character,
                    "avatarStyle": avatar_style,
                    "talkingAvatarSynthesizer": {
                        "voice": "en-AU-WilliamNeural"
                    }
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def speak_with_avatar(
        self,
        session_id: str,
        text: str,
        voice: str = "en-AU-WilliamNeural"
    ) -> dict:
        """
        Make avatar speak text.
        
        Synthesizes speech and drives avatar animation.
        """
        url = f"{self.endpoint}/cognitiveservices/avatar/speak/v1"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.key,
                    "Content-Type": "application/json"
                },
                json={
                    "sessionId": session_id,
                    "text": text,
                    "voice": voice
                }
            )
            response.raise_for_status()
            return response.json()
```

---

# 8. Azure Communication Services Integration

## 8.1 ACS Service Implementation

```python
# app/services/azure_acs.py
from azure.communication.identity import CommunicationIdentityClient
from azure.communication.identity import CommunicationTokenScope
from azure.communication.callautomation import CallAutomationClient
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class AzureACSService:
    """Azure Communication Services wrapper."""
    
    def __init__(self):
        self.connection_string = settings.ACS_CONNECTION_STRING
        self.endpoint = settings.ACS_ENDPOINT
        self.callback_url = settings.ACS_CALLBACK_URL
        
        self.identity_client = CommunicationIdentityClient.from_connection_string(
            self.connection_string
        )
        self.call_client = CallAutomationClient.from_connection_string(
            self.connection_string
        )
    
    async def create_user_and_token(
        self,
        scopes: list = None
    ) -> dict:
        """
        Create ACS identity and access token.
        
        Migrated from: supabase/functions/acs-token-generator/index.ts
        """
        scopes = scopes or [CommunicationTokenScope.VOIP]
        
        # Create user identity
        user = self.identity_client.create_user()
        
        # Generate token
        token_response = self.identity_client.get_token(user, scopes=scopes)
        
        return {
            "token": token_response.token,
            "expires_on": token_response.expires_on.isoformat(),
            "user": {
                "communication_user_id": user.properties["id"]
            }
        }
    
    async def refresh_token(
        self,
        user_id: str,
        scopes: list = None
    ) -> dict:
        """Refresh token for existing user."""
        from azure.communication.identity import CommunicationUserIdentifier
        
        scopes = scopes or [CommunicationTokenScope.VOIP]
        user = CommunicationUserIdentifier(user_id)
        
        token_response = self.identity_client.get_token(user, scopes=scopes)
        
        return {
            "token": token_response.token,
            "expires_on": token_response.expires_on.isoformat()
        }
    
    async def start_recording(
        self,
        server_call_id: str,
        recording_content_type: str = "audio",
        recording_channel_type: str = "unmixed"
    ) -> dict:
        """Start call recording."""
        recording_properties = self.call_client.start_recording(
            call_locator={"server_call_id": server_call_id},
            recording_content_type=recording_content_type,
            recording_channel_type=recording_channel_type,
            recording_state_callback_url=f"{self.callback_url}/recording"
        )
        
        return {
            "recording_id": recording_properties.recording_id,
            "recording_state": recording_properties.recording_state
        }
    
    async def stop_recording(self, recording_id: str) -> dict:
        """Stop call recording."""
        self.call_client.stop_recording(recording_id)
        return {"status": "stopped"}
    
    async def download_recording(self, content_location: str) -> bytes:
        """Download recording content."""
        from azure.communication.callautomation import ContentDownloader
        
        downloader = ContentDownloader(self.call_client)
        return downloader.download(content_location)
```

## 8.2 ACS Webhook Handler

```python
# app/api/v1/webhooks.py (complete implementation)
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from datetime import datetime
import logging

from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/acs")
async def handle_acs_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Azure Communication Services webhook events.
    
    Migrated from: supabase/functions/acs-webhook-handler/index.ts
    """
    try:
        events = await request.json()
        
        # Handle as array (EventGrid format)
        if not isinstance(events, list):
            events = [events]
        
        for event in events:
            event_type = event.get("eventType", "")
            data = event.get("data", {})
            
            logger.info(f"Received ACS event: {event_type}")
            
            # EventGrid subscription validation
            if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
                validation_code = data.get("validationCode")
                logger.info(f"EventGrid validation: {validation_code}")
                return {"validationResponse": validation_code}
            
            # Process events in background
            background_tasks.add_task(process_acs_event, event_type, data)
        
        return {"status": "accepted", "events_received": len(events)}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_acs_event(event_type: str, data: dict):
    """Background processing of ACS events."""
    supabase = SupabaseClient()
    
    try:
        correlation_id = data.get("correlationId")
        server_call_id = data.get("serverCallId")
        
        if event_type == "Microsoft.Communication.CallStarted":
            await handle_call_started(supabase, correlation_id, data)
            
        elif event_type == "Microsoft.Communication.CallEnded":
            await handle_call_ended(supabase, correlation_id, data)
            
        elif event_type == "Microsoft.Communication.ParticipantJoined":
            logger.info(f"Participant joined call {correlation_id}")
            
        elif event_type == "Microsoft.Communication.ParticipantLeft":
            logger.info(f"Participant left call {correlation_id}")
            
        elif event_type == "Microsoft.Communication.RecordingFileStatusUpdated":
            await handle_recording_ready(supabase, correlation_id, data)
            
        elif event_type == "Microsoft.Communication.PlayCompleted":
            logger.info(f"Play completed for call {correlation_id}")
            
        elif event_type == "Microsoft.Communication.RecognizeCompleted":
            recognized_text = data.get("recognizeResult", {}).get("speech", "")
            logger.info(f"Recognized: {recognized_text}")
            
        else:
            logger.warning(f"Unhandled event type: {event_type}")
            
    except Exception as e:
        logger.error(f"Error processing event {event_type}: {e}")


async def handle_call_started(supabase: SupabaseClient, correlation_id: str, data: dict):
    """Handle call started event."""
    logger.info(f"Call started: {correlation_id}")
    
    # Find interview by correlation ID in metadata
    result = await supabase.client.table("interviews").select("*").execute()
    
    for interview in result.data:
        metadata = interview.get("metadata", {}) or {}
        if metadata.get("correlationId") == correlation_id:
            # Update interview status
            await supabase.client.table("interviews").update({
                "status": "in_progress",
                "started_at": datetime.utcnow().isoformat(),
                "metadata": {
                    **metadata,
                    "serverCallId": data.get("serverCallId")
                }
            }).eq("id", interview["id"]).execute()
            
            logger.info(f"Updated interview {interview['id']} to in_progress")
            return
    
    logger.warning(f"No interview found for correlation ID: {correlation_id}")


async def handle_call_ended(supabase: SupabaseClient, correlation_id: str, data: dict):
    """Handle call ended event."""
    logger.info(f"Call ended: {correlation_id}")
    
    result = await supabase.client.table("interviews").select("*").execute()
    
    for interview in result.data:
        metadata = interview.get("metadata", {}) or {}
        if metadata.get("correlationId") == correlation_id:
            started_at = interview.get("started_at")
            ended_at = datetime.utcnow()
            
            duration_seconds = None
            if started_at:
                start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                duration_seconds = int((ended_at - start).total_seconds())
            
            await supabase.client.table("interviews").update({
                "status": "completed",
                "ended_at": ended_at.isoformat(),
                "duration_seconds": duration_seconds
            }).eq("id", interview["id"]).execute()
            
            logger.info(f"Updated interview {interview['id']} to completed")
            return


async def handle_recording_ready(supabase: SupabaseClient, correlation_id: str, data: dict):
    """Handle recording file ready event."""
    content_location = data.get("recordingStorageInfo", {}).get("recordingChunks", [{}])[0].get("contentLocation")
    
    if content_location:
        logger.info(f"Recording ready at: {content_location}")
        
        # Update interview with recording URL
        result = await supabase.client.table("interviews").select("*").execute()
        
        for interview in result.data:
            metadata = interview.get("metadata", {}) or {}
            if metadata.get("correlationId") == correlation_id:
                await supabase.client.table("interviews").update({
                    "recording_url": content_location
                }).eq("id", interview["id"]).execute()
                
                logger.info(f"Updated recording URL for interview {interview['id']}")
                return
```

---

# 9. Document Processing

## 9.1 Azure Document Intelligence Integration

```python
# app/services/azure_document.py
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
import logging

from app.config import settings
from app.services.azure_openai import AzureOpenAIService

logger = logging.getLogger(__name__)


class AzureDocumentService:
    """Azure Document Intelligence for resume parsing."""
    
    def __init__(self):
        self.client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_DOCUMENT_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_DOCUMENT_KEY)
        )
        self.openai = AzureOpenAIService()
    
    async def extract_text_from_pdf(self, file_content: bytes) -> str:
        """
        Extract text content from PDF using Document Intelligence.
        
        Uses prebuilt-read model for best text extraction.
        """
        try:
            poller = self.client.begin_analyze_document(
                "prebuilt-read",
                AnalyzeDocumentRequest(bytes_source=file_content)
            )
            result = poller.result()
            
            # Combine all page content
            full_text = ""
            for page in result.pages:
                for line in page.lines:
                    full_text += line.content + "\n"
            
            return full_text
            
        except Exception as e:
            logger.error(f"Document extraction failed: {e}")
            raise
    
    async def parse_resume(self, file_content: bytes) -> dict:
        """
        Full resume parsing pipeline.
        
        1. Extract text with Document Intelligence
        2. Structure with Azure OpenAI
        
        Migrated from: supabase/functions/parse-resume/index.ts
        """
        # Step 1: Extract raw text
        raw_text = await self.extract_text_from_pdf(file_content)
        
        if not raw_text.strip():
            raise ValueError("No text could be extracted from document")
        
        # Step 2: Structure with AI
        parsed = await self.openai.parse_resume(raw_text)
        
        return parsed
    
    async def extract_document_fields(
        self,
        file_content: bytes,
        model_id: str = "prebuilt-document"
    ) -> dict:
        """
        Extract key-value pairs and tables from document.
        
        Useful for structured forms.
        """
        poller = self.client.begin_analyze_document(
            model_id,
            AnalyzeDocumentRequest(bytes_source=file_content)
        )
        result = poller.result()
        
        fields = {}
        for kv in result.key_value_pairs:
            if kv.key and kv.value:
                fields[kv.key.content] = kv.value.content
        
        tables = []
        for table in result.tables:
            table_data = []
            for cell in table.cells:
                table_data.append({
                    "row": cell.row_index,
                    "col": cell.column_index,
                    "content": cell.content
                })
            tables.append(table_data)
        
        return {
            "fields": fields,
            "tables": tables
        }
```

## 9.2 Resume API Endpoint

```python
# app/api/v1/resume.py (complete implementation)
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import base64
import logging

from app.api.middleware.auth import get_current_user
from app.services.azure_document import AzureDocumentService
from app.services.azure_storage import AzureStorageService
from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)
router = APIRouter()


class PersonalInfo(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None


class Employment(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    description: str
    achievements: List[str] = []


class Education(BaseModel):
    institution: str
    degree: str
    field: str
    graduation_date: Optional[str] = None
    gpa: Optional[float] = None


class Skills(BaseModel):
    technical: List[str] = []
    soft: List[str] = []
    languages: List[str] = []
    certifications: List[str] = []


class ParsedResume(BaseModel):
    personal_info: PersonalInfo
    employment: List[Employment]
    education: List[Education]
    skills: Skills
    summary: str


class ParseResumeRequest(BaseModel):
    file_path: str
    user_id: str


@router.post("/parse", response_model=ParsedResume)
async def parse_resume(
    request: ParseResumeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Parse a resume PDF and extract structured data.
    
    Migrated from: supabase/functions/parse-resume/index.ts
    """
    try:
        # Download file from storage
        storage = AzureStorageService()
        file_content = await storage.download_blob(request.file_path)
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Resume file not found")
        
        # Parse with Document Intelligence + OpenAI
        document_service = AzureDocumentService()
        parsed = await document_service.parse_resume(file_content)
        
        return ParsedResume(**parsed)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse resume")


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload resume to Azure Blob Storage.
    
    Returns file path for later parsing.
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Upload to storage
        storage = AzureStorageService()
        user_id = current_user.get("id")
        blob_path = f"resumes/{user_id}/{file.filename}"
        
        url = await storage.upload_blob(blob_path, content, content_type="application/pdf")
        
        # Update candidate profile
        supabase = SupabaseClient()
        await supabase.client.table("candidate_profiles").update({
            "cv_file_path": blob_path,
            "cv_uploaded_at": "now()"
        }).eq("user_id", user_id).execute()
        
        return {
            "file_path": blob_path,
            "url": url,
            "filename": file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload resume")
```

---

# 10. Data Retention & GDPR Compliance

## 10.1 Scheduled Cleanup Tasks

```python
# app/services/data_retention.py
from datetime import datetime, timedelta
from typing import List
import logging

from app.services.supabase_client import SupabaseClient
from app.services.azure_storage import AzureStorageService

logger = logging.getLogger(__name__)


class DataRetentionService:
    """
    GDPR-compliant data retention management.
    
    Migrated from: supabase/functions/data-retention-cleanup/index.ts
    """
    
    def __init__(self):
        self.supabase = SupabaseClient()
        self.storage = AzureStorageService()
    
    async def cleanup_old_recordings(self) -> dict:
        """
        Delete recordings older than organization retention period.
        
        Run daily via scheduler.
        """
        stats = {"processed": 0, "deleted": 0, "errors": 0}
        
        try:
            # Get all organizations with retention settings
            orgs_result = await self.supabase.client.table("organisations").select(
                "id, name, recording_retention_days"
            ).execute()
            
            for org in orgs_result.data:
                org_id = org["id"]
                retention_days = org.get("recording_retention_days") or 60
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                
                # Find interviews with old recordings
                interviews_result = await self.supabase.client.table("interviews").select(
                    "id, recording_url, application_id"
                ).not_.is_("recording_url", "null").is_("recording_deleted_at", "null").lt(
                    "ended_at", cutoff_date.isoformat()
                ).execute()
                
                # Filter by organization
                for interview in interviews_result.data:
                    stats["processed"] += 1
                    
                    try:
                        # Get application to check org
                        app_result = await self.supabase.client.table("applications").select(
                            "job_role_id"
                        ).eq("id", interview["application_id"]).single().execute()
                        
                        role_result = await self.supabase.client.table("job_roles").select(
                            "organisation_id"
                        ).eq("id", app_result.data["job_role_id"]).single().execute()
                        
                        if role_result.data["organisation_id"] != org_id:
                            continue
                        
                        # Delete recording from storage
                        recording_url = interview["recording_url"]
                        if recording_url:
                            await self.storage.delete_blob_from_url(recording_url)
                        
                        # Update interview
                        await self.supabase.client.table("interviews").update({
                            "recording_url": None,
                            "recording_deleted_at": datetime.utcnow().isoformat()
                        }).eq("id", interview["id"]).execute()
                        
                        stats["deleted"] += 1
                        logger.info(f"Deleted recording for interview {interview['id']}")
                        
                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(f"Error deleting recording {interview['id']}: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            raise
    
    async def process_deletion_requests(self) -> dict:
        """
        Process pending data deletion requests.
        
        Handles full deletion, recording-only, and anonymization.
        """
        stats = {"processed": 0, "completed": 0, "failed": 0}
        
        try:
            # Get pending requests
            requests_result = await self.supabase.client.table("data_deletion_requests").select(
                "*"
            ).eq("status", "pending").execute()
            
            for request in requests_result.data:
                stats["processed"] += 1
                request_id = request["id"]
                user_id = request["user_id"]
                request_type = request["request_type"]
                
                try:
                    # Update status to processing
                    await self.supabase.client.table("data_deletion_requests").update({
                        "status": "processing"
                    }).eq("id", request_id).execute()
                    
                    # Execute deletion based on type
                    if request_type == "full_deletion":
                        await self._perform_full_deletion(user_id)
                    elif request_type == "recording_only":
                        await self._delete_user_recordings(user_id)
                    elif request_type == "anonymize":
                        await self._anonymize_user_data(user_id)
                    
                    # Mark as completed
                    await self.supabase.client.table("data_deletion_requests").update({
                        "status": "completed",
                        "processed_at": datetime.utcnow().isoformat()
                    }).eq("id", request_id).execute()
                    
                    stats["completed"] += 1
                    
                except Exception as e:
                    logger.error(f"Deletion request {request_id} failed: {e}")
                    await self.supabase.client.table("data_deletion_requests").update({
                        "status": "failed",
                        "notes": str(e)
                    }).eq("id", request_id).execute()
                    stats["failed"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Process deletions failed: {e}")
            raise
    
    async def _perform_full_deletion(self, user_id: str):
        """Delete all user data."""
        # Delete in order respecting foreign keys
        
        # 1. Delete interview-related data
        interviews = await self._get_user_interviews(user_id)
        for interview in interviews:
            interview_id = interview["id"]
            
            # Delete scores and dimensions
            await self.supabase.client.table("score_dimensions").delete().eq(
                "interview_id", interview_id
            ).execute()
            await self.supabase.client.table("interview_scores").delete().eq(
                "interview_id", interview_id
            ).execute()
            
            # Delete transcripts
            await self.supabase.client.table("transcript_segments").delete().eq(
                "interview_id", interview_id
            ).execute()
            
            # Delete recording if exists
            if interview.get("recording_url"):
                await self.storage.delete_blob_from_url(interview["recording_url"])
            
            # Delete interview
            await self.supabase.client.table("interviews").delete().eq(
                "id", interview_id
            ).execute()
        
        # 2. Delete invitations
        applications = await self._get_user_applications(user_id)
        for app in applications:
            await self.supabase.client.table("invitations").delete().eq(
                "application_id", app["id"]
            ).execute()
        
        # 3. Delete applications
        await self.supabase.client.table("applications").delete().eq(
            "candidate_id", user_id
        ).execute()
        
        # 4. Delete candidate profile data
        profile = await self.supabase.client.table("candidate_profiles").select(
            "cv_file_path"
        ).eq("user_id", user_id).single().execute()
        
        if profile.data and profile.data.get("cv_file_path"):
            await self.storage.delete_blob(profile.data["cv_file_path"])
        
        await self.supabase.client.table("candidate_skills").delete().eq(
            "user_id", user_id
        ).execute()
        await self.supabase.client.table("education").delete().eq(
            "user_id", user_id
        ).execute()
        await self.supabase.client.table("employment_history").delete().eq(
            "user_id", user_id
        ).execute()
        await self.supabase.client.table("candidate_dei").delete().eq(
            "user_id", user_id
        ).execute()
        await self.supabase.client.table("candidate_profiles").delete().eq(
            "user_id", user_id
        ).execute()
        
        # 5. Delete practice interviews
        await self.supabase.client.table("practice_interviews").delete().eq(
            "user_id", user_id
        ).execute()
        
        logger.info(f"Full deletion completed for user {user_id}")
    
    async def _delete_user_recordings(self, user_id: str):
        """Delete only user's interview recordings."""
        interviews = await self._get_user_interviews(user_id)
        
        for interview in interviews:
            if interview.get("recording_url"):
                await self.storage.delete_blob_from_url(interview["recording_url"])
                await self.supabase.client.table("interviews").update({
                    "recording_url": None,
                    "recording_deleted_at": datetime.utcnow().isoformat()
                }).eq("id", interview["id"]).execute()
        
        logger.info(f"Recordings deleted for user {user_id}")
    
    async def _anonymize_user_data(self, user_id: str):
        """Anonymize personal information."""
        await self.supabase.client.table("candidate_profiles").update({
            "first_name": "REDACTED",
            "last_name": "REDACTED",
            "email": f"redacted-{user_id[:8]}@example.com",
            "phone": None,
            "linkedin_url": None,
            "portfolio_url": None
        }).eq("user_id", user_id).execute()
        
        await self.supabase.client.table("candidate_dei").delete().eq(
            "user_id", user_id
        ).execute()
        
        logger.info(f"Data anonymized for user {user_id}")
    
    async def _get_user_interviews(self, user_id: str) -> List[dict]:
        """Get all interviews for a user."""
        result = await self.supabase.client.rpc(
            "get_user_interviews",
            {"_user_id": user_id}
        ).execute()
        return result.data or []
    
    async def _get_user_applications(self, user_id: str) -> List[dict]:
        """Get all applications for a user."""
        result = await self.supabase.client.table("applications").select(
            "id"
        ).eq("candidate_id", user_id).execute()
        return result.data or []
```

## 10.2 Scheduler Configuration

```python
# app/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

from app.services.data_retention import DataRetentionService

logger = logging.getLogger(__name__)


def setup_scheduler() -> AsyncIOScheduler:
    """Configure scheduled tasks."""
    scheduler = AsyncIOScheduler()
    
    # Recording cleanup - daily at 2 AM
    scheduler.add_job(
        run_recording_cleanup,
        CronTrigger(hour=2, minute=0),
        id="recording_cleanup",
        name="Delete expired recordings",
        replace_existing=True
    )
    
    # Deletion requests - every 6 hours
    scheduler.add_job(
        run_deletion_processing,
        CronTrigger(hour="*/6"),
        id="deletion_processing",
        name="Process deletion requests",
        replace_existing=True
    )
    
    return scheduler


async def run_recording_cleanup():
    """Scheduled task for recording cleanup."""
    logger.info("Starting scheduled recording cleanup")
    service = DataRetentionService()
    stats = await service.cleanup_old_recordings()
    logger.info(f"Recording cleanup complete: {stats}")


async def run_deletion_processing():
    """Scheduled task for processing deletion requests."""
    logger.info("Starting deletion request processing")
    service = DataRetentionService()
    stats = await service.process_deletion_requests()
    logger.info(f"Deletion processing complete: {stats}")
```

## 10.3 Audit Logging

```python
# app/services/audit_log.py
from datetime import datetime
from typing import Optional, Any
import logging

from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class AuditLogService:
    """Audit logging for compliance."""
    
    def __init__(self):
        self.supabase = SupabaseClient()
    
    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        organisation_id: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None
    ):
        """
        Create audit log entry.
        
        Actions: create, update, delete, view, export, login, logout
        """
        try:
            await self.supabase.client.table("audit_log").insert({
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "organisation_id": organisation_id,
                "old_values": old_values,
                "new_values": new_values,
                "ip_address": ip_address,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
        except Exception as e:
            logger.error(f"Audit log failed: {e}")
            # Don't raise - audit should not break main flow
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100
    ) -> list:
        """Get audit history for an entity."""
        result = await self.supabase.client.table("audit_log").select("*").eq(
            "entity_type", entity_type
        ).eq(
            "entity_id", entity_id
        ).order(
            "created_at", desc=True
        ).limit(limit).execute()
        
        return result.data
```

---

# 11. Authentication & Security

## 11.1 Supabase JWT Validation Middleware

```python
# app/api/middleware/auth.py
from fastapi import HTTPException, Header, Depends, Request
from jose import jwt, JWTError
from typing import Optional
import logging

from app.config import settings
from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    request: Request = None
) -> dict:
    """
    Validate Supabase JWT and return user info.
    
    Migrated from edge function auth patterns.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        # Decode JWT
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
        
        # Get additional user data from Supabase
        supabase = SupabaseClient()
        user_data = await supabase.get_user_profile(user_id)
        
        return {
            "id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role"),
            **user_data
        }
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Optional[dict]:
    """Get user if authenticated, None otherwise."""
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


async def require_org_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Require user to be an organization admin."""
    supabase = SupabaseClient()
    
    org_id = await supabase.get_user_org_id(current_user["id"])
    if not org_id:
        raise HTTPException(status_code=403, detail="User not in any organization")
    
    role = await supabase.get_user_org_role(org_id, current_user["id"])
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {**current_user, "org_id": org_id, "org_role": role}


async def require_org_member(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Require user to be a member of any organization."""
    supabase = SupabaseClient()
    
    org_id = await supabase.get_user_org_id(current_user["id"])
    if not org_id:
        raise HTTPException(status_code=403, detail="Organization membership required")
    
    role = await supabase.get_user_org_role(org_id, current_user["id"])
    
    return {**current_user, "org_id": org_id, "org_role": role}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers."""
    # Check forwarded headers (for reverse proxy)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fall back to client host
    if request.client:
        return request.client.host
    
    return "unknown"
```

## 11.2 Rate Limiting Middleware

```python
# app/api/middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis.asyncio as redis
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed rate limiting middleware.
    
    Limits requests per IP address.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.redis = None
        self.requests_limit = settings.RATE_LIMIT_REQUESTS
        self.window_seconds = settings.RATE_LIMIT_WINDOW
    
    async def get_redis(self):
        if self.redis is None:
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        try:
            redis_client = await self.get_redis()
            
            # Get client IP
            client_ip = self._get_client_ip(request)
            key = f"ratelimit:{client_ip}"
            
            # Check current count
            current = await redis_client.get(key)
            
            if current is None:
                # First request in window
                await redis_client.setex(key, self.window_seconds, 1)
            elif int(current) >= self.requests_limit:
                # Rate limit exceeded
                logger.warning(f"Rate limit exceeded for {client_ip}")
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later."
                )
            else:
                # Increment counter
                await redis_client.incr(key)
            
        except redis.RedisError as e:
            # Log but don't block on Redis errors
            logger.error(f"Redis error in rate limiting: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        if request.client:
            return request.client.host
        
        return "unknown"


# Decorator for per-endpoint rate limiting
from functools import wraps
from fastapi import Depends


def rate_limit(requests: int = 10, window: int = 60):
    """
    Decorator for endpoint-specific rate limiting.
    
    Usage:
        @router.post("/chat")
        @rate_limit(requests=10, window=60)
        async def chat(...):
            ...
    """
    async def check_rate_limit(request: Request):
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        endpoint = request.url.path
        key = f"ratelimit:{endpoint}:{client_ip}"
        
        # Implementation would use Redis similar to middleware
        # This is a simplified version
        pass
    
    return Depends(check_rate_limit)
```

## 11.3 CORS Configuration

```python
# app/api/middleware/cors.py
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


def get_cors_origins() -> list:
    """Get allowed CORS origins from settings."""
    origins = settings.ALLOWED_ORIGINS.split(",")
    return [origin.strip() for origin in origins]


def configure_cors(app):
    """Add CORS middleware to FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Client-Info",
            "apikey",
            "x-supabase-auth"
        ],
        expose_headers=["X-Total-Count", "X-Page-Count"],
        max_age=600  # Cache preflight for 10 minutes
    )
```

---

# 12. Deployment Configuration

## 12.1 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## 12.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      # Azure OpenAI
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT:-gpt-4o}
      
      # Azure Speech
      - AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
      - AZURE_SPEECH_REGION=${AZURE_SPEECH_REGION:-australiaeast}
      
      # Azure Communication Services
      - ACS_CONNECTION_STRING=${ACS_CONNECTION_STRING}
      - ACS_ENDPOINT=${ACS_ENDPOINT}
      - ACS_CALLBACK_URL=${ACS_CALLBACK_URL}
      
      # Azure Storage
      - AZURE_STORAGE_CONNECTION_STRING=${AZURE_STORAGE_CONNECTION_STRING}
      
      # Azure Document Intelligence
      - AZURE_DOCUMENT_ENDPOINT=${AZURE_DOCUMENT_ENDPOINT}
      - AZURE_DOCUMENT_KEY=${AZURE_DOCUMENT_KEY}
      
      # Supabase
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      
      # Redis
      - REDIS_URL=redis://redis:6379
      
      # Email
      - RESEND_API_KEY=${RESEND_API_KEY}
      
      # Application
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-http://localhost:5173}
    depends_on:
      - redis
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api
    restart: unless-stopped

volumes:
  redis_data:
```

## 12.3 Azure Container Apps Deployment

```bicep
// infra/main.bicep
param location string = 'australiaeast'
param environmentName string = 'talenti'

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${environmentName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${environmentName}-api'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['https://talenti.lovable.app']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      secrets: [
        { name: 'azure-openai-key', value: azureOpenAiKey }
        { name: 'azure-speech-key', value: azureSpeechKey }
        { name: 'acs-connection-string', value: acsConnectionString }
        { name: 'supabase-service-key', value: supabaseServiceKey }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: '${containerRegistry.properties.loginServer}/talenti-api:latest'
          resources: {
            cpu: json('1')
            memory: '2Gi'
          }
          env: [
            { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenAiEndpoint }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-key' }
            { name: 'AZURE_SPEECH_KEY', secretRef: 'azure-speech-key' }
            { name: 'AZURE_SPEECH_REGION', value: 'australiaeast' }
            { name: 'ACS_CONNECTION_STRING', secretRef: 'acs-connection-string' }
            { name: 'SUPABASE_URL', value: supabaseUrl }
            { name: 'SUPABASE_SERVICE_KEY', secretRef: 'supabase-service-key' }
            { name: 'ENVIRONMENT', value: 'production' }
          ]
        }
      ]
      scale: {
        minReplicas: 2
        maxReplicas: 10
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${environmentName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: '${environmentName}acr'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}
```

## 12.4 GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AZURE_CONTAINER_REGISTRY: talentiacr.azurecr.io
  IMAGE_NAME: talenti-api
  RESOURCE_GROUP: talenti-prod-rg
  CONTAINER_APP_NAME: talenti-api

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
          
      - name: Run tests
        run: |
          pytest tests/ -v --cov=app --cov-report=xml
          
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
          
      - name: Login to ACR
        run: |
          az acr login --name talentiacr
          
      - name: Build and push image
        run: |
          docker build -t ${{ env.AZURE_CONTAINER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} .
          docker push ${{ env.AZURE_CONTAINER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker tag ${{ env.AZURE_CONTAINER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
                     ${{ env.AZURE_CONTAINER_REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          docker push ${{ env.AZURE_CONTAINER_REGISTRY }}/${{ env.IMAGE_NAME }}:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
          
      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name ${{ env.CONTAINER_APP_NAME }} \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.AZURE_CONTAINER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

---

# Appendix A: Environment Variables

```bash
# .env.example

# ===========================================
# Azure OpenAI
# ===========================================
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# ===========================================
# Azure Speech Services
# ===========================================
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=australiaeast

# ===========================================
# Azure Communication Services
# ===========================================
ACS_CONNECTION_STRING=endpoint=https://your-acs.communication.azure.com/;accesskey=your-key
ACS_ENDPOINT=https://your-acs.communication.azure.com
ACS_CALLBACK_URL=https://api.talenti.ai/api/v1/webhooks

# ===========================================
# Azure Storage
# ===========================================
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONTAINER=interview-recordings

# ===========================================
# Azure Document Intelligence
# ===========================================
AZURE_DOCUMENT_ENDPOINT=https://your-doc-intel.cognitiveservices.azure.com/
AZURE_DOCUMENT_KEY=your-doc-intel-key

# ===========================================
# Supabase
# ===========================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# ===========================================
# Redis
# ===========================================
REDIS_URL=redis://localhost:6379

# ===========================================
# Email (Resend)
# ===========================================
RESEND_API_KEY=re_your_api_key
EMAIL_FROM=noreply@talenti.ai

# ===========================================
# Application
# ===========================================
ENVIRONMENT=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:5173,https://talenti.lovable.app
API_BASE_URL=https://api.talenti.ai
FRONTEND_URL=https://talenti.lovable.app

# ===========================================
# Rate Limiting
# ===========================================
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

---

# Appendix B: Requirements

```txt
# requirements.txt

# ===========================================
# Web Framework
# ===========================================
fastapi==0.109.2
uvicorn[standard]==0.27.1
python-multipart==0.0.9
python-jose[cryptography]==3.3.0

# ===========================================
# Data Validation
# ===========================================
pydantic==2.6.1
pydantic-settings==2.1.0
email-validator==2.1.0

# ===========================================
# Azure SDKs
# ===========================================
openai==1.12.0
azure-cognitiveservices-speech==1.35.0
azure-communication-identity==1.5.0
azure-communication-callautomation==1.1.0
azure-communication-email==1.0.0
azure-ai-documentintelligence==1.0.0b1
azure-storage-blob==12.19.0
azure-identity==1.15.0
azure-core==1.30.0

# ===========================================
# Database
# ===========================================
supabase==2.3.5
httpx==0.26.0

# ===========================================
# Caching & Rate Limiting
# ===========================================
redis==5.0.1
hiredis==2.3.2

# ===========================================
# Scheduling
# ===========================================
apscheduler==3.10.4

# ===========================================
# Email
# ===========================================
resend==0.7.2

# ===========================================
# Utilities
# ===========================================
python-dateutil==2.8.2
orjson==3.9.12

# ===========================================
# Monitoring
# ===========================================
opencensus-ext-azure==1.1.13
applicationinsights==0.11.10

# ===========================================
# Testing
# ===========================================
pytest==8.0.0
pytest-asyncio==0.23.4
pytest-cov==4.1.0
httpx==0.26.0
respx==0.20.2

# ===========================================
# Development
# ===========================================
black==24.1.1
isort==5.13.2
mypy==1.8.0
ruff==0.2.0
```

---

# Appendix C: Database Pydantic Models

```python
# app/models/database.py
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ===========================================
# Enums
# ===========================================

class AppRole(str, Enum):
    ORG_ADMIN = "org_admin"
    ORG_RECRUITER = "org_recruiter"
    ORG_VIEWER = "org_viewer"
    CANDIDATE = "candidate"


class InterviewStatus(str, Enum):
    INVITED = "invited"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    BOUNCED = "bounced"
    EXPIRED = "expired"


class JobRoleStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


# ===========================================
# Organisation Models
# ===========================================

class OrganisationBase(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    billing_email: Optional[str] = None
    billing_address: Optional[str] = None
    recording_retention_days: int = 60
    values_framework: Optional[dict] = None


class OrganisationCreate(OrganisationBase):
    pass


class Organisation(OrganisationBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrgUser(BaseModel):
    id: str
    organisation_id: str
    user_id: str
    role: str = "viewer"
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Job Role Models
# ===========================================

class JobRequirements(BaseModel):
    skills: List[str] = []
    experience: List[str] = []
    qualifications: List[str] = []
    responsibilities: List[str] = []
    interview_questions: List[str] = []


class ScoringDimension(BaseModel):
    name: str
    description: str
    weight: float


class JobRoleBase(BaseModel):
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    salary_range_min: Optional[int] = None
    salary_range_max: Optional[int] = None
    requirements: Optional[JobRequirements] = None
    scoring_rubric: Optional[List[ScoringDimension]] = None
    interview_structure: Optional[dict] = None
    status: JobRoleStatus = JobRoleStatus.DRAFT


class JobRoleCreate(JobRoleBase):
    organisation_id: str


class JobRole(JobRoleBase):
    id: str
    organisation_id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Application Models
# ===========================================

class ApplicationBase(BaseModel):
    job_role_id: str
    candidate_id: str
    status: str = "pending"
    match_score: Optional[float] = None


class ApplicationCreate(ApplicationBase):
    pass


class Application(ApplicationBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Interview Models
# ===========================================

class InterviewBase(BaseModel):
    application_id: str
    status: InterviewStatus = InterviewStatus.INVITED
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    recording_url: Optional[str] = None
    recording_deleted_at: Optional[datetime] = None
    anti_cheat_signals: Optional[dict] = None
    metadata: Optional[dict] = None


class InterviewCreate(InterviewBase):
    pass


class Interview(InterviewBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Candidate Models
# ===========================================

class CandidateProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    suburb: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    cv_file_path: Optional[str] = None
    cv_uploaded_at: Optional[datetime] = None
    availability: Optional[str] = None
    work_mode: Optional[str] = None
    work_rights: Optional[str] = None
    gpa_wam: Optional[float] = None
    profile_visibility: Optional[str] = None
    visibility_settings: Optional[dict] = None
    paused_at: Optional[datetime] = None


class CandidateProfileCreate(CandidateProfileBase):
    user_id: str


class CandidateProfile(CandidateProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CandidateSkill(BaseModel):
    id: str
    user_id: str
    skill_name: str
    skill_type: str
    proficiency_level: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Education(BaseModel):
    id: str
    user_id: str
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class EmploymentHistory(BaseModel):
    id: str
    user_id: str
    company_name: str
    job_title: str
    start_date: str
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Scoring Models
# ===========================================

class InterviewScoreBase(BaseModel):
    interview_id: str
    overall_score: Optional[float] = None
    narrative_summary: Optional[str] = None
    candidate_feedback: Optional[str] = None
    anti_cheat_risk_level: Optional[str] = None
    scored_by: Optional[str] = None
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    rubric_version: Optional[str] = None
    human_override: bool = False
    human_override_by: Optional[str] = None
    human_override_reason: Optional[str] = None


class InterviewScoreCreate(InterviewScoreBase):
    pass


class InterviewScore(InterviewScoreBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScoreDimension(BaseModel):
    id: str
    interview_id: str
    dimension: str
    score: float
    weight: Optional[float] = None
    evidence: Optional[str] = None
    cited_quotes: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptSegment(BaseModel):
    id: str
    interview_id: str
    speaker: str
    content: str
    start_time_ms: int
    end_time_ms: Optional[int] = None
    confidence: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Invitation Models
# ===========================================

class InvitationBase(BaseModel):
    application_id: str
    token: str
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: datetime
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    email_template: Optional[str] = None


class InvitationCreate(InvitationBase):
    pass


class Invitation(InvitationBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Audit Models
# ===========================================

class AuditLog(BaseModel):
    id: str
    user_id: Optional[str] = None
    organisation_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DataDeletionRequest(BaseModel):
    id: str
    user_id: str
    request_type: str = "full_deletion"
    status: str = "pending"
    reason: Optional[str] = None
    notes: Optional[str] = None
    requested_at: datetime
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None

    class Config:
        from_attributes = True
```

---

# Appendix D: Frontend Integration Guide

## D.1 API URL Updates

The React frontend needs minimal changes. Update API URLs in custom hooks:

```typescript
// src/config/api.ts
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://api.talenti.ai';

export const endpoints = {
  interview: {
    chat: `${API_BASE_URL}/api/v1/interview/chat`,
    start: `${API_BASE_URL}/api/v1/interview/start`,
    end: `${API_BASE_URL}/api/v1/interview/end`,
  },
  scoring: {
    analyze: `${API_BASE_URL}/api/v1/scoring/analyze`,
  },
  resume: {
    parse: `${API_BASE_URL}/api/v1/resume/parse`,
    upload: `${API_BASE_URL}/api/v1/resume/upload`,
  },
  speech: {
    token: `${API_BASE_URL}/api/v1/speech/token`,
  },
  acs: {
    token: `${API_BASE_URL}/api/v1/acs/token`,
  },
};
```

## D.2 Updated Hooks

```typescript
// src/hooks/useAzureSpeech.ts - Update token fetch
const fetchSpeechToken = async () => {
  const response = await fetch(endpoints.speech.token, {
    headers: {
      'Authorization': `Bearer ${supabaseSession.access_token}`,
    },
  });
  return response.json();
};

// src/hooks/useAcsToken.ts - Update token fetch
const fetchAcsToken = async () => {
  const response = await fetch(endpoints.acs.token, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${supabaseSession.access_token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ scopes: ['voip'] }),
  });
  return response.json();
};
```

## D.3 Environment Variables

```bash
# Frontend .env updates
VITE_API_URL=https://api.talenti.ai
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

---

# Migration Checklist

## Phase 1: Infrastructure Setup
- [ ] Create Azure resource group
- [ ] Deploy Azure OpenAI with GPT-4o
- [ ] Deploy Azure Speech Services
- [ ] Deploy Azure Communication Services
- [ ] Deploy Azure Container Registry
- [ ] Deploy Azure Container Apps environment
- [ ] Configure Azure Key Vault
- [ ] Set up Application Insights

## Phase 2: Python Backend Development
- [ ] Set up FastAPI project structure
- [ ] Implement configuration management
- [ ] Create Pydantic models
- [ ] Implement authentication middleware
- [ ] Implement rate limiting
- [ ] Create Azure service clients
- [ ] Migrate AI interviewer endpoint
- [ ] Migrate scoring endpoint
- [ ] Migrate resume parsing endpoint
- [ ] Migrate job extraction endpoint
- [ ] Migrate shortlist generation endpoint
- [ ] Migrate invitation endpoint
- [ ] Migrate speech token endpoint
- [ ] Migrate ACS token endpoint
- [ ] Migrate webhook handler
- [ ] Implement data retention service
- [ ] Implement scheduled tasks

## Phase 3: Testing
- [ ] Unit tests for all services
- [ ] Integration tests for API endpoints
- [ ] Load testing for concurrent interviews
- [ ] Security testing (auth, rate limiting)
- [ ] End-to-end testing with frontend

## Phase 4: Deployment
- [ ] Build Docker image
- [ ] Push to Azure Container Registry
- [ ] Deploy to Container Apps (staging)
- [ ] Run smoke tests
- [ ] Update frontend API URLs
- [ ] Deploy to production
- [ ] Monitor logs and metrics

## Phase 5: Cutover
- [ ] DNS switch to new backend
- [ ] Monitor for errors
- [ ] Verify all features working
- [ ] Decommission edge functions
- [ ] Update documentation

---

# Support & Resources

## Azure Documentation
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure Speech Services](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/)
- [Azure Communication Services](https://learn.microsoft.com/en-us/azure/communication-services/)
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/)

## Python SDK References
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Azure Speech SDK for Python](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/)
- [Azure Communication Identity](https://learn.microsoft.com/en-us/python/api/azure-communication-identity/)

## FastAPI Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

**Document prepared for Talenti AI Migration Project**  
**Last updated:** January 2026
