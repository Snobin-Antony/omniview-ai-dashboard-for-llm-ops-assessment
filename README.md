# OmniView AI Dashboard — LLM Ops Assessment

Local **development demo** for the Applied AI / R&D technical exercise: usage & cost admin, document insights, and reliable document-analysis jobs.

This is **not** their production Azure stack. It is a replica you can run on a laptop: FastAPI + Postgres + Redis + a mock LLM worker + a React UI.

**Submission write-up:** [Technical Exercise_ AI-Forward Engineering.pdf](./Technical%20Exercise_%20AI-Forward%20Engineering.pdf)  
**How the work was done:** [docs/README.md](./docs/README.md) · [AGENTS.md](./AGENTS.md) · [plan.md](./plan.md)

---

## Quick start

**Need:** Docker Desktop, Python 3.11+, Node 20+.

```powershell
# Repo root — Postgres + Redis, Python venv, seed, frontend deps
.\scripts\setup.ps1
```

Then three terminals:

```powershell
# API
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --port 8000

# Worker
.\.venv\Scripts\Activate.ps1
python worker\main.py

# UI
cd frontend
npm run dev
```

- UI: http://localhost:5173  
- API: http://localhost:8000/docs  

Copy [`.env.example`](./.env.example) to `.env` if you are not using `setup.ps1`.

### Seed users (`X-User-Id`)

| Role | User ID | Access |
|------|---------|--------|
| Org owner | `cccccccc-cccc-cccc-cccc-ccccccccccc1` | All workspaces + org analytics |
| Workspace admin | `cccccccc-cccc-cccc-cccc-ccccccccccc2` | Workspace Alpha only |

| Resource | ID |
|----------|-----|
| Org Acme AI | `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` |
| Workspace Alpha | `bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1` |
| Workspace Beta | `bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2` |

Switch user in the header: admin must get **403** on Beta usage.

### Demo path

1. Org owner: Usage, Documents, Jobs on Alpha and Beta.  
2. Workspace admin: Beta usage → 403.  
3. Documents: pick a doc → run analysis → Jobs shows `queued → processing → completed`.  
4. Failed job: **Check again** (reconcile) and **Retry** (no-op if already completed).  
5. Usage cards/chart update from worker `llm_usage_events`.

### Tests

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
pytest -q
```

---

## Local replacements (no cloud keys)

| Exercise / production | This demo |
|----------------------|-----------|
| Azure Blob | `data/blobs/{job_id}.json` |
| Azure Queue | Redis list `omniview:jobs` (+ DLQ) |
| OpenAI / Vertex | Mock delay; optional `MOCK_LLM_FAILURE_RATE` |
| IdP / JWT | `X-User-Id` + seed users |
| Charts | Recharts + Tailwind |

Tunables in `.env`: `LEASE_SECONDS`, `MAX_JOB_RETRIES`, `MOCK_LLM_DELAY_SECONDS`, `MOCK_LLM_FAILURE_RATE`.

---

## Layout

```
frontend/          Vite + React + TypeScript + TanStack Query
backend/           FastAPI + SQLAlchemy (async)
worker/            Lease worker, mock LLM, blobs, usage events
docker-compose.yml Postgres 16 + Redis 7
docs/              Index of plans, agent guides, screenshots
assets/            Architecture diagrams + UI screenshots
```

Postgres is the source of truth. Redis is cache + queue. Queries are scoped by `org_id` / `workspace_id`.

---

## What is implemented

**Platform:** orgs, workspaces, memberships, mock auth, health checks.  

**Jobs / worker:** atomic claim, lease heartbeat, blob path = `job_id`, DLQ, list+GET reconcile if blob exists, `/retry` idempotent.  

**Usage:** DECIMAL cost at write, `daily_usage_rollup`, workspace dashboard (spend, failures, provider/model bars). Org API exists; org UI deferred. Chart X = provider/model; Y = cost (failed also plotted). Seed has three provider/model prices; UI enqueue currently defaults to `openai` / `gpt-4o-mini`.  

**Documents:** cursor list, URL filters, virtualized table, `DocumentRepository` (API only), analyze → job.

**Deferred:** real Azure, OIDC, IndexedDB, density modes, top-workflows table, billing recon, provider picker in the UI.

---

## Docs

| Path | What it is |
|------|-----------|
| [docs/README.md](./docs/README.md) | Index: method, diagrams, tests |
| [AGENTS.md](./AGENTS.md) | Agent protocol (written before app code) |
| [CLAUDE.md](./CLAUDE.md) | Claude-specific rules |
| [plan.md](./plan.md) | MVP plan from Plan mode |
| [Technical Exercise_ AI-Forward Engineering.pdf](./Technical%20Exercise_%20AI-Forward%20Engineering.pdf) | Interview PDF |
| Original `.docx` | Interviewer problem set |

Screenshots: `assets/problem1_usage_admin_view.png`, `problem2_document_insights.png`, `problem3_jobs_worker.png`.
