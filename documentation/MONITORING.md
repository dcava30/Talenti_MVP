# Monitoring & Observability

> Last Updated: April 2026
>
> **See also:** [ARCHITECTURE_OVERVIEW.md, Section 17](./ARCHITECTURE_OVERVIEW.md#17-logging-monitoring-and-operational-support) for the architectural context of monitoring and observability.

Talenti runs as a set of FastAPI microservices (backend API, backend-worker, model-service-1, model-service-2, python-acs-service) backed by PostgreSQL, Azure integrations, and GitHub Actions deployments. The platform assumes Azure-native observability with Log Analytics, Application Insights, Azure Monitor alerts, and GitHub Release metadata.

## What to Monitor

### API Health
- Backend API: `GET /health` on port 8000.
- model-service-1: `GET /health` on port 8001.
- model-service-2: `GET /health` on port 8002.
- python-acs-service: `GET /health`, `GET /health/ready`, `GET /health/live` (internal).
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

### Workers & Model Services
- `backend-worker` process health and restart count.
- Structured queue metrics emitted by `backend-worker`:
  - `pending_jobs`
  - `oldest_pending_job_age_seconds`
- `python-acs-service` readiness (ACS connection, storage, backend callback connectivity).
- ACS worker callback failures (`/api/v1/acs/worker-events`).
- model-service-1 and model-service-2 prediction latency and error rate.
- Model service container restart count and memory usage (model loading can require 2-4GB).

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
3. Check model-service-1/model-service-2 logs if scoring returns errors or timeouts. Verify `MODEL_SERVICE_1_URL` and `MODEL_SERVICE_2_URL` are reachable from the backend.
4. Check `python-acs-service` logs if call automation or recordings fail. Verify `ACS_WORKER_SHARED_SECRET` matches between backend and ACS service.
5. Use the `X-Request-ID` response header to correlate API failures to backend logs in Log Analytics.
4. Verify `.env` or Container App configuration for Azure keys, `DATABASE_URL`, `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS`, `BACKGROUND_WORKER_METRICS_LOG_INTERVAL_SECONDS`, and `AUTO_SCORE_INTERVIEWS`.
5. Confirm Azure Monitor alert state, web test health, and Action Group delivery.
6. Confirm PostgreSQL connectivity, storage capacity, and server health.
7. Verify Azure service health and quotas.


