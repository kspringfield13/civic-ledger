# Blueprint 11 — Prototype Backlog (Deliverable H)

Status: BACKLOG. Milestones M1–M6 sequence the build described in
`10-build-plan.md` (referenced below as "BP §n"). Maps onto `ROADMAP.md`:
M1–M2 ≈ Phase 1, M3 ≈ Phase 2, M4 ≈ Phases 3–4, M5 ≈ Phase 3 export +
Phase 5 slice, M6 ≈ Phase 5 + DETECTION_PRINCIPLES #7–8. On conflict, the
governance docs win, then ROADMAP, then this file.

## How to use this backlog (mobile workflow, per CLAUDE.md)

- **One task = one `/goal` prompt = roughly one reviewable commit.** Each
  task row is written so it can be pasted after `/goal` as-is. If a task
  turns out bigger than a session, split it and update this file in the same
  commit.
- Every task inherits the standing acceptance criteria: `make test` and
  `make lint` pass; no secrets committed; signal/lead language complies with
  `EVIDENCE_STANDARD.md`; assumptions recorded in the commit message.
- Tasks tagged **[OPERATOR]** are human decisions/approvals the agent must
  not perform (GOVERNANCE.md): source registration sign-off, account
  creation, anything leaving the system. They are listed because they block
  engineering tasks — the agent's job is to prepare them and then stop.
- Within a milestone, tasks are in dependency order unless marked (parallel).

---

## M1 — Ingestion skeleton

**Goal:** real persistence and a gated, auditable ingest path; the fictional
sample data flows through the *production* code path end to end.

**Depends on:** nothing (current repo state).

| ID | Task (one /goal) | Done when |
|---|---|---|
| M1.1 | Initialize Alembic (`alembic.ini`, `env.py` wired to `app.database.Base` and `DATABASE_URL`) + baseline migration `0001` capturing the existing 15 models; add `make db-migrate` | `alembic upgrade head` builds a fresh SQLite DB matching the models; test asserts metadata == migration result |
| M1.2 | Migration + model change: money columns to `Decimal`, timezone-aware UTC datetimes (05 TODO-1, TODO-2) | types verified by a unit test; no float in any amount `Mapped[]` |
| M1.3 | Migration: tighten `source_documents` (sha256 NOT NULL, `storage_path`, `size_bytes`, `content_type`, unique `(data_source_id, sha256, locator)`); add `slug`/`revoked_at`/`registry_commit` to `data_sources` (05 TODO-4, TODO-5) | constraints exercised by tests on SQLite |
| M1.4 | Migration + model: `pipeline_runs` table (05 TODO-6) + `services/pipeline.py` start/finalize helpers + lock-file mutex (BP §5) | overlapping run refused in a test; run row written before work, finalized after |
| M1.5 | Migration + model: `audit_events` (05 TODO-20) + `services/audit.py` single writer with required common fields (09 §2); refuse blank actor | unit test: event without actor raises; append-only convention documented in module docstring |
| M1.6 | Implement the registered-source gate + write-once raw file store in `services/ingestion.py` (BP §6 skeleton: gate, hash, artifact idempotency, `data/raw/` layout) | unregistered/unapproved/revoked source raises before any fetch; duplicate artifact run finalizes `unchanged` |
| M1.7 | Migration: add `source_record_locator` + `last_seen_document_id` to the four fact tables (05 TODO-3) | columns present; locator format documented |
| M1.8 | Fetcher registry + `sample_fixture` fetcher: `data/sample/*.csv` through the real gated path into `exclusion_records`, `vendors` (raw), `contract_awards` (raw) with lineage columns | integration test: `ingest --source sample_fixture` yields rows each resolving to file + `csv:row=N`; rerun is a no-op |
| M1.9 | `app/cli.py` (`ingest`, `pipeline` stub) + Makefile targets `ingest`, `pipeline`; emit `ingestion_run` audit events from the service layer | `make ingest SOURCE=sample_fixture` works from a clean checkout after `make setup` |
| M1.10 | **[OPERATOR]** Complete + sign off registry entries (docs/registry/) for SAM.gov Exclusions and USAspending awards, per `docs/data-source-inventory-template.md` and inventory #2/#1; create any needed free SAM.gov account | committed registry entries with approval noted; `DataSource` rows seeded with `approved_at` |
| M1.11 | `sam_exclusions.py` fetcher: pin `EXPECTED_HEADERS` from the first real pull, parse → normalized `exclusion_records` with snapshot semantics (BP §6); politeness config from the registry entry | blocked by M1.10; live pull stores artifact + rows; header drift raises `UnexpectedSchemaError` in a test with a mutated fixture |

