# CLAUDE.md — Instructions for Claude

This file guides Claude (Claude Code, Cursor Claude, etc.) when working in this repository. For the full AI protocol, see [AGENTS.md](./AGENTS.md).

## Project context

This repo supports the **OmniView AI Dashboard / LLM Ops Assessment** — a reference architecture for:

1. **Usage & Cost Admin View** — workspace/org analytics from LLM usage events
2. **Document Insights** — virtualized document list with filters and insights panel
3. **Worker Reliability** — idempotent job processing with lease, DLQ, and reconciliation

Stack: React + TypeScript + Vite + TanStack Query + shadcn-style UI · FastAPI · Postgres · Redis · Azure Blob/Queue (or local equivalents for dev).

Requirements and build order: [README.md](./README.md).

---

## How Claude should work here

### Do freely

- Explore the codebase and read existing patterns before editing
- Draft boilerplate: models, routes, components, hooks, tests
- Look up library syntax (FastAPI dependencies, TanStack Query keys, SQLAlchemy, Azure SDK)
- Propose small, focused diffs aligned with README epics

### Require human approval before

- Changing auth, tenancy, or role-check logic
- Modifying job state machine transitions or lease/idempotency rules
- Adding new API routes that expose cross-tenant data
- Choosing architecture alternatives (e.g. moving source of truth from Postgres to Redis)

### Never do

- Import IndexedDB drivers directly in React components (use `DocumentRepository` facade)
- Use `useEffect` for data fetching (use TanStack Query)
- Skip `WHERE workspace_id` / `WHERE org_id` in database queries
- Use floating-point for currency — use Postgres `DECIMAL`
- Force-push, amend pushed commits, or skip git hooks unless explicitly asked

---

## Code review checklist

Before considering a task done, verify:

- [ ] Authorization enforced at API layer, not only in UI
- [ ] Query keys include `workspace_id` to prevent cache leakage
- [ ] Job updates follow: Postgres first (durable), then Redis (cache)
- [ ] Worker blob writes use `job_id` as path for idempotency
- [ ] Loading, error, and empty states handled in UI features
- [ ] Tests cover tenancy boundaries where applicable

---

## Stop conditions

Stop and ask the user if:

- The same bug persists after two fix attempts
- Requirements in README conflict with existing code
- Real Azure/LLM credentials would be needed (prefer mocks for local dev)
- Scope grows beyond the current epic without explicit approval

---

## MVP build priority

When implementing, prefer this order:

1. Epic 0 — platform (auth, org/workspace, Postgres, Redis, UI shell)
2. Epic 3 — jobs + worker (mock LLM, lease, reconciliation)
3. Epic 1 — usage dashboard (events from worker)
4. Epic 2 — document insights (API-first, no IndexedDB in MVP)

Ship the “MVP” items in README first; defer listed items unless the user asks otherwise.

---

## Diagrams

Architecture diagrams live in `assets/`:

- `problem1_data_flow.png` — usage event → rollups → API → dashboard
- `problem3_state_machine.png` — job status state machine

Refer to these when implementing worker or analytics flows.
