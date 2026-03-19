# Talenti Application Architecture Diagram

This draft reflects the platform as it currently stands across:

- [documentation/ENV_SETUP.md](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/documentation/ENV_SETUP.md)
- [INTEGRATION_GUIDE.md](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/INTEGRATION_GUIDE.md)
- The frontend API modules in [`src/api`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/src/api)
- The FastAPI routes in [`backend/app/api`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/backend/app/api)
- The worker/runtime services in [`backend/app/services`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/backend/app/services)
- The deployment topology in [docker-compose.yml](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/docker-compose.yml)

## Mermaid Diagram

```mermaid
flowchart LR
    recruiter["Recruiter / Organisation User"]
    candidate["Candidate User"]

    subgraph frontend["Frontend Client (React + Vite SPA)"]
        org_ui["Organisation UI<br/>role dashboard, shortlist,<br/>resume review, invitations"]
        candidate_ui["Candidate UI<br/>claim invite, profile review,<br/>portal, lobby, live interview"]
        api["Frontend API modules<br/>auth, organisations, roles, candidates,<br/>interviews, invitations, resumeBatches,<br/>storage, scoring, shortlist, speech, acs"]
        browser_runtime["Browser runtime layer<br/>ACS Calling SDK<br/>Azure Speech SDK<br/>Azure Avatar WebRTC<br/>Browser speech fallback"]
    end

    subgraph backend["Backend API (FastAPI :8000)"]
        auth["Auth + Claim APIs<br/>/api/auth/register<br/>/api/auth/login<br/>/api/auth/claim-context<br/>/api/auth/claim-invite"]
        org_role["Organisation + Role APIs<br/>/api/orgs/*<br/>/api/roles/*"]
        resume_ingest["Resume ingestion APIs<br/>/api/v1/resume-batches/*"]
        candidate_app["Candidate + Application APIs<br/>/api/v1/candidates/*<br/>/api/v1/applications/*<br/>/api/invitations*"]
        interview_api["Interview lifecycle APIs<br/>/api/v1/interviews/start<br/>/api/v1/interviews/{id}/complete<br/>/api/v1/interview/chat<br/>/api/v1/interviews/*"]
        scoring_api["Scoring + ranking APIs<br/>/api/v1/scoring/analyze<br/>/api/v1/shortlist/generate<br/>/api/v1/roles/extract-requirements"]
        media_api["Azure token + call orchestration APIs<br/>/api/v1/acs/*<br/>/api/v1/speech/token<br/>/api/v1/call-automation/*"]
        storage_api["Storage + audit + retention APIs<br/>/api/storage/upload-url<br/>/api/v1/audit-log/*<br/>/api/v1/data-retention/*"]
    end

    subgraph data["Persistence (PostgreSQL + Files)"]
        pg["PostgreSQL<br/>users<br/>candidate_profiles<br/>applications<br/>invitations<br/>resume_ingestion_batches<br/>resume_ingestion_items<br/>parsed_profile_snapshots<br/>files<br/>interviews<br/>transcript_segments<br/>interview_scores<br/>score_dimensions<br/>background_jobs<br/>domain_events"]
        blob["Azure Blob Storage<br/>candidate CVs<br/>resume batch uploads<br/>recordings<br/>future artifacts"]
        localfs["Backend local filesystem<br/>data/uploads<br/>(local-only CV fallback)"]
    end

    subgraph ai_ml["AI / Model Layer"]
        openai["Azure OpenAI<br/>AI interviewer chat"]
        model1["Model Service 1 :8001<br/>culture / communication scoring"]
        model2["Model Service 2 :8002<br/>technical / competency scoring"]
        parser["Async resume parsing + prefill logic<br/>heuristic parser now<br/>AI parser-ready pathway later"]
    end

    subgraph workers["Background Services"]
        backend_worker["backend-worker<br/>polls background_jobs<br/>handles:<br/>candidate_cv_postprocess<br/>bulk_resume_parse<br/>candidate_profile_prefill<br/>candidate_invite_prepare<br/>interview_start_orchestration<br/>interview_complete_orchestration<br/>scoring_run"]
        acs_worker["python-acs-service<br/>ACS call automation<br/>recording lifecycle"]
    end

    subgraph azure["Azure Runtime Services"]
        acs_identity["Azure Communication Services<br/>identity + token issuance"]
        acs_media["Azure Communication Services<br/>calling / media plane"]
        speech["Azure Speech Services<br/>token, STT, TTS"]
        avatar["Azure Avatar relay<br/>TURN / WebRTC"]
        acs_events["ACS webhooks / worker callbacks"]
    end

    recruiter --> org_ui
    candidate --> candidate_ui

    org_ui --> api
    candidate_ui --> api
    candidate_ui --> browser_runtime

    api --> auth
    api --> org_role
    api --> resume_ingest
    api --> candidate_app
    api --> interview_api
    api --> scoring_api
    api --> media_api
    api --> storage_api

    auth --> pg
    org_role --> pg
    resume_ingest --> pg
    candidate_app --> pg
    interview_api --> pg
    scoring_api --> pg
    media_api --> pg
    storage_api --> pg

    org_ui -->|request SAS URLs| storage_api
    candidate_ui -->|request SAS URLs| storage_api
    storage_api --> blob

    candidate_app -->|local dev fallback only| localfs

    resume_ingest -->|file metadata + batch items| pg
    resume_ingest -->|Blob-first upload contract| blob

    candidate_app -->|claim/profile/app data| pg
    interview_api -->|interview readiness gate| pg

    interview_api --> openai
    scoring_api --> model1
    scoring_api --> model2

    candidate_app --> backend_worker
    resume_ingest --> backend_worker
    interview_api --> backend_worker
    backend_worker --> pg
    backend_worker --> blob
    backend_worker --> parser
    parser --> blob
    parser --> pg
    backend_worker --> model1
    backend_worker --> model2
    backend_worker --> acs_worker

    media_api --> acs_identity
    media_api --> speech
    media_api --> acs_worker

    acs_worker --> acs_media
    acs_worker --> blob
    acs_events -->|/api/v1/acs/webhook| media_api
    acs_worker -->|worker status callbacks| media_api

    browser_runtime -->|ACS token from backend| media_api
    browser_runtime -->|Speech token from backend| media_api
    browser_runtime -->|live media session| acs_media
    browser_runtime -->|speech recognition / TTS| speech
    browser_runtime -->|avatar relay session| avatar
```

