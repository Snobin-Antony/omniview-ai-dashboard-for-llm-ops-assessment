# AGENTS.md — AI Interaction Protocol

How AI coding agents (Codex, GitHub Copilot, Cursor Agent, etc.) should work on this project.

## Philosophy

Treat AI agents as highly capable mid-level pair programmers. They excel at pattern matching, generating boilerplate, writing localized tests, and suggesting framework-specific syntax. They **do not** have holistic system context or an inherent sense of security and domain-specific risk.

The human owner defines architecture, security boundaries, and state machines. The agent implements mechanics under review.

---

## What the AI should explore and draft

- **Scaffolding and boilerplate** — CRUD endpoints, ORM models, React component shells, TypeScript interfaces from a provided schema
- **Test generation** — unit tests and edge cases for pure functions or isolated components
- **Syntax and API nuances** — library-specific setup (Azure Queue client, Postgres window functions, TanStack Query hooks, shadcn components)

---

## What the AI must NOT decide alone

- **Architecture and system boundaries** — where data lives, service communication, queues vs synchronous calls
- **Security and authorization** — tenancy checks (org vs workspace), auth middleware, data-leakage prevention
- **State machine logic** — job lifecycle transitions, lease/idempotency rules, DLQ behavior
- **Verification strategy** — which integration and security tests are required

---

## Verification strategy

Never trust, always verify. Review AI-generated code for:

1. Missing authorization checks
2. N+1 query problems
3. Abuse of React `useEffect` (prefer TanStack Query, derived state, URL state)
4. Hardcoded values (tenant IDs, secrets, magic timeouts)
5. Silent error swallowing

Write integration tests and security boundary tests manually to enforce human-defined invariants.

---

## When to stop the agent

Stop the agent and take over if:

- It fails to fix the same issue after **two focused attempts**
- Its suggestion touches **auth, tenancy, or state-machine logic** without explicit human approval
- It proposes bypassing the storage facade or querying across workspace boundaries

Escalation beats repeated wrong patches.

---

## Project-specific conventions

When implementing code in this repo, follow these boundaries:

| Area | Rule |
|------|------|
| Tenancy | Every query must filter by `org_id` or `workspace_id`; never trust client-side filters |
| Job status | Postgres is source of truth; Redis is UI cache only |
| Usage analytics | API reads materialized views, not raw event tables |
| Frontend data | TanStack Query for server state; URL params for filters/selection |
| IndexedDB | Components use `DocumentRepository` facade only — no direct driver imports |
| Cost | Store `cost_usd` as `DECIMAL` in Postgres; compute at event-write time |

---

## Useful prompts for this codebase

```
Draft FastAPI SQLAlchemy models for llm_usage_events and SQL for daily_usage_rollup.
```

```
Generate a React dashboard layout using shadcn components based on this JSON payload.
```

```
Write TanStack useInfiniteQuery boilerplate for documents with cursor pagination and filtering.
```

```
Draft pytest-asyncio test simulating two workers receiving the same queue message.
```

Always review output against the requirements in [README.md](./README.md) before merging.
