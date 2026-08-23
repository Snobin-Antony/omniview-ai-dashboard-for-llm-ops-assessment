#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

cp -n .env.example .env 2>/dev/null || true

echo "==> Starting Postgres + Redis"
docker compose up -d

echo "==> Waiting for healthchecks"
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U omniview -d omniview >/dev/null 2>&1 \
    && docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> Python venv + deps"
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate || source .venv/Scripts/activate
pip install -q -r backend/requirements.txt

echo "==> Seed database"
cd backend && python -m app.seed && cd ..

echo "==> Frontend deps"
(cd frontend && npm install)

echo "Ready. Run in three terminals:"
echo "  1) source .venv/Scripts/activate && cd backend && uvicorn app.main:app --reload --port 8000"
echo "  2) source .venv/Scripts/activate && python worker/main.py"
echo "  3) cd frontend && npm run dev"
