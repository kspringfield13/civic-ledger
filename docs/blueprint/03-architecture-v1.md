# Blueprint 03 — System Architecture v1 (Deliverable E)

Status: DESIGN. Extends `docs/architecture.md` (which remains the one-page
summary) into a buildable v1. Subordinate to the governance docs; if anything
here conflicts with `LEGAL_AND_ETHICAL_BOUNDARIES.md`, `DATA_SOURCE_POLICY.md`,
`EVIDENCE_STANDARD.md`, `DETECTION_PRINCIPLES.md`, or `GOVERNANCE.md`, those
win. Companion data model: `05-data-model.md`. Audit/event requirements this
doc places in the service layer are defined in
`09-governance-and-safety-controls.md` §2.

Everything this pipeline produces is a **risk signal or case lead for human
review — never a finding or accusation.**

---

## 1. Design goals and constraints

1. **Registered-source-only ingestion.** No bytes enter the system without a
   `DataSource` row whose registry entry is operator-approved
   (`DATA_SOURCE_POLICY.md`). Enforced in code, not convention (§3.1).
2. **Chain of custody.** Every retrieved artifact is SHA-256 hashed at
   ingestion and every derived row can be traced back to raw bytes
   (`EVIDENCE_STANDARD.md`).
3. **Reproducibility.** Same inputs + same code version + same detector spec
   version ⇒ same outputs (`DETECTION_PRINCIPLES.md` #6).
4. **Two-dialect reality.** SQLite for dev/prototype, Postgres for prod, one
   `DATABASE_URL` switch (existing `backend/app/database.py`). Every design
   choice below is checked against both dialects.
5. **One-operator scale now, agency scale later.** v1 runs on a laptop or a
   single small VM. §9 names the seams where scale is added later without
   rearchitecting — and explicitly defers building them.

## 2. Layered dataflow

```
            ┌────────────────────────────────────────────────────────────┐
            │ L0 RAW        files in data/raw/ + SourceDocument rows     │
            │               (immutable bytes, SHA-256, locator, license) │
            └───────────────┬────────────────────────────────────────────┘
                            │ parse + normalize (services/normalization.py)
            ┌───────────────▼────────────────────────────────────────────┐
            │ L1 CLEAN      typed fact tables: contract_awards,          │
            │               grant_awards, payments, exclusion_records    │
            │               each row → source_document_id + record locator│
            └───────────────┬────────────────────────────────────────────┘
                            │ entity resolution (services/entity_resolution.py)
            ┌───────────────▼────────────────────────────────────────────┐
            │ L2 ENTITY     agencies, vendors, person_officers,          │
            │               addresses, relationship_edges                │
            └───────────────┬────────────────────────────────────────────┘
                            │ detector engine (YAML specs, services/detectors.py)
            ┌───────────────▼────────────────────────────────────────────┐
            │ L3 RISK       risk_signals + evidence_items                │
            │               (evidence gate: services/evidence.py)        │
            └───────────────┬────────────────────────────────────────────┘
                            │ lead assembly (bundling related signals)
            ┌───────────────▼────────────────────────────────────────────┐
            │ L4 REVIEW     case_leads, review_actions (humans only)     │
            └────────────────────────────────────────────────────────────┘
                 every layer writes audit_events (append-only, §7)
```

Data flows downward only. Feedback flows upward as *parameters*, not data
edits: structured dismissal reasons (`ReviewAction.reason_code`) inform
threshold changes, which land as new detector spec versions — never as
mutation of existing signals.

### 2.1 What lives where (files vs tables)

| Layer | Storage | Rationale |
|---|---|---|
| L0 raw bytes | Files under `data/raw/` (git-ignored), one metadata row per artifact in `source_documents` | Blobs don't belong in SQLite; files + SHA-256 give cheap immutability and later map 1:1 onto object storage keys (§9) |
| L0 metadata | `data_sources`, `source_documents`, `pipeline_runs` tables | Queryable provenance; joins to everything |
| L1 clean facts | Tables (`contract_awards`, `grant_awards`, `payments`, `exclusion_records`) | Detectors are set-based queries; facts must be indexable |
| L2 entities | Tables (`agencies`, `vendors`, `person_officers`, `addresses`, `relationship_edges`) | Same |
| L3/L4 | Tables (`risk_signals`, `evidence_items`, `case_leads`, `review_actions`) | Same, plus audit requirements |
| Detector specs | YAML files in `detectors/` (git) | Reviewable artifacts; git history is the spec version audit trail |
| Case packet exports | Files under `data/processed/exports/` (git-ignored), content-hashed, logged as `export` audit events | Per `09-…` §2 |

`data/processed/` is scratch for intermediate artifacts only; nothing under it
is authoritative. Anything a signal relies on must be in tables or `data/raw/`.

## 3. Ingestion layer

### 3.1 Registered-source gate

`services/ingestion.py` exposes one entry point per retrieval, roughly:

```
ingest(source_name, fetch_plan) →
  1. load DataSource by name; REFUSE unless approved_at is set
     (raise UnregisteredSourceError — no bypass parameter exists)
  2. check terms/rate-limit notes; apply per-source politeness config
  3. fetch bytes (or accept operator-provided file path)
  4. sha256 = hash(bytes); write file (§3.2); insert/skip SourceDocument (§4.2)
  5. parse → normalize → upsert L1 rows with lineage columns (§4.1)
  6. write pipeline_run + ingestion_run audit event (§7)
```

Step 1 is the only place source authorization is checked, and every fetcher
must go through it. The engineering agent never registers or approves a
source; that is an operator action (`GOVERNANCE.md`).

Operator-provided files (authorized uploads) take the same path: the operator
registers a `DataSource` with `access_basis="operator_authorized"`, and the
file is hashed and stored like any other artifact. No side door.

### 3.2 Raw file layout

```
data/raw/<source_slug>/<YYYY>/<YYYY-MM-DDTHHMMSSZ>__<sha256_first12>__<safe_name>
e.g.
data/raw/sam_exclusions/2026/2026-07-03T060002Z__a1b2c3d4e5f6__exclusions_extract.csv
```

- `source_slug` derives from `DataSource.name` (recorded on the row so the
  mapping is explicit, not inferred).
- Files are **write-once**: ingestion never overwrites or edits a raw file.
  A corrupted download is deleted and re-fetched as a new artifact.
- `SourceDocument.storage_path` (new column, see `05-data-model.md`) records
  the relative path; `sha256` proves content; `locator` records where it came
  from (URL, API request descriptor, or `upload:<operator-stated-origin>`).
- Full SHA-256 is the identity of the bytes; the 12-char prefix in the
  filename is only for human navigation.

### 3.3 Fetcher contract (per source)

Each source gets a small fetcher module under
`backend/app/services/sources/` implementing:

- `plan()` — what would be fetched (used for dry runs and rate-limit review);
- `fetch()` — returns `(bytes, locator, retrieval_method)` per artifact;
- `parse(bytes)` — yields `(record_locator, record_dict)` pairs where
  `record_locator` is deterministic for the same bytes (§4.1);
- a `SOURCE_NAME` constant matching the registered `DataSource.name` exactly.

Fetchers contain zero normalization logic (that stays in
`services/normalization.py`, shared and tested) and zero authorization logic
(that stays in the gate). Column-name pinning per
`01-data-source-inventory.md` happens in `parse()` with loud failures on
unexpected headers — schema drift must break the run, not silently mis-map.

## 4. Lineage, versioning, idempotency

### 4.1 Row-level lineage: normalized row → raw bytes

Every L1 fact row carries two lineage columns:

- `source_document_id` (FK, exists today) — which artifact;
- `source_record_locator` (new, see `05-data-model.md`) — which record inside
  it, in a deterministic scheme per format:
  - CSV/flat file: `csv:row=<1-based data row>` (header excluded);
  - JSON API page: `json:<request-page>#<index>` or the record's own stable
    key when the source provides one (e.g. an award ID), prefixed `key:`;
  - The scheme string is part of the fetcher's contract and its tests.

Resolution path for any claim: fact row → (`source_document_id`,
`source_record_locator`) → file at `storage_path`, integrity-checked against
`sha256` → the exact record. This is what `EVIDENCE_STANDARD.md`'s "quoted,
not paraphrased" fields point at. We deliberately do **not** copy every raw
record into a staging table in v1 — the raw file plus a deterministic locator
gives the same guarantee at half the storage. If a future source's format
makes locators unstable, a `raw_records` staging table is the named fallback
(§9), not a rewrite.

### 4.2 Artifact-level idempotency

- Before writing a `SourceDocument`, ingestion checks for an existing row with
  the same `(data_source_id, sha256, locator)`. Hit ⇒ the artifact is
  unchanged: skip file write and L1 upserts, log the run as
  `outcome="unchanged"`. (A repeated retrieval that found identical bytes is
  still evidence-relevant, so the run and its timestamp are recorded in
  `pipeline_runs` — the original `SourceDocument.retrieved_at` is not edited.)
- Same bytes at a *different* locator (e.g. mirror vs. origin) is a new
  `SourceDocument` — provenance is (bytes × where-from), not bytes alone.

### 4.3 Record-level idempotency (re-ingestion and reprocessing)

Two distinct operations, both idempotent:

- **Re-ingestion** (new artifact from the same source): L1 rows are upserted
  on the table's natural key (defined per table in `05-data-model.md`, e.g.
  `(agency_id, award_key)` for contract awards). Changed values update the row
  and bump `last_seen_document_id`; the previous `source_document_id` chain is
  preserved via the write-once raw files and `pipeline_runs`, so history is
  reconstructable even though L1 holds current state.
