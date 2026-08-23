# OmniView

Workspace dashboard for LLM operations: **usage and cost**, **document analysis**, and **background jobs** with retries and reconciliation.

Local stack (no Azure account required): FastAPI, Postgres, Redis, a mock LLM worker, React UI.

## Features

- **Usage** — daily spend, failed-request count, cost by provider/model (Postgres `DECIMAL`, rollup table)
- **Documents** — virtualized list, URL filters, insights panel, analyze via jobs
- **Jobs** — lease-based workers, heartbeat, DLQ, idempotent retry, blob path = `job_id`
- **Tenancy** — org vs workspace roles; every query is scoped

## Stack

| Layer | Choice |
|-------|--------|
| UI | React, TypeScript, Vite, TanStack Query, Recharts |
| API | FastAPI, SQLAlchemy (async) |
| Worker | Python, Redis queue, filesystem blobs |
| Data | Postgres 16, Redis 7 (Docker Compose) |

Postgres is the source of truth. Redis is cache and queue.

## Run locally

**Need:** Docker Desktop, Python 3.11+, Node 20+.

```powershell
.\scripts\setup.ps1
```

```powershell
# Terminal 1 — API  (http://localhost:8000/docs)
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — worker
.\.venv\Scripts\Activate.ps1
python worker\main.py

# Terminal 3 — UI  (http://localhost:5173)
cd frontend
npm run dev
```

Copy [`.env.example`](./.env.example) to `.env` if you skip `setup.ps1`.

### Seed users

Auth is a demo header: `X-User-Id`.

| Role | ID |
|------|-----|
| Org owner | `cccccccc-cccc-cccc-cccc-ccccccccccc1` |
| Workspace admin (Alpha only) | `cccccccc-cccc-cccc-cccc-ccccccccccc2` |

Workspaces: Alpha `…bbb1`, Beta `…bbb2`. Switching to the admin user on Beta usage should return 403.

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
pytest -q
```

## Layout

```
frontend/     Vite + React
backend/      FastAPI
worker/       Job worker (mock LLM)
docker-compose.yml
assets/       Architecture diagrams
```

## Configuration

| Env | Meaning |
|-----|---------|
| `LEASE_SECONDS` | Worker lease TTL (heartbeat renews it) |
| `MAX_JOB_RETRIES` | Then DLQ |
| `MOCK_LLM_DELAY_SECONDS` | Simulated LLM latency |
| `MOCK_LLM_FAILURE_RATE` | 0–1, for reliability testing |

Blobs: `data/blobs/{job_id}.json`. Queue: Redis list `omniview:jobs`.

## License

MIT — see [LICENSE](./LICENSE).
