# civic-ledger

A lawful, auditable **fraud, waste, and abuse (FWA) risk-intelligence platform** for
public spending. civic-ledger ingests public records and authorized datasets,
normalizes entities, runs transparent rule-based detectors, and produces
**risk signals and review queues — never accusations**.

> ⚠️ **Legal & ethical warning.** This system generates *leads* with confidence
> scores for human review. It must never be represented as proof of fraud.
> It uses only public or explicitly authorized data. Unauthorized access,
> scraping of private systems, privacy invasion, or targeting of individuals
> is out of scope and prohibited. See `LEGAL_AND_ETHICAL_BOUNDARIES.md`.

## Architecture (current scaffold)

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytest, ruff
- **Database:** Postgres (target) with SQLite prototype fallback (default)
- **Frontend:** React + Vite + TypeScript dashboard shell
- **Detectors:** declarative YAML specs in `detectors/`, contract-tested
- **Data:** `data/sample/` fictional seed data only; `data/raw|processed` are git-ignored

## Quick start

```bash
cp .env.example .env        # edit only inside the execution environment
make setup                  # create .venv, install backend deps
make test                   # run tests
make backend                # API at http://localhost:8000 (docs at /docs)
make frontend               # dashboard at http://localhost:5173
```

Optional Postgres: `make db-up`, then set `DATABASE_URL` in `.env`.

## Environment setup

See `docs/environment-setup.md`. Mobile / Claude Code orchestration:
`docs/mobile-claude-code-workflow.md`. Operating manual for Claude sessions:
`CLAUDE.md`.

## Testing

```bash
make test    # health endpoint, normalization, detector spec contracts
make lint
```

## Next step

Issue the next `/goal` prompt (see `ROADMAP.md` and the recommended prompt in
`CLAUDE.md`) to design the ingestion pipeline and first working detector.

## What NOT to do

- Do not commit `.env`, keys, databases, or anything in `data/raw|processed`.
- Do not ingest non-public data without documented authorization (`DATA_SOURCE_POLICY.md`).
- Do not present risk signals as findings of fraud, internally or externally.
- Do not build access, scraping, or deanonymization capabilities against private systems.