- **Snapshot sources** (e.g. a daily exclusions extract, which is a full
  point-in-time list, not a delta): rows are keyed
  `(source_document_id, source_record_locator)` and the "current" set is
  defined as *rows from the latest successfully ingested document of that
  source*. Old snapshots' rows persist untouched — signals that cited them
  stay resolvable forever. Detectors query the current set; evidence pins the
  specific document.
- **Reprocessing** (same raw artifact, new parser/normalizer code): re-runs
  `parse()`+normalize over the stored file. Because normalization is
  deterministic (pure functions in `services/normalization.py`, no clock, no
  randomness, no network) and upserts key on natural keys, reprocessing the
  same artifact with the same code version is a no-op, and with new code it
  converges to the new code's output. Reprocessing never re-fetches.

### 4.4 What "version" means, per artifact type

| Thing | Versioned by | Recorded where |
|---|---|---|
| Raw bytes | SHA-256 | `source_documents.sha256` |
| Parser/normalizer/ER code | git commit SHA | `pipeline_runs.code_git_sha` |
| Detector logic | `version:` in the YAML spec (+ git history) | `risk_signals.detector_version` (exists) |
| A pipeline execution | `pipeline_runs.id` | referenced by audit events; `risk_signals.pipeline_run_id` (new) |

## 5. Scheduling: cron/APScheduler, not Airflow

