# Architecture Decisions

This document captures the current architecture for Talenti. The system is a FastAPI + SQLite backend with a React frontend and Azure service integrations.

## ADR-001: FastAPI + SQLite Backend

**Status:** Accepted

**Decision:** Use FastAPI for the backend API layer and SQLite as the primary datastore.

**Rationale:**
- Simple, lightweight local development experience.
- Consistent with current `DATABASE_URL` defaults and migrations.
- No external database dependency required for initial deployments.

## ADR-002: JWT Authentication

**Status:** Accepted

**Decision:** Use JWTs issued and validated by the FastAPI service with a local user table.

**Rationale:**
- Keeps auth in the same service boundary as the API.
- Enables local development without third-party auth providers.

## ADR-003: Azure Integrations

**Status:** Accepted

**Decision:** Use Azure Communication Services, Azure Speech, Azure OpenAI, and Azure Blob Storage for communications, transcription, AI responses, and file storage.

**Rationale:**
- Provides scalable managed services aligned with product requirements.
- Keeps the backend responsible for access and key management.

## ADR-004: Frontend + API Contract

**Status:** Accepted

**Decision:** The React frontend communicates with the FastAPI backend via REST endpoints under `/api` and `/api/v1` prefixes.

**Rationale:**
- Clear versioning for API endpoints.
- Compatible with existing frontend API clients.
