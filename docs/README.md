# Docs

How this assessment was turned into a local demo, and where each artifact lives.

## Interview vs this repo

The original exercise asked for a **PDF** of approach, risks, and verification — not a full product. This repo is the **development replica** I used to prove that approach: requirements first, then plan, agent guides, build, test, and debug.

| Document | Purpose |
|----------|---------|
| [Technical Exercise Applied AI and R&D Recruitment 1.docx](../Technical%20Exercise%20Applied%20AI%20and%20R&D%20Recruitment%201.docx) | Original interviewer problems |
| [Technical Exercise_ AI-Forward Engineering.pdf](../Technical%20Exercise_%20AI-Forward%20Engineering.pdf) | Submission PDF (process + answers + screenshots) |
| [Technical Exercise_ AI-Forward Engineering.docx](../Technical%20Exercise_%20AI-Forward%20Engineering.docx) | Same content as Word |
| [AGENTS.md](../AGENTS.md) | What the AI agent may draft vs what I own |
| [CLAUDE.md](../CLAUDE.md) | Claude-specific rules for this repo |
| [plan.md](../plan.md) | MVP plan from Plan mode |
| [README.md](../README.md) | How to run the demo |

## Working method

1. Read the three problems → write requirements in the README (ship / defer / blocked).
2. Local assumptions: no Azure credentials, mock LLM, header auth, filesystem blobs, Redis as queue.
3. Plan mode → `plan.md` (platform → jobs/worker → usage → documents).
4. Write `AGENTS.md` / `CLAUDE.md` **before** application code.
5. Agent/build mode → implement the local stack.
6. Test, then Debug mode for false-failed jobs and duplicates.
7. Screenshots of the three pages in `assets/`.

## Architecture diagrams and UI screenshots

| File | Problem |
|------|---------|
| [`assets/local_demo_architecture.png`](../assets/local_demo_architecture.png) | Local stack from the plan (no Azure) |
| [`assets/problem1_data_flow.png`](../assets/problem1_data_flow.png) | Usage event → rollup → API → dashboard |
| [`assets/problem1_usage_admin_view.png`](../assets/problem1_usage_admin_view.png) | Usage admin page |
| [`assets/problem2_document_insights.png`](../assets/problem2_document_insights.png) | Document Insights page |
| [`assets/problem3_state_machine.png`](../assets/problem3_state_machine.png) | Job status machine |
| [`assets/problem3_jobs_worker.png`](../assets/problem3_jobs_worker.png) | Jobs page |

## Tests

From `backend/`:

```powershell
pytest -q
```

Coverage includes tenancy (403), usage rollup accuracy, duplicate job claim, blob reconcile, list-poll heal, `/retry` idempotency.

## What is not in this demo

- Real Azure Blob/Queue and live OpenAI/Vertex keys
- Production OIDC/JWT
- Org-level usage UI (API exists)
- Encrypted IndexedDB / density modes
- Top-workflows-by-cost table
