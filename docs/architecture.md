# Architecture

## Flow
```
registered sources ─▶ ingestion (hash + provenance) ─▶ data/raw
        ─▶ normalization ─▶ entity resolution ─▶ Postgres/SQLite
        ─▶ detector engine (YAML specs) ─▶ RiskSignal + EvidenceItem
        ─▶ case leads ─▶ human review (dashboard) ─▶ ReviewAction audit trail
```

## Layers
- **Provenance:** `DataSource`, `SourceDocument` (SHA-256, locator, timestamp).
  Nothing enters the system without a registered source.
- **Entities:** `Agency`, `Vendor`, `PersonOfficer` (official capacities only),
  `Address`, `RelationshipEdge` for typed graph edges.
- **Spend:** `ContractAward`, `GrantAward`, `Payment`, `ExclusionRecord`.
- **Signals:** `RiskSignal` (severity ≠ confidence; spec-versioned),
  gated by `services/evidence.py` — no evidence, no signal.
- **Review:** `CaseLead`, `ReviewAction` (structured dismissal reasons feed
  threshold tuning), `EvidenceItem`.

## Key decisions
- Declarative YAML detectors with contract tests, so hypotheses and
  false-positive modes are reviewable artifacts, not code comments.
- SQLite default / Postgres target: one `DATABASE_URL` switch, SQLAlchemy 2
  typed models compatible with both.
- Backend and frontend are decoupled over JSON; the frontend reads
  `FRONTEND_API_BASE_URL`.
