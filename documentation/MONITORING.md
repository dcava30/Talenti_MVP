# Monitoring & Observability

Talenti runs as a FastAPI service backed by PostgreSQL, Azure integrations, and GitHub Actions deployments. The platform now assumes Azure-native observability with Log Analytics, Application Insights, Azure Monitor alerts, and GitHub Release metadata.

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
- `backend-worker` process health and restart count.
- Structured queue metrics emitted by `backend-worker`:
  - `pending_jobs`
  - `oldest_pending_job_age_seconds`
- ACS worker callback failures.

## Logs

- Backend API and ACS worker emit structured JSON logs to stdout.
- Backend request middleware adds `X-Request-ID` and includes `request_id`, route, method, status code, and duration in request-completion logs.
- Worker logs include `correlation_id`, `job_type`, `job_id`, and queue-metric events.
- In Azure Container Apps, these logs flow to Log Analytics and are used by scheduled query alerts.

## Azure Alerting Baseline

Each environment should have:

- Log Analytics workspace
- Application Insights component
- Azure Monitor Action Group with a shared team email
- Synthetic availability checks for:
  - frontend root URL
  - backend `/health`
- Metric alerts for:
  - backend 5xx spikes
  - backend latency degradation
  - container restart spikes
- Scheduled query alerts for:
  - frontend synthetic failure
  - backend synthetic failure
  - background job backlog
  - background job age

## Alerts

- **Backend Health Down:** backend availability test fails.
- **Frontend Health Down:** frontend availability test fails.
- **Backend 5xx Spike:** container app request metric shows sustained 5xx traffic.
- **Latency Regression:** backend response-time metric exceeds the configured threshold.
- **Container Restarts:** restart count exceeds the configured threshold on backend, worker, model, or ACS apps.
- **Job Backlog:** `pending_jobs` from worker queue metrics exceeds the configured threshold.
- **Job Age:** `oldest_pending_job_age_seconds` exceeds the configured threshold.

## Troubleshooting Checklist

1. Check FastAPI logs for stack traces.
2. Check `backend-worker` logs if orchestration, CV post-processing, or async scoring is stalled.
3. Use the `X-Request-ID` response header to correlate API failures to backend logs in Log Analytics.
4. Verify `.env` or Container App configuration for Azure keys, `DATABASE_URL`, `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS`, `BACKGROUND_WORKER_METRICS_LOG_INTERVAL_SECONDS`, and `AUTO_SCORE_INTERVIEWS`.
5. Confirm Azure Monitor alert state, web test health, and Action Group delivery.
6. Confirm PostgreSQL connectivity, storage capacity, and server health.
7. Verify Azure service health and quotas.