**Decision: v1 uses OS cron (or the operator's launcher) invoking `make`
targets, with APScheduler inside the FastAPI process as an optional
convenience for the single-VM deployment. No Airflow/Dagster/Prefect.**

Justification, specific to this project:

- The v1 schedule is trivially small: on the order of one daily pull
  (exclusions extract), one monthly pull (entity extract), periodic bulk/API
  award pulls, and detector runs after ingests. That is a handful of
  independent jobs, not a DAG with fan-out.
- Airflow's real costs — a metadata database, scheduler + webserver processes,
  worker model, upgrade treadmill — buy dependency graphs, backfill UX, and
  multi-team concurrency we don't have. On a mobile-driven, one-operator
  workflow (`CLAUDE.md`), that's pure overhead and a new attack/maintenance
  surface.
- Our correctness needs (did it run, with what inputs, what did it produce)
  are met by `pipeline_runs` + audit events, which we need anyway for
  governance — an orchestrator's run history would duplicate, not replace,
  them.
- Job ordering ("run detectors after today's ingest") is handled by a single
  sequential runner command (`make pipeline` → ingest sources, then detectors)
  rather than inter-job dependencies. Sequential is a feature at this scale:
  no concurrent-write questions on SQLite.

Concrete shape:

- `make ingest SOURCE=<slug>` and `make detect` (new targets) wrap CLI entry
  points; `make pipeline` runs the daily sequence.
- Cron entry (documented, operator-installed) calls `make pipeline` and
  relies on `pipeline_runs.outcome` + a nonzero exit code for failure
  visibility; failures are surfaced in the dashboard's ops panel (Phase 4).
- A mutex (lock file or `pipeline_runs` row with `running` status checked at
  start) prevents overlapping runs — required for SQLite, still sensible on
  Postgres.
- Revisit trigger (recorded here so it's a decision, not drift): move to a
  real orchestrator only when we have >~10 interdependent jobs, multi-hour
  backfills that need resumability, or more than one concurrent operator.

## 6. Transforms: Python services vs dbt

**Decision: Python services (SQLAlchemy Core/ORM, set-based queries, pure
normalization functions) for all v1 transforms. No dbt in v1.** Tradeoffs
considered:

| Concern | dbt-style SQL | Python services (chosen) |
|---|---|---|
| Two dialects (SQLite dev / PG prod) | dbt targets Postgres well; SQLite support exists only via a community adapter — maturity **must be verified**, and dialect-specific SQL would fork our logic (confidence: moderate; verify before ever adopting) | SQLAlchemy already abstracts both dialects in this repo; one code path, tested on both in CI |
| Evidence gate | Hard to enforce "no signal without evidence" inside SQL models; the gate (`services/evidence.py`) is Python and must remain the single choke point | Gate sits naturally in the same call path |
| Row-level lineage semantics | dbt lineage is model-level (table→table), not row→raw-byte | Our lineage is row-level by design (§4.1); Python writes the locator columns as it parses |
| Fuzzy matching / ER | Name normalization, match-quality scoring don't fit SQL | Already implemented as tested pure functions |
| Reviewable transform logic | dbt SQL + docs are genuinely nice artifacts | Mitigation: transforms live in small, single-purpose modules with docstrings stating input tables → output tables; detector *logic* is already declarative YAML, which covers the highest-review-value layer |
| Team/tooling | Adds a second toolchain, second config, second scheduler integration | Zero new dependencies |

What we keep from the dbt philosophy without the tool: transforms are
**declarative about their interfaces** (each module documents inputs/outputs
and is a pure function of tables + code version), **tested with fixture data**
(`data/sample/`), and **rebuildable from raw** (`make rebuild` = wipe L1–L3,
reprocess all stored artifacts, rerun detectors; L4 human data is never wiped).
Signals produced by a rebuild are matched to existing rows via the
signal fingerprint (`05-data-model.md`, `risk_signals.signal_key`) so review
state is preserved.

## 7. Reproducibility and audit logging

### 7.1 Reproducibility rules (enforced, not aspirational)

1. Every ingest/transform/detector execution writes a `pipeline_runs` row
   *before* doing work and finalizes it after: kind, `code_git_sha`, params
   JSON, input `source_document_id` set (JSON array), started/finished,
   outcome, error text.
2. Transform and detector code must be deterministic: no wall-clock inputs to
   logic (timestamps are metadata only), no unordered iteration feeding
   tie-breaks (explicit `ORDER BY` before any "first wins" rule), no network
   calls outside fetchers, no randomness.
3. Detector runs record `detector_id` + `detector_version` on every signal
   (already in the model) plus `pipeline_run_id` (new). Contract tests already
   validate specs; the engine must refuse to run a spec whose file content
   hash differs from the version it claims *within one run* (cheap guard
   against editing a spec without bumping `version`).
4. Signal idempotency: a deterministic `signal_key` (hash of detector_id +
   detector_version + subject + the identifying evidence facts) makes detector
   re-runs upsert rather than duplicate. Same inputs + same spec version ⇒
   the same `signal_key`s ⇒ no new rows.
5. `make rebuild` from the same raw set + same git SHA must produce
   byte-identical L1–L3 content (modulo surrogate ids and run metadata). This
   is a testable claim; a CI job on sample data asserts it (Phase 2+).

### 7.2 Audit logging placement

Per `09-governance-and-safety-controls.md` §2: a single append-only
`audit_events` table, written **from the service layer** — the same functions
that perform ingests, detector runs, state transitions, and exports emit the
event inside the same DB transaction, so no API route or CLI path can perform
an audited action without its event. Routers never write audit rows directly;
they call services. `pipeline_runs` (operational lineage, §7.1) and
`audit_events` (governance narrative) are distinct on purpose: runs are
queryable engineering data, events are the immutable record; ingestion/detector
audit events carry the `pipeline_run_id` in their payload. Append-only is
enforced by code review now and DB permissions in Postgres (Phase 5), matching
the 09 doc.

## 8. Failure and partial-ingest handling

- Fetch failure: `pipeline_runs.outcome="failed"`, no `SourceDocument`, no L1
  writes. Cron surfaces via exit code.
- Parse failure mid-file: the artifact is already safely stored (file +
  `SourceDocument` committed first), L1 upserts run in one transaction per
  artifact — a parse crash rolls back L1 cleanly and the artifact can be
  reprocessed after a code fix. Outcome `"partial"` is reserved for
  multi-artifact runs where some artifacts succeeded.
- Schema drift (unexpected columns): hard failure by design (§3.3).
- Source revocation: operator flips the source; ingestion refuses at the gate;
  dependent signals flagged `source_revoked` per `DATA_SOURCE_POLICY.md`
  (the flag propagates via `evidence_items → source_documents → data_sources`).

## 9. How it scales later — named seams, explicitly not built now

| Pressure | Seam prepared in v1 | Later change (not now) |
|---|---|---|
| Award/payment volume outgrows one table scan | Facts carry date columns and stable natural keys | Postgres declarative partitioning by fiscal year on `payments`/`contract_awards`; detectors already filter by date range |
| `data/raw/` outgrows local disk | File identity is `sha256`; path stored per document | Move blobs to S3-compatible object storage keyed by sha256; `storage_path` becomes a URI; hashes and evidence chain unchanged |
| Relationship queries get deep (multi-hop networks) | `relationship_edges` is already a generic typed edge list | Mirror edges into a graph DB (or Postgres recursive CTEs first — cheaper) as a *derived read model*; SQL stays the source of truth |
| Concurrent pipelines / heavy backfills | Sequential runner + run mutex; jobs are already independent CLI entry points | Adopt a real orchestrator per the §5 revisit trigger |
| Unstable record locators in some future format | Locator scheme is per-fetcher | Add `raw_records` staging table for that source only |
| Multi-user review load | API is stateless FastAPI over Postgres | Ordinary horizontal scaling + auth (already Phase 5) |

None of these change the evidence chain: `sha256` + locator + spec version
are storage- and scale-independent by construction.

## 10. Open items to verify before build

- dbt-SQLite adapter maturity is irrelevant *unless* the §6 decision is
  revisited; recorded so the revisit starts from facts, not memory
  (confidence: moderate that an adapter exists; unknown current state).
- Exact natural keys per source (award ID uniqueness scope, exclusions record
  keys) must be pinned from real data dictionaries on first pull — see
  per-table notes and TODOs in `05-data-model.md` (confidence: moderate;
  verify per `01-data-source-inventory.md`).
- SQLite upsert (`INSERT … ON CONFLICT`) and partial-index behavior used by
  the dedup keys must be covered by tests on both dialects (high confidence
  both support what we need — SQLite ≥3.24 for upsert, ≥3.8 for partial
  indexes — but CI should prove it, not this doc).
