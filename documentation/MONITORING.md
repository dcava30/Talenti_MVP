# Monitoring & Observability

Talenti runs today as a lean dev-only Azure deployment: one FastAPI backend Container App, PostgreSQL, Blob Storage, and supporting Azure services. Observability in the live environment is currently limited to backend logs, Log Analytics, and Application Insights.

## What to Monitor

### API Health
- `/health` endpoint for liveness checks.
- HTTP 5xx error rate on `/api/*` routes.
- Latency percentiles (p50/p95/p99).
- Presence of `X-Request-ID` on backend responses for incident traceability.

### Database (PostgreSQL)
- Database connectivity and server health for PostgreSQL.
- Disk usage and available capacity.
- Migration status on startup (Alembic).
- Queue depth and job age in `background_jobs`.
- Event volume and write failures in `domain_events`.

### Azure Services
- Azure Communication Services token issuance failures.
- Azure Speech token issuance failures.
- Azure OpenAI request errors/timeouts.
- Azure Blob Storage upload URL generation failures.

### Workers
- `backend-worker` process health when it is started locally.
- Structured queue metrics emitted by `backend-worker` when it is running:
  - `pending_jobs`
  - `oldest_pending_job_age_seconds`
- ACS worker callback failures when the local ACS worker is in use.

## Logs

- Backend API and ACS worker emit structured JSON logs to stdout.
- Backend request middleware adds `X-Request-ID` and includes `request_id`, route, method, status code, and duration in request-completion logs.
- Worker logs include `correlation_id`, `job_type`, `job_id`, and queue-metric events when the worker is running.
- In Azure Container Apps, backend logs flow to Log Analytics and Application Insights.

## Current Azure Monitoring State

The live `dev` environment currently has:

- Log Analytics workspace
- Application Insights component
- backend Container App logs

The live `dev` environment currently does not run:

- Azure Monitor Action Group
- synthetic availability checks
- Azure Monitor metric alerts
- scheduled query alerts
- Azure-hosted worker/model/ACS runtime alerts

The Bicep module still contains future-state alerting and synthetic test definitions for environments that enable them later.

## What To Watch Manually In Dev

- **Backend health:** `GET /health` on the Container App hostname.
- **Frontend reachability:** load the Static Web Apps hostname in a browser.
- **Queue backlog:** inspect `background_jobs` in PostgreSQL if async work appears stalled.
- **Worker progress:** inspect local worker logs when `start-dev-worker-local.ps1` is in use.
- **Azure dependency failures:** look for ACS, Speech, OpenAI, or Blob errors in backend logs.

## Troubleshooting Checklist

1. Check FastAPI logs for stack traces.
2. Check local `backend-worker` logs if orchestration, CV post-processing, or async scoring is stalled.
3. Use the `X-Request-ID` response header to correlate API failures to backend logs in Log Analytics.
4. Verify `.env` or Container App configuration for Azure keys, `DATABASE_URL`, `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS`, `BACKGROUND_WORKER_METRICS_LOG_INTERVAL_SECONDS`, and `AUTO_SCORE_INTERVIEWS`.
5. If you later enable Azure alerting, confirm alert state, web test health, and Action Group delivery.
6. Confirm PostgreSQL connectivity, storage capacity, and server health.
7. Verify Azure service health and quotas.


