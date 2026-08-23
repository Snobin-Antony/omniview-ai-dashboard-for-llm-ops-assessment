# OmniView local demo helpers (Windows PowerShell / make-compatible via scripts)

.PHONY: up down seed api worker ui test setup

up:
	docker compose up -d

down:
	docker compose down

seed:
	cd backend && python -m app.seed

api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	python worker/main.py

ui:
	cd frontend && npm run dev

test:
	cd backend && pytest -q

setup:
	docker compose up -d
	cd backend && pip install -r requirements.txt && python -m app.seed
	cd frontend && npm install
