# Talenti ACS Service

> Last Updated: April 2026

FastAPI microservice for Azure Communication Services call automation and recording management. This service handles the server-side orchestration of interview calls — creating outbound calls, starting/stopping recordings, and processing recording artifacts.

## Role in the Platform

This is an **internal service** — it has no public ingress in the deployed Container Apps environment. The main backend delegates call automation requests to this service, and this service calls back to the backend via a shared-secret-authenticated endpoint (`/api/v1/acs/worker-events`) when recordings are ready.

## Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Basic health check | None |
| GET | `/health/ready` | Readiness check (verifies ACS, storage, and backend connectivity) | None |
| GET | `/health/live` | Liveness probe | None |
| POST | `/internal/calls` | Create outbound interview call | Shared secret |
| POST | `/internal/calls/{call_connection_id}/hangup` | Hang up a call | Shared secret |
| POST | `/internal/recordings/start` | Start recording on an active call | Shared secret |
| POST | `/internal/recordings/{recording_id}/stop` | Stop a recording | Shared secret |

All `/internal/*` endpoints require the `X-ACS-Worker-Secret` header matching the `ACS_WORKER_SHARED_SECRET` value.

## Prerequisites

- Python 3.11+
- PostgreSQL 16 (shares the same database as the main backend)
- Azure Communication Services with Call Automation enabled
- Azure Blob Storage for recording artifacts

## Local Setup

```bash
cd python-acs-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure environment (uses the same .env as the backend, or set variables directly)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
```

## Docker

The service is included in the project's `docker-compose.yml` as `acs-worker` and runs on the internal `talenti-network`.

## Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://postgres:postgres@localhost:5432/talenti` |
| `ACS_CONNECTION_STRING` | Azure Communication Services connection string | *required* |
| `ACS_ENDPOINT` | ACS endpoint URL | `` |
| `ACS_CALLBACK_URL` | URL for ACS to send webhook events back | `` |
| `BACKEND_INTERNAL_URL` | Main backend URL for worker-events callback | `` |
| `ACS_WORKER_SHARED_SECRET` | Shared secret for authenticating with the backend | *required in production* |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob Storage connection string | `` |
| `RECORDING_CONTAINER` | Blob container for interview recordings | `interview-recordings` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENVIRONMENT` | Runtime environment (`development` / `production`) | `development` |

## Project Structure

```
app/
├── main.py           # FastAPI app, middleware, router registration
├── config.py         # Pydantic settings
├── logging_utils.py  # Structured logging
├── api/
│   ├── router.py     # API router (health, calls, recordings)
│   └── routes/       # Route handlers
├── db/               # Database layer
├── jobs/             # Background task processing
├── models/           # SQLAlchemy models
├── repositories/     # Data access layer
├── schemas/          # Pydantic schemas
├── security/         # Shared-secret authentication
└── services/         # ACS call automation and recording logic
```

## Related Documentation

- [Architecture Diagram](../documentation/ARCHITECTURE_DIAGRAM.md) — see the Runtime Topology view
- [Monitoring](../documentation/MONITORING.md) — health check and alerting guidance
- [Handover](../documentation/HANDOVER.md) — system overview
