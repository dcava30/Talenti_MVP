# Monitoring & Observability

Talenti runs as a FastAPI service backed by SQLite and Azure integrations. Monitoring should focus on API latency, error rates, background jobs, and Azure dependency health.

## What to Monitor

### API Health
- `/health` endpoint for liveness checks.
- HTTP 5xx error rate on `/api/*` routes.
- Latency percentiles (p50/p95/p99).

### Database (SQLite)
- File system health for the SQLite database path.
- Disk usage and available capacity.
- Migration status on startup (Alembic).

### Azure Services
- Azure Communication Services token issuance failures.
- Azure Speech token issuance failures.
- Azure OpenAI request errors/timeouts.
- Azure Blob Storage upload URL generation failures.

## Logs

- Use structured JSON logging in the FastAPI server.
- Include request ID, user ID (when available), and route in log context.

## Alerts

- **API Down:** `/health` unreachable for > 2 minutes.
- **Auth Failures:** sustained spike in 401/403 responses.
- **Azure Dependency Errors:** 5xx/timeout spikes on ACS, Speech, OpenAI, or Blob APIs.
- **Disk Pressure:** SQLite database path low on disk (<10%).

## Troubleshooting Checklist

1. Check FastAPI logs for stack traces.
2. Verify `.env` configuration for Azure keys and `DATABASE_URL`.
3. Confirm SQLite file permissions and storage capacity.
4. Verify Azure service health and quotas.
