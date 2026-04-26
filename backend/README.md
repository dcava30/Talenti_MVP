# Talenti Backend

> Last Updated: April 2026

FastAPI backend for the Talenti AI interview platform. This service is the control plane for all platform state — authentication, interview orchestration, scoring coordination, file storage, and Azure service integration.

## Architecture

The backend runs as two processes from the same codebase:

- **API server** (`uvicorn app.main:app`) — handles HTTP requests on port 8000
- **Background worker** (`python -m app.worker_main`) — polls `background_jobs` and `domain_events` tables for async work (resume parsing, auto-scoring, invite prep)

Both processes share the same PostgreSQL database and must be running for the platform to function correctly.

## Prerequisites

- Python 3.11+
- PostgreSQL 16
- Azure credentials (Storage, ACS, Speech, OpenAI) for full functionality

## Local Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

# Configure environment
cp ../.env.example ../.env
# Edit ../.env with your DATABASE_URL, JWT_SECRET, and Azure credentials

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In a separate terminal, start the background worker
python -m app.worker_main
```

Or use the one-command local bootstrap from the repo root:

```powershell
.\scripts\start-local.ps1
```

## Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://postgres:postgres@localhost:5432/talenti` |
| `JWT_SECRET` | Secret key for signing JWTs | *required* |
| `JWT_ACCESS_TTL_MINUTES` | Access token lifetime | `60` |
| `MODEL_SERVICE_1_URL` | Culture fit scoring service | `http://model-service-1:8001` |
| `MODEL_SERVICE_2_URL` | Skills fit scoring service | `http://model-service-2:8002` |
| `ACS_WORKER_URL` | Python ACS service URL | `` |
| `ACS_WORKER_SHARED_SECRET` | Shared secret for ACS worker callbacks | `` |
| `AUTO_SCORE_INTERVIEWS` | Auto-run scoring on interview completion | `false` |
| `TDS_DECISION_SHADOW_WRITE_ENABLED` | Enable dark behavioural Decision Layer persistence behind the scoring flow | `false` |
| `TDS_DECISION_INSPECTION_API_ENABLED` | Enable internal/admin behavioural decision inspection routes | `false` |
| `TDS_SKILLS_SUMMARY_SHADOW_WRITE_ENABLED` | Enable dark Skills Assessment Summary persistence behind the scoring flow | `false` |
| `TDS_SKILLS_SUMMARY_INSPECTION_API_ENABLED` | Enable internal/admin Skills Assessment Summary inspection routes | `false` |
| `TDS_SHADOW_COMPARISON_API_ENABLED` | Enable internal/admin shadow comparison reads for legacy, TDS, and skills artifacts | `false` |
| `TDS_RANKING_AND_SHORTLIST_QUARANTINE_ENABLED` | Disable shortlist ranking payloads under the MVP1 decision policy boundary | `false` |
| `TDS_RECRUITER_DECISION_API_ENABLED` | Enable recruiter-facing behavioural decision reads | `false` |
| `TDS_RECRUITER_SKILLS_SUMMARY_API_ENABLED` | Enable recruiter-facing Skills Assessment Summary reads | `false` |
| `TDS_HUMAN_REVIEW_API_ENABLED` | Enable flagged human review / exception handling create/list routes for authorised admins | `false` |
| `AZURE_STORAGE_ACCOUNT` | Azure Blob Storage account name | `` |
| `AZURE_ACS_CONNECTION_STRING` | Azure Communication Services connection | `` |
| `AZURE_SPEECH_KEY` | Azure Speech Services key | `` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | `` |
| `LOG_LEVEL` | Logging level | `INFO` |

See `.env.example` in the repo root for the complete list.

## Project Structure

```
app/
├── main.py              # FastAPI app, middleware, router registration
├── worker_main.py       # Background worker entry point
├── api/                 # Route handlers (18 modules)
├── core/                # Config, logging, migrations
├── db.py                # Database session management
├── models/              # SQLAlchemy ORM models (28 tables)
├── schemas/             # Pydantic request/response schemas
├── services/            # Business logic and external integrations
└── talenti_canonical/   # Canonical dimension and scoring definitions
```

## Running Tests

```bash
cd backend
pytest
```

## API Documentation

- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Full endpoint reference: [documentation/API_REFERENCE.md](../documentation/API_REFERENCE.md)
- Database schema: [documentation/DATABASE_SCHEMA.md](../documentation/DATABASE_SCHEMA.md)
- Environment setup: [documentation/ENV_SETUP.md](../documentation/ENV_SETUP.md)
