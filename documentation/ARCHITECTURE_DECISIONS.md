# Architecture Decisions

> Last Updated: April 2026

This document captures the current architecture for Talenti. The system is a FastAPI + PostgreSQL backend with a React frontend, two ML model scoring services, an Azure Communication Services worker, and Azure service integrations.

## ADR-001: FastAPI + PostgreSQL Backend

**Status:** Accepted

**Decision:** Use FastAPI for the backend API layer and PostgreSQL as the primary datastore.

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

## ADR-005: Database-Backed Background Jobs

**Status:** Accepted

**Decision:** Use a `background_jobs` table polled by `backend-worker` instead of an external message broker (e.g., RabbitMQ, Azure Service Bus).

**Rationale:**
- Avoids introducing an external broker dependency for the current workload scale.
- Jobs are transactionally consistent with the state changes that produce them.
- The `domain_events` outbox pattern ensures events are not lost even if the worker is temporarily unavailable.
- Retry logic with exponential backoff and max attempts is built into the worker.

## ADR-006: Dual Scorecard Architecture

**Status:** Accepted

**Decision:** Interview scoring is split into two independent model services: model-service-1 (culture/behavioural fit) and model-service-2 (skills/technical fit). Scores are never merged into a single composite number.

**Rationale:**
- Culture fit and skills fit are orthogonal assessments that should be evaluated independently.
- Keeping them separate allows recruiters to weight and interpret each dimension on its own terms.
- Each model service can evolve, be retrained, or be replaced independently without affecting the other.
- The five canonical culture dimensions (ownership, execution, challenge, ambiguity, feedback) are structurally different from the JD-driven skills dimensions.

## ADR-007: Decision-Dominant Scoring Logic

**Status:** Accepted

**Decision:** ML classifiers extract signals from interview transcripts, but all scoring decisions are made by deterministic rules with configurable thresholds.

**Rationale:**
- Deterministic decisions are auditable and legally defensible — important for hiring decisions.
- Scoring rules can be explained to candidates and recruiters without exposing ML internals.
- Confidence gating ensures the system flags uncertainty rather than producing overconfident scores.
- Fatal risk flags can override all other signals, providing a safety mechanism.

## ADR-008: Python ACS Service Separation

**Status:** Accepted

**Decision:** Azure Communication Services call automation runs as a separate `python-acs-service` microservice with internal-only ingress, not as part of the main backend.

**Rationale:**
- Call automation has different scaling characteristics and failure modes from the main API.
- Isolating ACS logic prevents call-related issues from affecting core API availability.
- The service communicates with the backend via shared-secret-authenticated callbacks.
- Internal-only ingress reduces the attack surface.

## ADR-009: Trunk-Based Release with Immutable Promotion

**Status:** Accepted

**Decision:** Use trunk-based development on `main` with release-please for versioning. Container images are built once on `main`, signed, attested, and promoted immutably through DEV -> UAT -> PROD without rebuilding.

**Rationale:**
- Build-once-promote-many eliminates "works on DEV but not PROD" class of issues.
- Image signing and attestation provide supply-chain integrity verification at each promotion gate.
- `release-manifest.json` captures exact image digests for reproducible deployments.
- UAT auto-promotes from published releases; PROD requires manual approval by release tag.

