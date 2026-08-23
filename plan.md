Local OmniView Demo MVP

Goal

Ship a runnable local demo that proves the architecture in README.md: mock tenancy/auth, reliable job worker, usage analytics, and document insights — matching the interview stack with local replacements for Azure.

Local assumptions (documented in README)

Production (exercise)

Local demo

Azure Blob

./data/blobs/{job_id} filesystem

Azure Queue

Redis list + BRPOP/LPUSH

Real LLM providers

Mock worker with configurable delay + failure rate

Auth provider

Header-based mock users (X-User-Id) seeded in DB

Charts

Recharts + shadcn-style Tailwind UI

Seed: 1 org, 2 workspaces, users org_owner + workspace_admin (workspace A only), sample documents and pricing rows.

Architecture

flowchart LR
  UI[frontend Vite React] --> API[backend FastAPI]
  API --> PG[(Postgres)]
  API --> Redis[(Redis job cache + queue)]
  Worker[worker Python] --> Redis
  Worker --> PG
  Worker --> Blob[local filesystem blobs]
  Worker --> Events[llm_usage_events]

Monorepo layout:

frontend/     # Vite + React + TS + TanStack Query + Tailwind
backend/      # FastAPI + SQLAlchemy + Alembic
worker/       # async worker (lease, mock LLM, usage events)
infra/        # docker-compose.yml (postgres, redis)
data/blobs/   # gitignored blob store

Build order (README epics)

Phase 1 — Epic 0: Platform

Docker Compose: Postgres 16 + Redis 7

Backend: FastAPI app, SQLAlchemy models (orgs, workspaces, users, memberships), Alembic migration, seed script

Auth deps: get_current_user, verify_workspace_admin, verify_org_owner (from X-User-Id; every query filters org_id/workspace_id)

Redis client + health endpoints

Frontend shell: Vite app, TanStack Query, role/workspace switcher, routes placeholders

Root docker-compose + Makefile/scripts/dev.sh to run API + worker + UI

Phase 2 — Epic 3: Jobs + Worker (Problem 3)

Tables: jobs (status, worker_id, lease_expires_at, blob_url, retry_count, …)

APIs: POST /jobs, GET /jobs/{id} (reconcile Redis ← Postgres), POST /jobs/{id}/retry (idempotent if completed)

Worker loop: claim via UPDATE … WHERE status=queued RETURNING * → Redis processing → mock LLM → write blob as {job_id} → Postgres completed → Redis → ack queue

Lease expiry re-claim; max retries → failed/DLQ list; reconciler if blob exists but status stale

UI: job list/detail with polling, Retry + Check Again

Tests: duplicate-worker concurrency, partial-failure reconcile, /retry idempotency

Phase 3 — Epic 1: Usage dashboard (Problem 1 MVP)

Tables: llm_usage_events, pricing_rates; worker writes events (DECIMAL cost_usd) on each mock LLM call

Materialized views: daily_usage_rollup (+ refresh helper); defer workflow_cost_rollup / org drill-down if time-tight (README MVP ship-first)

API: GET /api/v1/workspaces/{id}/analytics/usage?from=&to=

UI: workspace Usage page — daily spend, failed count, provider/model chart (Recharts)

Tests: tenancy 403 + rollup sample accuracy

Phase 4 — Epic 2: Document Insights (Problem 2 MVP)

Table: documents (workspace_id, owner_id, title, analysis_status, insights JSON)

APIs: cursor-paginated list + filters; get by id; creating analysis enqueues a job

Frontend: DocumentInsightsPage, filters in URL, useInfiniteQuery + @tanstack/react-virtual, details panel, loading/empty/error

DocumentRepository facade (API-only; no IndexedDB)

Defer: density modes, IndexedDB

Explicitly deferred (README + no Azure)

Real Azure Queue/Blob, Azurite

Org-level usage rollup UI, billing reconciliation

Encrypted IndexedDB, density toggle

Production auth (JWT/OIDC), CI/CD, DLQ admin UI

Demo script (what you show in interview)

Switch user (org owner vs workspace admin) — cross-tenant 403

Start document analysis job — status polling through lease/processing

Simulate failure → Check Again / reconcile after blob present

Usage dashboard updates from worker-emitted events

Point at AGENTS.md conventions enforced in code (query keys, DECIMAL, Postgres truth)

Docs touch

Update README.md with “How to run locally”, assumptions table, and seed users

Keep AGENTS.md / CLAUDE.md as-is for agent workflow during implementation