## Current-State Notes

- The backend is the control plane for auth, candidate/application state, invitations, interview lifecycle, scoring orchestration, storage URL issuance, and worker job creation.
- Blob Storage is now the canonical upload path in deployed environments for both self-serve candidate CV uploads and organisation bulk resume ingestion.
- `/api/v1/candidates/cv` still exists only as a local-development fallback when Blob Storage is not configured.
- Resume ingestion is now a first-class platform capability:
  - recruiters create role-linked `resume_ingestion_batches`
  - files are uploaded to Blob
  - each file becomes a `resume_ingestion_item`
  - parsing results are stored in `parsed_profile_snapshots`
  - candidate user/profile/application records are matched or created
- Organisation-uploaded candidates can now exist as dormant accounts before the candidate has ever visited the platform.
- Dormant invited candidate accounts are keyed by resume email and require `claim-invite` before normal login is allowed.
- Invitation validation now returns claim state, profile-confirmation state, and interview unlock state.
- The AI interview is gated by:
  - valid invitation
  - account claimed when required
  - profile confirmation completed when required
- Candidate profile confirmation is now an explicit lifecycle step before interview start for prefilled invite flows.
- Candidate CV upload and organisation bulk resume upload both feed the same async prefill architecture through `background_jobs`.
- `backend-worker` is now the general async platform worker; `python-acs-service` remains specialized for ACS call and recording tasks.
- Async scoring scaffolding is present through `scoring_run`, while synchronous `/api/v1/scoring/analyze` remains available.
- Resume parsing is currently a best-effort backend parser with PDF/DOCX/text extraction and structured prefill logic. The architecture is intentionally ready for a future AI parser to replace or augment this layer.

## Sequence Diagram: Bulk Resume Ingestion and Invite Preparation

```mermaid
sequenceDiagram
    actor Recruiter
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant Blob as Azure Blob Storage
    participant DB as PostgreSQL
    participant BW as backend-worker

    Recruiter->>UI: Open role and bulk upload resumes
    UI->>API: POST /api/v1/resume-batches
    API->>DB: Create resume_ingestion_batch
    API-->>UI: batch_id

    loop For each uploaded resume
        UI->>API: POST /api/v1/resume-batches/{id}/items/upload-url
        API->>DB: Create file + resume_ingestion_item
        API-->>UI: SAS upload_url + item_id + file_id
        UI->>Blob: PUT resume file
    end

    UI->>API: POST /api/v1/resume-batches/{id}/process
    API->>DB: Enqueue bulk_resume_parse jobs
    API-->>UI: queued_items

    loop Worker processing
        BW->>DB: Claim bulk_resume_parse
        BW->>Blob: Download resume
        BW->>BW: Parse text and normalize structured data
        BW->>DB: Save parsed_profile_snapshot
        BW->>DB: Create or match user/profile/application
        BW->>DB: Update resume_ingestion_item
        BW->>DB: Enqueue candidate_profile_prefill
    end

    BW->>DB: Claim candidate_profile_prefill
    BW->>DB: Prefill candidate profile, skills, experience, education

    Recruiter->>UI: Review parsed queue
    UI->>API: GET /api/v1/resume-batches/{id}/items
    API->>DB: Load review queue
    API-->>UI: parsed candidates, errors, statuses

    Recruiter->>UI: Approve selected candidates
    UI->>API: PATCH /api/v1/resume-batches/items/{item_id}
    API->>DB: Mark approved

    Recruiter->>UI: Queue invitations
    UI->>API: POST /api/v1/resume-batches/{id}/invite
    API->>DB: Enqueue candidate_invite_prepare jobs

    BW->>DB: Claim candidate_invite_prepare
    BW->>DB: Create invitation linked to application + candidate email
    BW->>DB: Mark item invited, application invited
```

