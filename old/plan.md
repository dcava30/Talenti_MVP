# Plan: Create Python Migration Prompt Document

## Objective
Create a comprehensive text file that serves as a detailed prompt/instruction document for a team of software engineers to transform the Talenti AI interview platform from its current React/TypeScript + Edge Functions architecture to a Python backend integrated with Azure Cognitive Services.

## Document Structure

The migration prompt document will include:

### 1. Executive Summary
- Current architecture overview (React + Supabase Edge Functions + Azure SDK)
- Target architecture (Python FastAPI + Azure Cognitive Services)
- Key migration considerations

### 2. Current System Components

**Frontend (React/TypeScript)**
- Pages and routing structure
- Custom hooks for Azure Speech, Avatar, ACS
- Component architecture

**Backend (Supabase Edge Functions - Deno/TypeScript)**
- AI Interviewer (conversation management)
- Score Interview (transcript analysis)
- Parse Resume (document processing)
- Extract Requirements (job description analysis)
- Generate Shortlist (candidate matching)
- Send Invitation (email workflow)
- Azure Speech Token (token generation)
- Data Retention Cleanup (GDPR compliance)
- ACS Webhook Handler (call events)

**Database Schema (PostgreSQL)**
- 17 tables with full schema
- RLS policies and functions
- Relationships and enums

**Existing Python Service**
- ACS Call Automation Service (already Python)
- Recording management
- Blob storage integration

### 3. Azure Cognitive Services Integration Requirements
- Azure Speech Services (STT/TTS)
- Azure AI Speech Avatar
- Azure Communication Services (VoIP)
- Azure OpenAI (replacing Lovable AI Gateway)
- Azure Document Intelligence (resume parsing)
- Azure Blob Storage

### 4. Python Implementation Specifications
- FastAPI application structure
- Service layer architecture
- Azure SDK integration patterns
- Authentication and security
- Rate limiting and monitoring

### 5. API Endpoint Mapping
- Detailed mapping from Edge Functions to Python endpoints
- Request/response schemas
- Error handling patterns

### 6. Data Migration Strategy
- Database compatibility considerations
- Supabase to Azure SQL migration (if applicable)
- File storage migration

### 7. Non-Functional Requirements
- Latency targets (<800ms for AI interview turns)
- Data residency (AU clients, GDPR compliance)
- Scalability and deployment (Azure Container Apps)

## Deliverable
A single markdown file `PYTHON_MIGRATION_PROMPT.md` containing all instructions for the engineering team.

## Critical Files for Implementation
- `supabase/functions/*` - All edge functions to be migrated
- `src/hooks/useAzure*.ts` - Azure integration patterns to replicate
- `python-acs-service/*` - Existing Python service to extend
- `src/integrations/supabase/types.ts` - Database schema reference
- `src/pages/LiveInterview.tsx` - Main interview flow logic
