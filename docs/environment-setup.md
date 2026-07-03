# Environment setup

## Python backend
```bash
make setup                 # python3 -m venv .venv + pip install -r backend/requirements.txt
make test                  # pytest
make backend               # uvicorn on http://localhost:8000 (OpenAPI docs at /docs)
```
Requires Python 3.11+.

## Node frontend
```bash
make frontend              # npm install + vite dev server on http://localhost:5173
```
Requires Node 20+.

## Database
Default is SQLite (`sqlite:///./local.db`) — zero setup, good for prototyping.
Postgres option:
```bash
make db-up                 # docker compose up -d db
# then in .env:
# DATABASE_URL=postgresql+psycopg://civic:civic_dev_only@localhost:5432/civic_ledger
```

## .env setup and key handling rules
```bash
cp .env.example .env
```
- Edit `.env` only inside the execution environment. It is git-ignored.
- All API keys are optional; add one only when its integration is built.
- Never paste keys into chat, commits, logs, or issue text.
- Run `make secrets-scan` (gitleaks) before pushing if you touched config.
- Production: use encrypted secret management (cloud secret manager, SOPS,
  Vault) — dotenv is a development convenience only.

## Troubleshooting
- `ModuleNotFoundError` → re-run `make setup`; confirm commands use `.venv`.
- Port 8000/5173 busy → `--port` flag on uvicorn/vite, or kill the stale process.
- SQLite "database is locked" → stop duplicate backend processes; SQLite is
  single-writer, fine for prototype, not for concurrent use.
- Docker unavailable (e.g. Claude Code Web) → stay on SQLite; everything works.
- `psycopg` missing when switching to Postgres → add `psycopg[binary]` to
  requirements (deliberately not installed in prototype mode).
