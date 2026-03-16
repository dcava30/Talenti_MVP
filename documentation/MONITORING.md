# Monitoring & Observability

Talenti runs as a FastAPI service backed by PostgreSQL and Azure integrations. Monitoring should focus on API latency, error rates, background jobs, and Azure dependency health.

## What to Monitor

### API Health
- `/health` endpoint for liveness checks.
- HTTP 5xx error rate on `/api/*` routes.
- Latency percentiles (p50/p95/p99).

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
- Count of `background_jobs` stuck in `pending` or `running`.
- ACS worker callback failures.

## Logs

- Use structured JSON logging in the FastAPI server.
- Include request ID, user ID (when available), and route in log context.

## Alerts

- **API Down:** `/health` unreachable for > 2 minutes.
- **Auth Failures:** sustained spike in 401/403 responses.
- **Azure Dependency Errors:** 5xx/timeout spikes on ACS, Speech, OpenAI, or Blob APIs.
- **Disk Pressure:** PostgreSQL storage low on disk (<10%).
- **Job Backlog:** `background_jobs` pending queue age exceeds expected poll/retry window.

## Troubleshooting Checklist

1. Check FastAPI logs for stack traces.
2. Check `backend-worker` logs if orchestration, CV post-processing, or async scoring is stalled.
3. Verify `.env` configuration for Azure keys, `DATABASE_URL`, `BACKGROUND_WORKER_POLL_INTERVAL_SECONDS`, and `AUTO_SCORE_INTERVIEWS`.
4. Confirm PostgreSQL connectivity, storage capacity, and server health.
5. Verify Azure service health and quotas.


