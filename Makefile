# civic-ledger task runner — every target is one short command,
# designed for orchestration from Claude Code (mobile-friendly).
.PHONY: setup backend frontend test lint fmt db-up db-down secrets-scan

setup:            ## install backend deps into .venv
	python3 -m venv .venv && .venv/bin/pip install -q -r backend/requirements.txt

backend:          ## run FastAPI dev server on :8000
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:         ## run Vite dev server on :5173
	cd frontend && npm install && npm run dev

test:             ## run backend test suite
	cd backend && ../.venv/bin/python -m pytest -q

lint:             ## ruff check
	.venv/bin/ruff check backend

fmt:              ## ruff format
	.venv/bin/ruff format backend

db-up:            ## start local Postgres via Docker
	docker compose up -d db

db-down:
	docker compose down

secrets-scan:     ## scan history for leaked secrets (requires gitleaks)
	gitleaks detect --source . || echo "Install gitleaks: https://github.com/gitleaks/gitleaks"
