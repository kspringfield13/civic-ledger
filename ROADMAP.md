# Roadmap

## Phase 0 — Scaffold (this repo state) ✅
Repo, governance, backend/frontend shells, detector specs, sample data, tests.

## Phase 1 — Data foundation
- Implement SQLAlchemy persistence + Alembic baseline migration.
- Ingestion service for two Tier-1 public sources (recommended first:
  SAM.gov exclusions download + USAspending award data via public API).
- Normalization: name/address canonicalization with tests.
- Source registry populated via the inventory template.

## Phase 2 — First working detectors
- Implement `debarred_vendor_match` and `duplicate_payment` end-to-end:
  spec → engine → RiskSignal rows → evidence links.
- Detector engine reads YAML specs generically (no per-detector hardcoding).
- Backfill contract tests into runtime validation.

## Phase 3 — Review workflow
- Case queue: assign, disposition (confirm-worthy / dismiss / needs-data)
  with structured reasons; ReviewAction audit trail.
- Case packet export (markdown) per EVIDENCE_STANDARD.

## Phase 4 — Dashboard v1
- Real data in the five pages; evidence drill-down; base-rate context.

## Phase 5 — Hardening
- Postgres by default, auth on the API, encrypted secret management,
  CI gates (tests, lint, secrets scan), deployment target decision.