## Sequence Diagram: Candidate Claim, Profile Confirmation, and Interview Unlock

```mermaid
sequenceDiagram
    actor Candidate
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL

    Candidate->>UI: Open /invite/{token}
    UI->>API: GET /api/v1/invitations/validate?token=...
    API->>DB: Load invitation, application, profile, user
    API-->>UI: valid + candidate_email + claim_required + profile_completion_required + interview_unlocked

    alt Dormant account must be claimed
        Candidate->>UI: Set password using resume email
        UI->>API: POST /api/auth/claim-invite
        API->>DB: Verify token + email
        API->>DB: Set password, clear password_setup_required, mark claimed
        API-->>UI: access token
    end

    alt Profile still needs confirmation
        Candidate->>UI: Review prefilled profile
        UI->>API: POST /api/v1/candidates/profile
        API->>DB: Save candidate edits
        Candidate->>UI: Confirm profile
        UI->>API: POST /api/v1/candidates/profile/confirm
        API->>DB: Mark candidate_profile and application confirmed
        API-->>UI: interview_unlocked = true
    end

    Candidate->>UI: Proceed to device check
    UI->>API: GET /api/v1/invitations/validate?token=...
    API-->>UI: interview_unlocked = true
```

## Sequence Diagram: Live Interview and Scoring Flow

```mermaid
sequenceDiagram
    actor Candidate
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant BW as backend-worker
    participant OAI as Azure OpenAI
    participant ACS as Azure Communication Services
    participant Speech as Azure Speech Services
    participant Avatar as Azure Avatar Relay
    participant M1 as Model Service 1
    participant M2 as Model Service 2

    Candidate->>UI: Start interview from lobby
    UI->>API: POST /api/v1/interviews/start
    API->>DB: Validate profile confirmed + invitation/application state
    API->>DB: Create/resume interview, mark in_progress
    API->>DB: Emit domain event + enqueue interview_start_orchestration
    API-->>UI: interview metadata

    BW->>DB: Claim interview_start_orchestration
    Note over BW: If no server-managed call metadata exists,<br/>fallback is browser-managed interview mode

    UI->>API: POST /api/v1/acs/token
    API->>ACS: Issue ACS identity token
    ACS-->>API: ACS token
    API-->>UI: token + identity

    UI->>API: POST /api/v1/speech/token
    API->>Speech: Request speech token
    Speech-->>API: Speech token
    API-->>UI: token + region

    UI->>ACS: Join live call via SDK
    UI->>Speech: Start STT / TTS
    UI->>Avatar: Start avatar relay session

    loop Interview conversation
        Candidate->>UI: Speak response
        UI->>Speech: Stream mic audio
        Speech-->>UI: Transcript text
        UI->>API: POST /api/v1/interview/chat
        API->>OAI: chat completion request
        OAI-->>API: AI interviewer reply
        API-->>UI: Next prompt
        UI->>Speech: Speak AI reply
        UI->>API: POST /api/v1/interviews/{id}/transcripts
        API->>DB: Save transcript segment
    end

    UI->>API: POST /api/v1/interviews/{id}/complete
    API->>DB: Mark interview complete, application scoring
    API->>DB: Emit interview.completed + scoring.requested
    API->>DB: Enqueue interview_complete_orchestration + scoring_run

    opt Auto-score enabled
        BW->>DB: Claim scoring_run
        par Culture / communication model
            BW->>M1: POST /predict
            M1-->>BW: score output
        and Technical / competency model
            BW->>M2: POST /predict/transcript
            M2-->>BW: score output
        end
        BW->>DB: Persist interview score + dimensions
    end

    opt Manual review scoring
        UI->>API: POST /api/v1/scoring/analyze
        API->>M1: POST /predict
        API->>M2: POST /predict/transcript
        API-->>UI: merged score output
        UI->>API: POST /api/v1/interviews/{id}/scores
        API->>DB: Persist final score
    end
```

## Implementation Notes

- `call-automation` is not treated as a normal user-facing frontend surface. Candidate interview start triggers orchestration, and any server-managed call work stays behind the backend and workers.
- The frontend now directly uses `/api/v1/resume-batches/*` for recruiter bulk upload/review and `/api/auth/claim-invite` plus `/api/v1/candidates/profile/confirm` for the prefilled candidate invite flow.
- The current recruiter bulk upload UI queues invite preparation but does not yet include outbound email delivery infrastructure in the repo; invitation records and tokens are created and stored.
- Because candidate accounts are keyed by resume email, invitation messaging should continue to instruct invited candidates to use the email address from their resume when claiming the account.
- The architecture now clearly separates:
  - synchronous control-plane APIs
  - DB-backed async orchestration in `backend-worker`
  - specialized ACS media/call handling in `python-acs-service`
  - browser-direct media/speech runtime traffic to Azure
