# Talenti Database Schema Documentation

> **Version:** 1.1.0  
> **Last Updated:** April 2026
> **Database:** PostgreSQL

## Overview

This document provides comprehensive documentation of the Talenti database schema, including table structures, relationships, access control policies, and data flow patterns.

---

## Table of Contents

1. [Entity Relationship Diagram](#entity-relationship-diagram)
2. [Tables](#tables)
3. [Enums](#enums)
4. [Functions](#functions)
5. [Access Control Policy Summary](#access-control-policy-summary)
6. [Data Flow Patterns](#data-flow-patterns)

---

## Entity Relationship Diagram

```mermaid
erDiagram
    organisations ||--o{ org_users : "has members"
    organisations ||--o{ job_roles : "has roles"
    organisations ||--o{ org_environment_inputs : "has environment"
    organisations ||--o{ resume_ingestion_batches : "has batches"
    organisations ||--o{ audit_log : "tracks"
    
    org_users }o--|| users : "references"
    
    job_roles ||--o{ applications : "receives"
    job_roles ||--o{ resume_ingestion_batches : "targets"
    
    applications ||--o{ interviews : "has"
    applications ||--o{ invitations : "has"
    applications }o--|| candidate_profiles : "from candidate"
    candidate_profiles }o--|| files : "links CV"
    
    interviews ||--o{ transcript_segments : "contains"
    interviews ||--o{ score_dimensions : "scored by"
    interviews ||--|| interview_scores : "has summary"
    interviews ||--o{ background_jobs : "triggers"
    interviews ||--o{ domain_events : "emits"
    
    interview_scores ||--o{ post_hire_outcomes : "tracks"
    
    resume_ingestion_batches ||--o{ resume_ingestion_items : "contains"
    resume_ingestion_items }o--|| parsed_profile_snapshots : "links snapshot"
    resume_ingestion_items }o--|| files : "links file"
    
    candidate_profiles ||--|| users : "belongs to"
    candidate_profiles ||--o{ candidate_skills : "has"
    candidate_profiles ||--o{ education : "has"
    candidate_profiles ||--o{ employment_history : "has"
    candidate_profiles ||--|| candidate_dei : "has optional"
    
    users ||--o{ user_roles : "has"
    users ||--o{ practice_interviews : "conducts"
    users ||--o{ data_deletion_requests : "requests"
```

---

## Tables

### organisations

Company/business accounts that use the platform.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| name | text | NO | - | Organisation name |
| description | text | YES | NULL | About the organisation |
| industry | text | YES | NULL | Industry sector |
| website | text | YES | NULL | Company website URL |
| logo_url | text | YES | NULL | Logo image URL |
| billing_email | text | YES | NULL | Billing contact email |
| billing_address | text | YES | NULL | Billing address |
| values_framework | jsonb | YES | NULL | Company values for culture fit |
| recording_retention_days | integer | YES | NULL | How long to keep recordings |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update timestamp |

**Indexes:**
- `organisations_pkey` (id)

---

### org_users

Team members belonging to an organisation.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| organisation_id | uuid | NO | - | FK to organisations |
| user_id | uuid | NO | - | FK to users |
| role | text | NO | 'member' | Role in org (admin, recruiter, viewer) |
| created_at | timestamptz | NO | now() | When added to org |

**Indexes:**
- `org_users_pkey` (id)
- `org_users_org_user_unique` (organisation_id, user_id) UNIQUE

**Foreign Keys:**
- `org_users_organisation_id_fkey` - organisations(id)

---

### job_roles

Open positions/job listings created by organisations.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| organisation_id | uuid | NO | - | FK to organisations |
| title | text | NO | - | Job title |
| description | text | YES | NULL | Full job description |
| department | text | YES | NULL | Department/team |
| location | text | YES | NULL | Work location |
| work_type | text | YES | NULL | remote/hybrid/onsite |
| employment_type | text | YES | NULL | full-time/part-time/contract |
| industry | text | YES | NULL | Industry category |
| salary_range_min | integer | YES | NULL | Minimum salary |
| salary_range_max | integer | YES | NULL | Maximum salary |
| requirements | jsonb | YES | NULL | Extracted requirements |
| scoring_rubric | jsonb | YES | NULL | Custom scoring weights |
| interview_structure | jsonb | YES | NULL | Interview configuration |
| status | job_role_status | NO | 'draft' | Role status |
| created_by | uuid | YES | NULL | User who created |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update timestamp |

**Requirements JSONB Structure:**
```json
{
  "skills": ["React", "JavaScript"],
  "experience": ["5+ years frontend"],
  "qualifications": ["Bachelor's degree"],
  "responsibilities": ["Lead frontend team"]
}
```

**Scoring Rubric JSONB Structure:**
```json
{
  "technical_skills": { "weight": 0.3, "label": "Technical Skills" },
  "communication": { "weight": 0.2, "label": "Communication" }
}
```

**Indexes:**
- `job_roles_pkey` (id)
- `job_roles_organisation_id_idx` (organisation_id)

**Foreign Keys:**
- `job_roles_organisation_id_fkey` - organisations(id)

---

### candidate_profiles

Candidate personal information and profile data.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | FK to users |
| first_name | text | YES | NULL | First name |
| last_name | text | YES | NULL | Last name |
| email | text | YES | NULL | Contact email |
| phone | text | YES | NULL | Phone number |
| suburb | text | YES | NULL | Suburb/city |
| state | text | YES | NULL | State/province |
| postcode | text | YES | NULL | Postal code |
| country | text | YES | NULL | Country |
| linkedin_url | text | YES | NULL | LinkedIn profile |
| portfolio_url | text | YES | NULL | Portfolio/website |
| cv_file_id | text | YES | NULL | FK to files.id for the linked CV |
| cv_file_path | text | YES | NULL | Path to CV in storage |
| cv_uploaded_at | timestamptz | YES | NULL | When CV was uploaded |
| availability | text | YES | NULL | When available to start |
| work_mode | text | YES | NULL | Preferred work mode |
| work_rights | text | YES | NULL | Work authorization |
| gpa_wam | numeric | YES | NULL | Academic score |
| profile_visibility | text | YES | NULL | Visibility setting |
| visibility_settings | jsonb | YES | NULL | Detailed visibility |
| paused_at | timestamptz | YES | NULL | When paused job search |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update timestamp |

**Indexes:**
- `candidate_profiles_pkey` (id)
- `candidate_profiles_user_id_idx` (user_id) UNIQUE

---

### candidate_skills

Skills listed by candidates.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | FK to users |
| skill_name | text | NO | - | Skill name |
| skill_type | text | NO | - | hard/soft |
| proficiency_level | text | YES | NULL | beginner/intermediate/expert |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Indexes:**
- `candidate_skills_pkey` (id)
- `candidate_skills_user_id_idx` (user_id)

---

### education

Educational history for candidates.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | FK to users |
| institution | text | NO | - | School/university name |
| degree | text | NO | - | Degree title |
| field_of_study | text | YES | NULL | Major/field |
| start_date | date | YES | NULL | Start date |
| end_date | date | YES | NULL | End/graduation date |
| is_current | boolean | YES | false | Currently studying |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Indexes:**
- `education_pkey` (id)
- `education_user_id_idx` (user_id)

---

### employment_history

Work history for candidates.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | FK to users |
| company_name | text | NO | - | Employer name |
| job_title | text | NO | - | Position title |
| description | text | YES | NULL | Role description |
| start_date | date | NO | - | Start date |
| end_date | date | YES | NULL | End date (null if current) |
| is_current | boolean | YES | false | Currently employed |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Indexes:**
- `employment_history_pkey` (id)
- `employment_history_user_id_idx` (user_id)

---

### candidate_dei

Diversity, equity, and inclusion data (optional, extra sensitive).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | FK to users |
| gender | text | YES | NULL | Gender identity |
| ethnicity | text | YES | NULL | Ethnic background |
| disability_status | text | YES | NULL | Disability disclosure |
| veteran_status | text | YES | NULL | Veteran status |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Note:** This data is used only for aggregate DEI reporting, never for individual candidate evaluation.

---

### applications

Job applications from candidates.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| job_role_id | uuid | NO | - | FK to job_roles |
| candidate_id | uuid | NO | - | FK to users (candidate) |
| status | text | NO | 'applied' | Application status |
| match_score | integer | YES | NULL | AI match score (0-100) |
| created_at | timestamptz | NO | now() | Application date |
| updated_at | timestamptz | NO | now() | Last update |

**Status Values:**
- `applied` - Initial application
- `screening` - Under review
- `invited` - Invited to interview
- `interviewing` - Interview in progress
- `interviewed` - Interview completed
- `shortlisted` - On shortlist
- `rejected` - Not proceeding
- `hired` - Offered/accepted

**Indexes:**
- `applications_pkey` (id)
- `applications_job_role_id_idx` (job_role_id)
- `applications_candidate_id_idx` (candidate_id)

**Foreign Keys:**
- `applications_job_role_id_fkey` - job_roles(id)

---

### interviews

Interview sessions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| application_id | uuid | NO | - | FK to applications |
| status | interview_status | NO | 'invited' | Interview status |
| started_at | timestamptz | YES | NULL | When interview began |
| ended_at | timestamptz | YES | NULL | When interview ended |
| duration_seconds | integer | YES | NULL | Total duration |
| call_connection_id | text | YES | NULL | ACS call connection identifier |
| server_call_id | text | YES | NULL | Server-managed ACS call identifier |
| recording_id | text | YES | NULL | Recording session identifier |
| recording_started | boolean | NO | false | Whether recording has started |
| recording_processed | boolean | NO | false | Whether recording has been processed |
| recording_status | text | YES | NULL | Recording lifecycle status |
| recording_error | text | YES | NULL | Recording failure message |
| recording_started_at | timestamptz | YES | NULL | When recording started |
| recording_stopped_at | timestamptz | YES | NULL | When recording stopped |
| recording_processed_at | timestamptz | YES | NULL | When recording was processed |
| recording_url | text | YES | NULL | URL to recording |
| transcript_status | text | YES | NULL | Transcript lifecycle status |
| anti_cheat_signals | text | YES | NULL | JSON-encoded detected anomalies |
| session_metadata | text | YES | NULL | JSON-encoded session/orchestration metadata |
| summary | text | YES | NULL | Interview summary text |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update |

**Session metadata JSON structure:**
```json
{
  "serverCallId": "...",
  "correlationId": "uuid",
  "lastEventAt": "2026-01-13T10:00:00Z"
}
```

**Indexes:**
- `interviews_pkey` (id)
- `interviews_application_id_idx` (application_id)

**Foreign Keys:**
- `interviews_application_id_fkey` - applications(id)

---

### transcript_segments

Interview transcript broken into speaker segments.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| interview_id | uuid | NO | - | FK to interviews |
| speaker | text | NO | - | 'ai' or 'candidate' |
| content | text | NO | - | Spoken text |
| start_time_ms | integer | NO | - | Start time in ms |
| end_time_ms | integer | YES | NULL | End time in ms |
| confidence | numeric | YES | NULL | STT confidence score |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Indexes:**
- `transcript_segments_pkey` (id)
- `transcript_segments_interview_id_idx` (interview_id)
- `transcript_segments_start_time_idx` (start_time_ms)

**Foreign Keys:**
- `transcript_segments_interview_id_fkey` - interviews(id)

---

### files

Blob-backed uploaded files tracked by the backend.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| organisation_id | text | YES | NULL | Owning organisation when applicable |
| user_id | text | YES | NULL | Owning user when applicable |
| purpose | text | NO | 'general' | File purpose such as `candidate_cv` |
| blob_path | text | NO | - | Blob path/key in storage |
| content_type | text | YES | NULL | MIME type |
| metadata | text | YES | NULL | JSON-encoded metadata |
| created_at | timestamptz | NO | now() | Creation timestamp |

---

### background_jobs

DB-backed asynchronous work queue processed by `backend-worker`.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| job_type | text | NO | - | Handler key such as `interview_start_orchestration` |
| status | text | NO | `pending` | `pending`, `running`, `completed`, `failed`, or `skipped` |
| payload_json | text | NO | - | JSON-encoded job payload |
| result_json | text | YES | NULL | JSON-encoded job result |
| attempts | integer | NO | 0 | Attempt count |
| max_attempts | integer | NO | 3 | Retry ceiling |
| available_at | timestamptz | NO | now() | Next eligible run time |
| started_at | timestamptz | YES | NULL | Processing start time |
| completed_at | timestamptz | YES | NULL | Processing completion time |
| last_error | text | YES | NULL | Most recent failure message |
| correlation_id | text | YES | NULL | Shared orchestration correlation ID |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update |

---

### domain_events

Outbox-style domain event log written transactionally with state changes.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| event_type | text | NO | - | Event name such as `interview.started` |
| aggregate_type | text | NO | - | Aggregate category such as `interview` |
| aggregate_id | text | NO | - | Aggregate identifier |
| payload_json | text | NO | - | JSON-encoded event payload |
| correlation_id | text | YES | NULL | Shared orchestration correlation ID |
| created_at | timestamptz | NO | now() | Creation timestamp |

---

### interview_scores

Summary scoring for completed interviews.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| interview_id | uuid | NO | - | FK to interviews (UNIQUE) |
| overall_score | integer | YES | NULL | Weighted score (0-100) |
| narrative_summary | text | YES | NULL | AI-generated summary |
| candidate_feedback | text | YES | NULL | Feedback for candidate |
| anti_cheat_risk_level | text | YES | NULL | low/medium/high |
| scored_by | text | YES | NULL | 'ai' or user ID |
| model_version | text | YES | NULL | AI model used |
| prompt_version | text | YES | NULL | Prompt version |
| rubric_version | text | YES | NULL | Rubric version |
| human_override | boolean | YES | false | Manual adjustment made |
| human_override_by | uuid | YES | NULL | Who overrode |
| human_override_reason | text | YES | NULL | Why overridden |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update |

**Indexes:**
- `interview_scores_pkey` (id)
- `interview_scores_interview_id_idx` (interview_id) UNIQUE

**Foreign Keys:**
- `interview_scores_interview_id_fkey` - interviews(id)

---

### score_dimensions

Individual dimension scores for interviews.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| interview_id | uuid | NO | - | FK to interviews |
| dimension | text | NO | - | Dimension name |
| score | numeric | NO | - | Score (0-10) |
| weight | numeric | YES | NULL | Weight used (0-1) |
| evidence | text | YES | NULL | Explanation |
| cited_quotes | jsonb | YES | NULL | Supporting quotes |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Dimensions are dynamic** and produced by the scoring pipeline. Culture fit dimensions from model-service-1 follow the canonical five (ownership, execution, challenge, ambiguity, feedback). Skills fit dimensions from model-service-2 are role-specific and derived from the job description.

**Indexes:**
- `score_dimensions_pkey` (id)
- `score_dimensions_interview_id_idx` (interview_id)

**Foreign Keys:**
- `score_dimensions_interview_id_fkey` - interviews(id)

---

### invitations

Interview invitations sent to candidates.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| application_id | uuid | NO | - | FK to applications |
| token | text | NO | - | Secure invite token |
| status | invitation_status | NO | 'pending' | Invitation status |
| email_template | text | YES | NULL | Template used |
| expires_at | timestamptz | NO | - | Expiration time |
| sent_at | timestamptz | YES | NULL | When email sent |
| opened_at | timestamptz | YES | NULL | When link clicked |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Indexes:**
- `invitations_pkey` (id)
- `invitations_token_idx` (token) UNIQUE
- `invitations_application_id_idx` (application_id)

**Foreign Keys:**
- `invitations_application_id_fkey` - applications(id)

---

### practice_interviews

Practice interview sessions (not tied to real jobs).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | FK to users |
| sample_role_type | text | NO | - | Practice role category |
| status | text | NO | 'pending' | Session status |
| started_at | timestamptz | YES | NULL | Start time |
| ended_at | timestamptz | YES | NULL | End time |
| duration_seconds | integer | YES | NULL | Duration |
| feedback | jsonb | YES | NULL | Practice feedback |
| created_at | timestamptz | NO | now() | Creation timestamp |

---

### user_roles

Application-level role assignments.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | FK to users |
| role | app_role | NO | - | Role enum value |
| created_at | timestamptz | NO | now() | When assigned |

**Indexes:**
- `user_roles_pkey` (id)
- `user_roles_user_id_idx` (user_id)

---

### audit_log

Audit trail for security and compliance.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | YES | NULL | User who took action |
| organisation_id | uuid | YES | NULL | Related organisation |
| action | text | NO | - | Action type |
| entity_type | text | NO | - | What was affected |
| entity_id | uuid | YES | NULL | ID of affected entity |
| old_values | jsonb | YES | NULL | Before state |
| new_values | jsonb | YES | NULL | After state |
| ip_address | text | YES | NULL | Client IP |
| created_at | timestamptz | NO | now() | When action occurred |

**Indexes:**
- `audit_log_pkey` (id)
- `audit_log_organisation_id_idx` (organisation_id)
- `audit_log_created_at_idx` (created_at)

**Foreign Keys:**
- `audit_log_organisation_id_fkey` - organisations(id)

---

### data_deletion_requests

GDPR data deletion request tracking.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| user_id | uuid | NO | - | User requesting deletion |
| request_type | text | NO | 'full_deletion' | Type of deletion |
| status | text | NO | 'pending' | Request status |
| reason | text | YES | NULL | Why requesting |
| notes | text | YES | NULL | Processing notes |
| requested_at | timestamptz | NO | now() | Request time |
| processed_at | timestamptz | YES | NULL | Completion time |
| processed_by | text | YES | NULL | Who processed |

**Request Types:**
- `full_deletion` - Delete all data
- `recording_only` - Delete only recordings
- `anonymize` - Anonymize PII, keep aggregate data

**Status Values:**
- `pending` - Awaiting processing
- `processing` - Currently being processed
- `completed` - Successfully processed
- `failed` - Processing failed

---

### org_environment_inputs

Organisation operating-environment survey responses used to configure culture fit scoring.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| organisation_id | text | NO | - | FK to organisations (CASCADE) |
| raw_answers | text | NO | - | JSON-encoded questionnaire answers |
| signals_json | text | YES | NULL | Extracted behavioural signals |
| derived_environment | text | NO | - | JSON-encoded derived environment profile |
| defaulted_variables | text | YES | NULL | Variables that used defaults |
| extra_fatal_risks | text | YES | NULL | Additional fatal risk flags |
| submitted_by | text | YES | NULL | User who submitted |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Foreign Keys:**
- `org_environment_inputs_organisation_id_fkey` - organisations(id) ON DELETE CASCADE

---

### resume_ingestion_batches

Bulk resume upload batches created by recruiters for a specific job role.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| organisation_id | text | NO | - | FK to organisations |
| job_role_id | text | NO | - | FK to job_roles |
| status | text | NO | 'draft' | Batch status (draft, processing, completed) |
| title | text | YES | NULL | Batch label |
| created_by | text | YES | NULL | FK to users |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update |

**Foreign Keys:**
- `resume_ingestion_batches_organisation_id_fkey` - organisations(id)
- `resume_ingestion_batches_job_role_id_fkey` - job_roles(id)
- `resume_ingestion_batches_created_by_fkey` - users(id)

---

### resume_ingestion_items

Individual resume items within a batch, tracking parse status and candidate matching.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| batch_id | text | NO | - | FK to resume_ingestion_batches |
| file_id | text | NO | - | FK to files |
| parse_status | text | NO | 'pending' | Parse status (pending, completed, failed) |
| recruiter_review_status | text | NO | 'pending_review' | Recruiter review state |
| candidate_email | text | YES | NULL | Extracted or assigned email |
| candidate_name | text | YES | NULL | Extracted name |
| parse_confidence_json | text | YES | NULL | JSON parse confidence scores |
| parse_error | text | YES | NULL | Parse failure message |
| matched_user_id | text | YES | NULL | FK to users (matched candidate) |
| candidate_profile_id | text | YES | NULL | FK to candidate_profiles |
| application_id | text | YES | NULL | FK to applications |
| snapshot_id | text | YES | NULL | FK to parsed_profile_snapshots |
| invitation_id | text | YES | NULL | FK to invitations |
| uploaded_at | timestamptz | YES | NULL | Upload timestamp |
| processed_at | timestamptz | YES | NULL | Parse completion time |
| invited_at | timestamptz | YES | NULL | When invitation was sent |
| created_at | timestamptz | NO | now() | Creation timestamp |
| updated_at | timestamptz | NO | now() | Last update |

**Foreign Keys:**
- `resume_ingestion_items_batch_id_fkey` - resume_ingestion_batches(id)
- `resume_ingestion_items_file_id_fkey` - files(id)
- `resume_ingestion_items_matched_user_id_fkey` - users(id)
- `resume_ingestion_items_candidate_profile_id_fkey` - candidate_profiles(id)
- `resume_ingestion_items_application_id_fkey` - applications(id)
- `resume_ingestion_items_snapshot_id_fkey` - parsed_profile_snapshots(id)
- `resume_ingestion_items_invitation_id_fkey` - invitations(id)

---

### parsed_profile_snapshots

Immutable snapshots of parsed resume data, preserving the extraction result at parse time.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| user_id | text | YES | NULL | FK to users (if matched) |
| file_id | text | NO | - | FK to files (source document) |
| snapshot_type | text | NO | 'resume_parse' | Snapshot category |
| parser_version | text | YES | NULL | Parser version used |
| source_kind | text | YES | NULL | Source type (pdf, docx, etc.) |
| data_json | text | NO | - | JSON-encoded parsed profile data |
| confidence_json | text | YES | NULL | JSON field-level confidence scores |
| raw_text | text | YES | NULL | Extracted raw text |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Foreign Keys:**
- `parsed_profile_snapshots_user_id_fkey` - users(id)
- `parsed_profile_snapshots_file_id_fkey` - files(id)

---

### post_hire_outcomes

Post-hire performance data linked to interview scores for predictive validation.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | text | NO | uuid | Primary key |
| interview_score_id | text | NO | - | FK to interview_scores (CASCADE) |
| observed_at | timestamptz | NO | - | When performance was observed |
| snapshot_period | text | NO | 'custom' | Observation period (e.g., 30d, 90d, custom) |
| outcome_rating | float | NO | - | Performance rating |
| outcome_notes | text | YES | NULL | Freeform notes |
| dimension_ratings | text | YES | NULL | JSON per-dimension performance ratings |
| recorded_by | text | YES | NULL | FK to users (SET NULL on delete) |
| created_at | timestamptz | NO | now() | Creation timestamp |

**Indexes:**
- `ix_post_hire_outcomes_interview_score_id` (interview_score_id)
- `ix_post_hire_outcomes_observed_at` (observed_at)
- `ix_post_hire_outcomes_snapshot_period` (snapshot_period)

**Foreign Keys:**
- `post_hire_outcomes_interview_score_id_fkey` - interview_scores(id) ON DELETE CASCADE
- `post_hire_outcomes_recorded_by_fkey` - users(id) ON DELETE SET NULL

---

## Enums

### app_role

Application-level roles.

```sql
CREATE TYPE app_role AS ENUM (
  'org_admin',
  'org_recruiter', 
  'org_viewer',
  'candidate'
);
```

### interview_status

Interview session states.

```sql
CREATE TYPE interview_status AS ENUM (
  'invited',
  'scheduled',
  'in_progress',
  'completed',
  'cancelled',
  'expired'
);
```

### invitation_status

Invitation states.

```sql
CREATE TYPE invitation_status AS ENUM (
  'pending',
  'sent',
  'delivered',
  'opened',
  'bounced',
  'expired'
);
```

### job_role_status

Job listing states.

```sql
CREATE TYPE job_role_status AS ENUM (
  'draft',
  'active',
  'paused',
  'closed'
);
```

---

## Functions

### user_belongs_to_org

Check if user is member of organisation.

```sql
CREATE FUNCTION user_belongs_to_org(_org_id uuid, _user_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM org_users 
    WHERE organisation_id = _org_id AND user_id = _user_id
  );
$$ LANGUAGE sql SECURITY DEFINER;
```

### user_org_role

Get user's role in organisation.

```sql
CREATE FUNCTION user_org_role(_org_id uuid, _user_id uuid)
RETURNS text AS $$
  SELECT role FROM org_users 
  WHERE organisation_id = _org_id AND user_id = _user_id;
$$ LANGUAGE sql SECURITY DEFINER;
```

### get_user_org_id

Get user's primary organisation.

```sql
CREATE FUNCTION get_user_org_id(_user_id uuid)
RETURNS uuid AS $$
  SELECT organisation_id FROM org_users 
  WHERE user_id = _user_id 
  LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER;
```

### has_role

Check if user has specific app role.

```sql
CREATE FUNCTION has_role(_role app_role, _user_id uuid)
RETURNS boolean AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_roles 
    WHERE user_id = _user_id AND role = _role
  );
$$ LANGUAGE sql SECURITY DEFINER;
```

---

## Access Control Policy Summary

> **Important:** The policies below describe the *intended* access control matrix. These are currently enforced at the **application layer** (FastAPI dependency injection in `backend/app/api/deps.py`) and **not** via PostgreSQL Row-Level Security (RLS). No RLS policies exist in the Alembic migrations. See [ARCHITECTURE_OVERVIEW.md, Appendix C, IMP-03](./ARCHITECTURE_OVERVIEW.md#c2-implementation-gaps) for the related audit finding.

| Table | SELECT | INSERT | UPDATE | DELETE |
|-------|--------|--------|--------|--------|
| organisations | Own org members | Service role | Org admins | - |
| org_users | Own org members | Service role | Org admins | Org admins |
| job_roles | Org members + public active | Org recruiters | Org recruiters | Org admins |
| candidate_profiles | Own + org with application | Own only | Own only | Own only |
| candidate_skills | Own + org with application | Own only | Own only | Own only |
| education | Own + org with application | Own only | Own only | Own only |
| employment_history | Own + org with application | Own only | Own only | Own only |
| candidate_dei | Own only | Own only | Own only | Own only |
| applications | Own + org members | Candidates | Org members | - |
| interviews | Own + org members | System | System | - |
| transcript_segments | Own + org members | System | - | - |
| interview_scores | Own + org members | System | Org admins | - |
| score_dimensions | Own + org members | System | - | - |
| invitations | Org members | Org recruiters | Org recruiters | - |
| practice_interviews | Own only | Own only | Own only | Own only |
| audit_log | Org admins | System | - | - |
| data_deletion_requests | Own only | Own only | System | - |

---

## Data Flow Patterns

### Candidate Application Flow

```mermaid
sequenceDiagram
    participant C as Candidate
    participant App as Application
    participant Inv as Invitation
    participant Int as Interview
    participant Score as Scores
    
    C->>App: Apply to role
    App->>App: Status: applied
    
    Note over App: Recruiter reviews
    App->>Inv: Send invitation
    Inv->>C: Email with token
    
    C->>Int: Start interview
    Int->>Int: Status: in_progress
    Int->>Int: Record transcript
    
    Int->>Score: AI scoring
    Int->>Int: Status: completed
    App->>App: Status: interviewed
```

### Data Retention Flow

```mermaid
flowchart TD
    A[Scheduled Job] --> B{Check retention policy}
    B --> C[Find expired recordings]
    C --> D[Delete from storage]
    D --> E[Update interview record]
    E --> F[Log to audit_log]
    
    A --> G{Check deletion requests}
    G --> H[Process pending requests]
    H --> I{Request type?}
    I -->|full_deletion| J[Delete all user data]
    I -->|recording_only| K[Delete recordings only]
    I -->|anonymize| L[Anonymize PII]
    J --> M[Update request status]
    K --> M
    L --> M
```


