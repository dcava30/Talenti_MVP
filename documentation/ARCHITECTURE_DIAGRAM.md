# Talenti Application Architecture Diagram

This draft is based on:

- [documentation/ENV_SETUP.md](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/documentation/ENV_SETUP.md)
- [INTEGRATION_GUIDE.md](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/INTEGRATION_GUIDE.md)
- The frontend API modules in [`src/api`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/src/api)
- The FastAPI routes in [`backend/app/api`](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/backend/app/api)
- The deployment topology in [docker-compose.yml](/c:/Users/Declan/Downloads/TalentiMatchFrontend/Talenti_MVP/docker-compose.yml)

## Mermaid Diagram

```mermaid
flowchart LR
    user[User]

    subgraph client["Frontend Client (React + Vite)"]
        web["SPA UI<br/>Pages, hooks, React Query, local JWT storage"]
        api["Frontend API modules<br/>auth, organisations, roles, candidates,<br/>interviews, scoring, invitations, audit,<br/>requirements, shortlist, speech, acs, storage"]
        browser_media["Browser media/runtime layer<br/>Azure ACS Calling SDK<br/>Azure Speech SDK<br/>Azure Avatar WebRTC<br/>Browser Speech fallback"]
    end

    subgraph backend["Backend API (FastAPI :8000)"]
        auth["Auth API<br/>/api/auth/*"]
        orgs["Organisation + Role APIs<br/>/api/orgs/*<br/>/api/roles/*"]
        candidate["Candidate + Application APIs<br/>/api/v1/candidates/*<br/>/api/v1/applications*<br/>/api/invitations*"]
        interview["Interview APIs<br/>/api/v1/interview/chat<br/>/api/v1/interviews/*<br/>/api/v1/interview-scores/*"]
        scoring["Scoring + ranking APIs<br/>/api/v1/scoring/analyze<br/>/api/v1/shortlist/generate<br/>/api/v1/roles/extract-requirements"]
        media["Azure token + media orchestration APIs<br/>/api/v1/acs/*<br/>/api/v1/speech/token<br/>/api/v1/call-automation/*"]
        storage["Storage, audit, retention<br/>/api/storage/upload-url<br/>/api/v1/audit-log<br/>/api/v1/data-retention"]
    end

    subgraph data["Persistence"]
        pg["PostgreSQL<br/>users, orgs, roles, candidates,<br/>applications, interviews, transcripts,<br/>scores, invitations, audit logs, files,<br/>background_jobs, domain_events"]
        localfs["Backend local filesystem<br/>data/uploads<br/>(local-only CV fallback)"]
    end

    subgraph ml["AI / ML Services"]
        openai["Azure OpenAI<br/>AI interviewer chat completions"]
        model1["Model Service 1 :8001<br/>culture / communication scoring<br/>POST /predict"]
        model2["Model Service 2 :8002<br/>technical / competency scoring<br/>POST /predict/transcript"]
    end

    subgraph worker["Internal Workers"]
        backend_worker["backend-worker<br/>DB jobs, domain events,<br/>interview/file/scoring orchestration"]
        acs_worker["python-acs-service<br/>ACS call automation + recording processor"]
    end

    subgraph azure["Azure Services"]
        acs_identity["Azure Communication Services<br/>Identity + token issuance"]
        acs_media["Azure Communication Services<br/>Calling / media plane"]
        speech["Azure Speech Services<br/>STS token endpoint<br/>STT / TTS"]
        avatar["Azure Speech Avatar relay<br/>TURN / WebRTC setup"]
        blob["Azure Blob Storage<br/>SAS uploads + recordings"]
        acs_events["ACS webhook callbacks / Event Grid style events"]
    end

    user --> web
    web --> api
    web --> browser_media

    api --> auth
    api --> orgs
    api --> candidate
    api --> interview
    api --> scoring
    api --> media
    api --> storage

    auth --> pg
    orgs --> pg
    candidate --> pg
    interview --> pg
    scoring --> pg
    media --> pg
    storage --> pg

    candidate -->|local dev fallback only| localfs
    storage --> blob

    interview --> openai
    scoring --> model1
    scoring --> model2

    interview --> backend_worker
    candidate --> backend_worker
    backend_worker --> pg
    backend_worker --> acs_worker
    backend_worker --> model1
    backend_worker --> model2

    media --> acs_identity
    media --> speech
    media --> acs_worker

    acs_worker --> acs_media
    acs_worker --> blob
    acs_worker -->|worker status callbacks| media

    acs_events -->|/api/v1/acs/webhook| media

    browser_media -->|ACS token from backend| media
    browser_media -->|Speech token from backend| media
    browser_media -->|live audio/video calls| acs_media
    browser_media -->|speech recognition + TTS| speech
    browser_media -->|avatar relay token + WebRTC| avatar
```