**Acceptance criteria (milestone):** fresh clone → `make setup` →
`make db-migrate` → `make ingest SOURCE=sample_fixture` → rows queryable with
full lineage (fact row → document → file → sha256); every run has a
`pipeline_runs` row and an `ingestion_run` audit event; re-ingestion
idempotent; CI green.

---

## M2 — Entity model + normalization

**Goal:** clean entities with conservative resolution: exact-key merges only,
fuzzy candidates become reviewable edges, never silent merges.

**Depends on:** M1 (migrations chain, ingest path).

| ID | Task (one /goal) | Done when |
|---|---|---|
| M2.1 | Migrations: vendor extensions (`cage_code`, `legacy_duns`, `registration_date`, partial unique on `uei`), address `country_code` + partial unique, agency `canonical_code` partial unique (05 TODO-7, TODO-8, TODO-10) | constraints tested on SQLite |
| M2.2 | Vendor/address upsert service: sample vendors CSV → `vendors` + `addresses` with `normalized_name`/`normalized` populated via existing `services/normalization.py` | raw values preserved alongside normalized; upsert keyed on natural keys |
| M2.3 | Expand normalization golden tests: suffix table edge cases, unicode/whitespace, UEI cleaning (`clean_uei`) with malformed inputs → `None` | golden file of input→output pairs; missing stays missing, never guessed |
| M2.4 | Entity resolution v0 in `services/entity_resolution.py`: exact UEI merge; `normalized_name`+postal merge; anything fuzzier emits `RelationshipEdge(relation="possible_same_entity")` with provenance (module docstring contract already says this) | test: two fictional name-variant vendors produce an edge, not a merge |
| M2.5 | Migration: `relationship_edges` constraints + `derived_by_run_id` (05 TODO-11); ER runs record their `pipeline_run_id` | rebuildable: deleting derived edges + rerunning ER reproduces them |
| M2.6 | (parallel) USAspending reference-data ingest (inventory #11: agency/NAICS/PSC codes) via the gated path | reference tables populated from a stored artifact; used by agency canonicalization |
| M2.7 | `usaspending_awards.py` fetcher — **spike first**: one recorded exploratory pull to pin field spellings + award natural-key scope (05 TODO-12 gate), notes committed to the registry entry; then ingest to `contract_awards` | blocked by M1.10; spike notes committed before ingest code; awards land with lineage; TODO-12 unique added only if key scope verified, else deferred with docstring note |
| M2.8 | Migrations: `contract_awards` competition/NAICS/PSC columns, `exclusion_records` extensions (`normalized_name`, `classification`, `excluding_agency`) (05 TODO-13, TODO-16) | columns populated for sample + any real pulls |

**Acceptance criteria:** entity queries return canonicalized vendors linked
to addresses; no automated fuzzy merge exists anywhere; USAspending awards
(or, if M1.10 stalls, sample awards only — milestone still closes on
fixtures) resolve to raw artifacts; ER is deterministic and rerunnable.

---

## M3 — First detectors (engine + two end-to-end)

**Goal:** ROADMAP Phase 2 exactly: `debarred_vendor_match` and
`duplicate_payment` spec → engine → evidence-gated `RiskSignal` rows, via a
generic executor with no per-detector hardcoding.

**Depends on:** M2 (entities + facts populated, at least from fixtures).

| ID | Task (one /goal) | Done when |
|---|---|---|
| M3.1 | Migration: `risk_signals` extensions (`signal_key` unique, `severity_inputs`, `confidence_inputs`, `false_positive_modes`, `pipeline_run_id`, CHECKs) + `evidence_items` tightening (05 TODO-17, TODO-18) | migrations apply; model tests updated |
| M3.2 | Field registry (`detector_engine/fields.py`): spec refs like `vendor.uei` → (model, column); unresolvable ref = refusal error | contract test: every `required_fields` entry in the two Phase-2 specs resolves |
| M3.3 | Spec v0.2 for `debarred_vendor_match` + `duplicate_payment`: add machine-readable `execution:` blocks (BP §7); extend `test_detector_contracts.py` (strategy registered, referenced fields declared, version-hash guard) | prose `logic` unchanged; human review of prose↔execution equivalence noted in PR/commit message |
| M3.4 | Primitive `window_match` with match-quality labels (uei_exact > name_plus_location) + deterministic ordering | unit-tested against in-window / out-of-window / name-collision fixture cases |
| M3.5 | Primitive `duplicate_group` (group keys, invoice match quality, date proximity) | unit-tested incl. the recurring-charge FP fixture staying below threshold |
| M3.6 | Scoring functions (`detector_engine/scoring.py`) from declared `severity_inputs`/`confidence_inputs` per 06; encode "missing data lowers, never raises" | 06's worked examples 1–4 pass as literal unit tests |
| M3.7 | Evidence builder + engine core: candidates → quoted `fields_relied_on` → `require_evidence` gate → `signal_key` upsert → `detector_run` audit event (BP §7 flow) | stripped-evidence candidate is suppressed AND counted in the audit payload |
| M3.8 | `detect` CLI + `make detect`; `make pipeline` = ingest → detect sequence with the M1.4 mutex | one command runs the full chain on fixtures |
| M3.9 | Integration test: full pipeline on `data/sample/` asserts the expected fictional signals (Sample Paving Co uei_exact exclusion match; a seeded duplicate-payment pair after extending sample data with a payments CSV) and zero others; rerun creates zero new rows | test is the reproducibility contract; sample payments CSV added, clearly fictional |
| M3.10 | Lead assembly v0 (`services/leads.py`): bundle open signals by subject into `CaseLead` + `case_lead_signals` join (05 TODO-19), triage score per 06 combination rule | lead's "why this score" terms stored/reproducible with a calculator, per 06 |

**Acceptance criteria:** `make pipeline` on fixtures produces spec-versioned,
evidence-linked signals and scored leads; detector reruns are idempotent;
editing a spec without a version bump refuses to run; no detector-specific
branch exists in `engine.py`.

---

## M4 — Investigator dashboard (API + UI on real rows)

**Goal:** the five existing pages plus detail views run on DB data with the
08-product-ux rendering rules; review actions work end to end.

**Depends on:** M3 (signals/leads exist). UI tasks parallelize with API tasks
once their endpoint lands.

| ID | Task (one /goal) | Done when |
|---|---|---|
| M4.1 | Pagination envelope (`schemas/common.py`) + convert `sources`/`entities` routers to DB-backed paginated queries (BP §4) | placeholder lists deleted; API tests for envelope, limit cap, filters |
| M4.2 | `risk-signals` list filters/sort + `GET /risk-signals/{id}` with joined evidence + spec metadata (hypothesis, FP modes, validation approach) | detail response carries FP modes verbatim from the spec version that produced the signal |
| M4.3 | `GET /cases`, `GET /cases/{id}` (join table, action history, score terms) + `GET /runs` + `GET /stats/overview` with denominators | stats response shows flagged/total pairs (base-rate honesty) |
| M4.4 | `services/review.py` state machine (09 §4) + `POST /cases/{id}/actions`; widen CORS to GET+POST in the same commit; `lead_state_change`/`disposition` audit events in-transaction | API tests: legal transitions, 409 on illegal with allowed-list, 422 on dismiss without `reason_code` |
| M4.5 | `test_language.py`: prohibited-language gate over API responses and spec text (BP §8.5) | runs in CI; seeded violation fails |
| M4.6 | (parallel) Frontend: shared API client + pagination hooks; wire Sources + Entities pages to real endpoints | placeholder JSX data removed |
| M4.7 | (parallel) Frontend: Risk-signals list + signal detail page (evidence links, confidence/severity shown separately, FP modes visible per 08 §4.2) | disclaimer + FP modes render on every signal view |
| M4.8 | (parallel) Frontend: Case queue + case detail with disposition form (structured reasons per 08 §6) driving `POST /actions` | full review round-trip from the browser on fixture data |
| M4.9 | Ops panel slice on the dashboard page: last pipeline runs + failures from `GET /runs` | failed fixture run visibly surfaced |

**Acceptance criteria:** a reviewer can go list → signal detail → evidence →
case → disposition entirely on real (fictional-fixture) rows; every rendered
signal shows severity and confidence separately, its FP modes, and its
disclaimer; all writes flow through the state machine and are audited.

---

## M5 — Evidence packets (export with chain of custody)

**Goal:** ROADMAP Phase 3 export: a case packet per `EVIDENCE_STANDARD.md`
and `docs/case-packet-template.md`, plus evidence integrity verification.

**Depends on:** M4 (case detail + actions).

| ID | Task (one /goal) | Done when |
|---|---|---|
| M5.1 | `services/packets.py`: render lead → markdown from `docs/case-packet-template.md` (hypothesis, all evidence items with locators + sha256, innocent explanations considered, uncertainty language) | packet for the fixture lead contains every linked evidence item and zero prohibited terms (language gate covers packet output) |
| M5.2 | `POST /cases/{id}/packet`: write to `DATA_EXPORT_DIR`, content-hash, `export` audit event with human-stated destination (09 §2) | export event carries packet sha256 + included object ids |
| M5.3 | `GET /evidence/{id}/resolve`: re-hash stored artifact vs recorded sha256, return chain + `intact` flag; mismatch surfaces as a custody incident (BP §4) | tampered-fixture test returns `intact: false` and the packet endpoint refuses that lead |
| M5.4 | Innocent-explanations enforcement: `confirm_worthy` transition requires the considered-explanations field (09 §4 table); packet refuses leads missing it | API test for the 422 path |
| M5.5 | (parallel) Frontend export view (08 §4.5): preview, destination statement input, download | round-trip in browser on fixture lead |

**Acceptance criteria:** an escalated fixture lead yields a packet whose
every claim resolves to hashed source bytes; packets are impossible for
leads with revoked-source or integrity-failed evidence; all exports audited.

---

## M6 — Validation + governance hardening

**Goal:** prove the reproducibility/two-dialect/feedback claims instead of
asserting them; close the CI and control gaps (ROADMAP Phase 5 slice +
09 §10 checklist items in engineering scope).

**Depends on:** M3 (determinism target exists); most tasks parallelize.

| ID | Task (one /goal) | Done when |
|---|---|---|
| M6.1 | `rebuild` CLI (wipe L1–L3, reprocess stored artifacts, rerun detectors; L4 untouched; review state preserved via `signal_key`) + `make rebuild` | integration test: rebuild preserves a disposed fixture lead's state |
| M6.2 | Determinism test: two rebuilds ⇒ identical L1–L3 content modulo surrogate ids/run metadata (03 §7.1.5); wire into CI | flaky-ordering bugs (unordered iteration tie-breaks) shaken out |
| M6.3 | CI: add gitleaks secrets-scan job (verify current action name/version first) + `backend-postgres` job with `postgres:16` service and `psycopg` (BP §8.7) | both jobs required-green; upsert/partial-index behavior proven on both dialects |
| M6.4 | Source-revocation flow: `revoked_at` set ⇒ ingestion refuses at the gate; dependent signals flagged `source_revoked` via evidence→document→source join; flagged leads blocked from `confirm_worthy` (09 §4 hard rule) | end-to-end test with a fixture source revoked mid-scenario |
| M6.5 | Dismissal-feedback report: aggregate `reason_code`s per detector into a threshold-tuning summary (DETECTION_PRINCIPLES #8) exposed at `GET /stats/dismissals` and in the dashboard | dismissing fixture leads changes the report; tuning still ships only as new spec versions, never data edits |
| M6.6 | Minimal API auth: static bearer token (`API_AUTH_TOKEN`) required on all non-`/health` routes when set; localhost-only default documented | tests for 401/200 paths; full RBAC per 09 §1 remains Phase 5+, recorded as such |
| M6.7 | Audit hardening: Postgres append-only grants for `audit_events` (09 §2), documented in migration; optional `prev_event_hash` chain behind a config flag | attempted UPDATE fails under the PG test job |
| M6.8 | Calibration exercise scaffolding: sampled-signal review sheet (fixture-driven) comparing reviewer judgments to confidence bands per 06 anti-gaming section | operator has a repeatable `make` target producing the sample sheet |
| M6.9 | **[OPERATOR]** Review the 09 §10 control-to-enforcement map against implemented state; decide deployment target (ROADMAP Phase 5) | decisions recorded in `docs/` per GOVERNANCE change control |

**Acceptance criteria:** CI proves determinism, both dialects, and no
leaked secrets on every PR; revoked sources demonstrably poison-pill
dependent leads; the reviewer-feedback loop is visible data; remaining
Phase-5 items (full RBAC, secret manager, deployment) are explicitly listed
as not-done rather than silently pending.

---

## Explicitly out of backlog scope

Orchestrators, dbt, graph DB, object storage (all named seams in
`03-architecture-v1.md` §9 with revisit triggers); detectors 3–10 of the
catalog (each lands post-M6 as: spec execution block → primitive if new →
fixtures → integration test — the M3 pattern); any LLM-assisted triage
(DETECTION_PRINCIPLES #1: ordering assistance only, and not in the
prototype); anything on the DO-NOT-INGEST list in `01-data-source-inventory.md`.