## Notes

- Frontend API traffic goes through `VITE_API_BASE_URL`, which points at the FastAPI backend.
- JWT auth is issued by FastAPI and stored client-side for subsequent API requests.
- Interview chat uses Azure OpenAI only through the backend.
- Interview scoring fans out from the backend to both model microservices, then combines their outputs.
- The live interview experience uses backend-issued ACS and Speech tokens, but the browser talks directly to Azure runtime services for media, speech, and avatar streaming.
- Candidate CV upload is Blob-first in deployed environments via `/api/storage/upload-url`; `/api/v1/candidates/cv` remains as a local-development fallback.
- Azure Blob Storage is used by the frontend upload flow and by the ACS worker for processed call recordings.
- `backend-worker` processes `background_jobs` and `domain_events` for interview start/completion orchestration, placeholder CV post-processing, and optional async scoring.
- The `python-acs-service` worker remains dedicated to ACS call automation and recording lifecycle events; the backend receives both worker callbacks and ACS webhook events.
- Current frontend API modules directly call `/api/storage/upload-url` for CV upload and `/api/v1/interviews/start` / `/complete` for candidate interview lifecycle actions. Call automation remains internal orchestration.

## Sequence Diagram: Live Interview Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant BW as backend-worker
    participant OAI as Azure OpenAI
    participant ACS as Azure Communication Services
    participant Speech as Azure Speech Services
    participant Avatar as Azure Avatar Relay

    User->>UI: Start interview
    UI->>API: POST /api/v1/interviews/start
    API->>DB: Create/resume interview, mark in_progress
    API->>DB: Write domain event + enqueue orchestration job
    API-->>UI: interview session metadata

    BW->>DB: Poll and claim interview_start_orchestration
    DB-->>BW: job payload
    Note over BW,API: If call automation metadata is missing, orchestration falls back to browser-managed mode

    UI->>API: POST /api/v1/acs/token
    API->>ACS: Create identity + issue token
    ACS-->>API: ACS token
    API-->>UI: token + user_id

    UI->>API: POST /api/v1/speech/token
    API->>Speech: Request speech token
    Speech-->>API: Speech token
    API-->>UI: token + region

    UI->>ACS: Join/start live call via ACS SDK
    UI->>Speech: Start STT / TTS via Speech SDK
    UI->>Avatar: Fetch relay token and open WebRTC avatar session

    loop Interview conversation
        User->>UI: Speaks answer
        UI->>Speech: Stream microphone audio
        Speech-->>UI: Transcript text
        UI->>API: POST /api/v1/interview/chat
        API->>OAI: chat.completions.create(...)
        OAI-->>API: Next interviewer response
        API-->>UI: AI reply
        UI->>Speech: Speak AI reply
    end

    UI->>API: POST /api/v1/interviews/{id}/transcripts
    API->>DB: Save transcript segments
    UI->>API: POST /api/v1/interviews/{id}/complete
    API->>DB: Update interview/application state
    API->>DB: Write completion/scoring events + jobs
```

## Sequence Diagram: Scoring Pipeline

```mermaid
sequenceDiagram
    actor Recruiter as Recruiter / Reviewer
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant BW as backend-worker
    participant M1 as Model Service 1
    participant M2 as Model Service 2

    Recruiter->>UI: Open completed interview
    UI->>API: GET /api/v1/interviews/{id}
    API->>DB: Load interview
    DB-->>API: Interview metadata
    API-->>UI: Interview details

    UI->>API: GET /api/v1/interviews/{id}/transcripts
    API->>DB: Load transcript segments
    DB-->>API: Transcript
    API-->>UI: Transcript

    opt Async auto-score enabled
        BW->>DB: Claim scoring_run job
        BW->>M1: POST /predict
        BW->>M2: POST /predict/transcript
        BW->>DB: Persist async score result
    end

    UI->>API: POST /api/v1/scoring/analyze
    API->>DB: Resolve org / role / application context
    DB-->>API: Context + rubric inputs

    par Culture / communication model
        API->>M1: POST /predict
        M1-->>API: Culture scoring result
    and Technical / competency model
        API->>M2: POST /predict/transcript
        M2-->>API: Skill scoring result
    end

    API->>API: Merge dimensions + compute overall score
    API-->>UI: Scoring response

    UI->>API: POST /api/v1/interviews/{id}/scores
    API->>DB: Persist interview score + dimensions
    DB-->>API: Saved score
    API-->>UI: Stored score result
```
