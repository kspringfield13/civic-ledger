# Blueprint 10 — Build Plan for the Working Prototype (Deliverable J)

Status: BUILD PLAN. This document turns the designs in `03-architecture-v1.md`
(pipeline), `05-data-model.md` (schema + migration TODOs),
`06-risk-scoring.md` (scoring), `08-product-ux.md` (UI data needs), and
`09-governance-and-safety-controls.md` (audit/state machine) into concrete
engineering work on the **existing stack**: FastAPI, SQLAlchemy 2, Alembic,
Pydantic v2, SQLite-dev / Postgres-prod, React + Vite. It does not restate
those designs; section references point at them. Subordinate to the
governance docs; on conflict, governance wins.

Everything built here emits **risk signals and case leads for human review —
never findings or accusations.** The milestone sequencing of this plan is
`11-backlog.md`; this doc is the "how", that one is the "in what order".

---

## 1. Ground truth: what exists today (verified against the tree, 2026-07-03)

- `backend/app/models/` — all 15 tables from `docs/architecture.md` exist as
  SQLAlchemy 2 typed models (`entity.py`, `procurement.py`, `review.py`,
  `risk.py`, `source.py`). No `pipeline_runs`, `audit_events`, or
  `case_lead_signals` yet (those are `05-data-model.md` TODO-6, TODO-20,
  TODO-19).
- `backend/app/routers/` — five routers (`health`, `sources`, `entities`,
  `risk_signals`, `cases`), **all GET, all returning in-memory placeholder
  data**. No DB session is wired into any route yet.
- `backend/app/services/` — stubs with correct contracts: `ingestion.py`
  (sha256 only), `normalization.py` (tested, working), `detectors.py`
  (spec loader + `REQUIRED_SPEC_FIELDS`), `evidence.py` (gate stub),
  `entity_resolution.py` (match key only).
- `backend/alembic/` — **contains only a README. Alembic is not initialized**
  (no `alembic.ini`, `env.py`, or `versions/`). First migration task starts
  from zero.
- `main.py` CORS: `allow_methods=["GET"]`. Any POST endpoint (review
  actions, packet export) fails from the browser until this is widened —
  do it in the same commit that adds the first POST route, not before.
- CI (`.github/workflows/ci.yml`): backend ruff + pytest on 3.12, frontend
  `tsc -b`. **No secrets-scan job, no Postgres job** — both are gaps this
  plan closes (§8).
- `data/sample/` — three fictional CSVs that already encode the intended
  first signals (Sample Paving Co matches an active fictional exclusion;
  two vendors share an address; two awards sit just under 10k close in time).

---

## 2. Target repo structure — delta only

Additions (`+`) and modifications (`~`) relative to the current tree. Nothing
is moved or rewritten; existing module boundaries hold.

```
backend/
  alembic.ini                          + Alembic config (script_location=alembic)
  alembic/
    env.py                             + wired to app.database.Base + DATABASE_URL
    versions/                          + 0001_baseline .. per 05 §6 TODO order
  app/
    cli.py                             + argparse entry points (stdlib, no new dep):
                                         python -m app.cli ingest --source <slug>
                                         python -m app.cli detect [--detector <id>]
                                         python -m app.cli pipeline | rebuild
    config.py                          ~ new settings (§3)
    main.py                            ~ CORS methods GET+POST when first POST lands;
                                         include new routers
    models/
      pipeline.py                      + PipelineRun (05 §2.3)
      audit.py                         + AuditEvent (05 §4.5 / 09 §2)
      review.py                        ~ + CaseLeadSignal join table (05 §4.3)
      (others)                         ~ columns per 05 §6 TODOs, one migration each
    routers/
      sources.py, entities.py,
      risk_signals.py, cases.py        ~ placeholder → DB-backed; pagination/filters (§4)
      runs.py                          + GET /runs ops visibility
      stats.py                         + GET /stats/overview (denominators, 08 §5)
    schemas/
      common.py                        + Page[T] envelope, error shape
      evidence.py                      + EvidenceItemOut, EvidenceResolutionOut
      run.py, stats.py                 + response models
    services/
      audit.py                         + emit(event_type, actor, object, payload) —
                                         the ONLY writer of audit_events (09 §2)
      pipeline.py                      + run bookkeeping + lock/mutex (03 §5, §7.1)
      ingestion.py                     ~ registered-source gate + artifact store (03 §3.1)
      sources/                         + one fetcher module per source (03 §3.3)
        __init__.py                    + fetcher registry {SOURCE_NAME: module}
        sample_fixture.py              + data/sample/ CSVs through the REAL path
        sam_exclusions.py              + gated on operator-approved registry entry
        usaspending_awards.py          + same
      detector_engine/                 + generic executor (§7); detectors.py keeps
        __init__.py                      loader/contract duties and re-exports
        fields.py                      + field registry: "vendor.uei" → (model, column)
        primitives.py                  + window_match, duplicate_group (+ later)
        scoring.py                     + severity/confidence from declared inputs (06)
        engine.py                      + run_spec(): validate → execute → gate → upsert
      leads.py                         + lead assembly: signals → CaseLead bundles
      review.py                        + state machine transitions (09 §4), audited
      packets.py                       + case-packet markdown render (05/09, template)
  tests/
    conftest.py                        + tmp SQLite engine + fixture-loading helpers
    test_ingestion.py, test_engine.py,
    test_api_*.py, test_language.py,
    test_rebuild_determinism.py        + per §8
data/
  raw/, processed/                       (exist, git-ignored; layout per 03 §3.2)
docs/
  registry/                            + completed data-source-inventory entries,
                                         one file per source, operator-signed
frontend/                              ~ per 08-product-ux; not re-planned here
Makefile                               ~ + ingest / detect / pipeline / rebuild /
                                         db-migrate targets (one short command each,
                                         per CLAUDE.md mobile workflow)
.github/workflows/ci.yml               ~ + secrets-scan job, + Postgres matrix job (§8)
```

Deliberately **not** added: Celery/Redis/Airflow (03 §5), dbt (03 §6),
graph DB, object storage — all named seams, all deferred.

---

## 3. Environment variables (conceptual extension of `.env.example`)

Extend `.env.example` with the block below when the consuming code lands —
not before (matches the file's existing "leave blank until built" rule).
No values here are secrets; real keys are operator-held and never committed
(`make secrets-scan` gate stays).

```
# --- Pipeline & storage ---------------------------------
DATA_RAW_DIR=./data/raw            # write-once artifacts (03 §3.2)
DATA_EXPORT_DIR=./data/processed/exports
DETECTOR_SPEC_DIR=./detectors
PIPELINE_LOCK_FILE=./data/.pipeline.lock   # overlap mutex (03 §5)

# --- Ingestion etiquette (DATA_SOURCE_POLICY compliance) -
INGEST_USER_AGENT="civic-ledger/0.x (operator contact email)"  # identify honestly
HTTP_TIMEOUT_SECONDS=60
INGEST_MIN_DELAY_SECONDS=2         # per-request politeness floor; per-source
                                   # overrides live in the source registry entry

# --- Source credentials (ALL OPTIONAL, operator-held) ----
SAM_GOV_API_KEY=                   # only if API lookups used; daily extract preferred
                                   # (inventory #2: free account may be needed —
                                   # operator creates/holds it, never the agent)
# USAspending API needs no key (confidence: high; VERIFY on first pull)
USASPENDING_API_BASE_URL=https://api.usaspending.gov

# --- Run identity & future auth --------------------------
AUDIT_ACTOR=                       # e.g. operator name or agent:<session-ref>;
                                   # required by CLI runs — audit events must
                                   # never have a blank actor (09 §2)
API_AUTH_TOKEN=                    # blank until Phase-5 auth lands
```

`config.py` gains matching typed fields with the same defaults. Anything
credential-shaped stays empty in the template, and the gitleaks CI job (§8)
fails the build if a value that looks like a key is ever committed.

---

## 4. API route plan

Principles carried from 09 §3 and the existing code: every signal-bearing
response embeds its evidence references and disclaimer (the existing
`RiskSignalOut.disclaimer` pattern generalizes); no route writes audit rows
directly — routers call services, services emit events.

**Pagination convention (all list endpoints):** `?limit=` (default 50,
max 200) + `?offset=`, returning an envelope
`{"items": [...], "total": n, "limit": l, "offset": o}` — simple, stateless,
fine at v1 scale; cursor pagination is a named seam, not a v1 need.

| Route | Phase | Notes |
|---|---|---|
| `GET /health` | exists | unchanged |
| `GET /sources` | 1 | DB-backed, paginated; add `?tier=` filter |
| `GET /sources/{id}` | 1 | + document count, last `pipeline_run` outcome, revocation state |
| `GET /entities/vendors` | 1 | paginated; `?q=` matches `normalized_name` prefix; `?uei=` exact |
| `GET /entities/vendors/{id}` | 3–4 | profile per 08 §4.1: awards, signals, edges — each with evidence refs |
| `GET /entities/agencies/{id}` | 3–4 | same shape for agencies |
| `GET /risk-signals` | 2 | filters: `detector_id`, `status`, `subject_type`, `min_severity`, `min_confidence`, `created_after`; sort: `-created_at` (default), `-severity`, `-confidence` |
| `GET /risk-signals/{id}` | 2 | signal + joined `EvidenceItem`s + spec metadata (hypothesis, FP modes, validation approach — read from the YAML at the signal's `detector_version`) per 08 §4.2 |
| `GET /risk-signals/{id}/evidence` | 2 | evidence items with locator, `sha256`, quoted `fields_relied_on` |
| `GET /evidence/{id}/resolve` | 5 | integrity check: re-hash stored file, compare to recorded `sha256`, return `intact: bool` + resolution chain (03 §4.1). Mismatch ⇒ custody incident surfaced, never hidden |
| `GET /cases` | 3 | filters: `status`, `assignee`; ordered by triage score (06 combination rule) then dollar exposure |
| `GET /cases/{id}` | 3 | lead + linked signals (via `case_lead_signals`) + `ReviewAction` history + "why this score" terms (06: every term visible) |
| `POST /cases/{id}/actions` | 3 | body = existing `ReviewActionIn`; `services/review.py` enforces the 09 §4 state machine (illegal transition ⇒ 409 with allowed transitions listed; dismiss without `reason_code` ⇒ 422); emits `lead_state_change` audit event in the same transaction. **Requires widening CORS from GET-only in `main.py` — same commit.** |
| `POST /cases/{id}/packet` | 3/5 | renders `docs/case-packet-template.md` to markdown under `DATA_EXPORT_DIR`, content-hashed, `export` audit event with destination stated by the human (09 §2); response returns packet text + hash |
| `GET /runs` | 1 | paginated `pipeline_runs` for the ops panel (03 §5) |
| `GET /stats/overview` | 4 | flagged counts **with denominators** (base-rate honesty, DETECTION_PRINCIPLES #7): signals by detector / total records scanned, leads by state |

Non-goals for the prototype API: no DELETE anywhere (dispositions never
delete, 09 §4); no write endpoints for signals or facts (only detectors and
ingestion write those, via services); no auth until Phase 5 — until then the
API binds to localhost by default and the README says so.

---

## 5. Background jobs: runner + cron + job table

Per the 03 §5 decision (cron + sequential runner; no orchestrator), the
implementation is deliberately small:

- **Entry points:** `app/cli.py` (argparse — zero new dependencies) exposes
  `ingest`, `detect`, `pipeline`, `rebuild`. Make targets wrap them
  one-to-one (`make ingest SOURCE=sam_exclusions`, `make detect`,
  `make pipeline`), keeping the phone-driven workflow to single short
  commands.
- **Job table = `pipeline_runs`** (05 §2.3): every run inserts a row with
  `kind`, `params` JSON, `code_git_sha`, `started_at` **before doing work**,
  then finalizes `finished_at`, `outcome` (`ok|unchanged|partial|failed`),
  `error_text`, and the input/output `source_document_id` sets. This is the
  auditability backbone; the paired `ingestion_run`/`detector_run` audit
  events carry `pipeline_run_id` in their payload (03 §7.2).
- **Mutex:** `pipeline.py` refuses to start if `PIPELINE_LOCK_FILE` exists
  and is fresh, or if a `pipeline_runs` row of the same kind is `running`
  younger than a staleness threshold. Required for SQLite writers; still
  correct on Postgres.
- **Cron:** operator-installed (documented in `docs/environment-setup.md`),
  e.g. daily `make pipeline` = ingest registered snapshot sources → run
  detectors → assemble leads, sequentially. Failure = nonzero exit +
  `outcome="failed"` row, visible at `GET /runs`. No in-process scheduler in
  the prototype; APScheduler remains the optional single-VM convenience
  named in 03 §5, added only if the operator asks.
- **`rebuild`** wipes L1–L3, reprocesses stored raw artifacts, reruns
  detectors; L4 human data is never wiped; review state survives via
  `signal_key` matching (03 §6, §7.1.4-5).

---

## 6. Sample transformation: SAM exclusions CSV → `exclusion_records`

Pseudocode for the full ingest path; this is the template every fetcher
follows. Column names are **deliberately symbolic** — exact extract headers
must be pinned from the first real pull (inventory #2: confidence high that
the public extract exists; format/headers unverified) and committed as
`EXPECTED_HEADERS` in the fetcher before any live run.

```python
# services/sources/sam_exclusions.py
SOURCE_NAME = "SAM.gov Exclusions"          # must equal DataSource.name exactly
EXPECTED_HEADERS = [...]                    # pinned on first pull; TODO marker until then

def parse(raw: bytes):
    rows = csv_reader(raw)
    if rows.header != EXPECTED_HEADERS:
        raise UnexpectedSchemaError(diff)    # drift breaks the run, never mis-maps (03 §3.3)
    for i, rec in enumerate(rows, start=1):  # 1-based data row, header excluded
        yield f"csv:row={i}", rec            # deterministic record locator (03 §4.1)

# services/ingestion.py — the one gated entry point
def ingest(source_name, artifact=None):
    src = get_registered_source(source_name)          # raises UnregisteredSourceError
    if src.approved_at is None or src.revoked_at:     #   unless operator-approved;
        raise UnregisteredSourceError(src.name)       #   no bypass parameter exists
    run = start_pipeline_run(kind="ingest", source=src, code_git_sha=current_sha())
    try:
        raw, locator, method = artifact or fetcher_for(src).fetch()   # honest UA, politeness delay
        digest = sha256_bytes(raw)                                    # exists today
        if find_document(src.id, digest, locator):                    # artifact idempotency (03 §4.2)
            return finalize(run, "unchanged")
        path = write_raw_file(src.slug, digest, safe_name)            # write-once (03 §3.2)
        doc  = insert_source_document(src.id, locator, digest, path, method)
        with db.begin():                                              # one txn per artifact (03 §8)
            n = 0
            for rec_locator, rec in fetcher_for(src).parse(raw):
                upsert_exclusion_record(
                    excluded_name   = rec["<name col>"].strip(),
                    normalized_name = normalize_vendor_name(rec["<name col>"]),  # raw kept verbatim
                    uei             = clean_uei(rec.get("<uei col>")),  # None stays None —
                                                                        # missing ≠ suspicious
                    classification  = rec.get("<class col>"),           # firm vs individual
                    exclusion_type  = rec.get("<type col>"),
                    active_from     = parse_date_or_none(rec.get("<activation col>")),
                    active_to       = parse_date_or_none(rec.get("<termination col>")),
                    source_document_id    = doc.id,
                    source_record_locator = rec_locator,
                    # snapshot semantics: keyed (source_document_id, source_record_locator);
                    # "current set" = rows of the latest ok document; old snapshots persist
                    # so signals citing them stay resolvable forever (03 §4.3)
                )
                n += 1
            emit_audit_event("ingestion_run", actor=settings.audit_actor,
                             object=("data_source", src.id),
                             payload={"pipeline_run_id": run.id, "records": n,
                                      "sha256": digest, "terms_note": src.terms_notes})
        return finalize(run, "ok", records=n)
    except Exception as e:
        finalize(run, "failed", error=str(e)); raise
```

Notes that are policy, not style: normalization never overwrites the raw
value (both columns stored); records naming excluded *individuals* are stored
exactly as the official record states them, no enrichment
(LEGAL_AND_ETHICAL_BOUNDARIES, individuals-in-official-capacity); date parse
failures null the field and count in the run's `rejected` tally rather than
guessing.

---

## 7. Detector engine: generic YAML executor

**The honest design problem:** ROADMAP Phase 2 requires "engine reads YAML
specs generically (no per-detector hardcoding)", but the specs' `logic:`
field is prose — reviewable, not executable. Resolution: keep prose `logic`
as the reviewer-facing source of truth, and add a machine-readable
`execution:` block (spec version bump to 0.2 for the two Phase-2 detectors)
that parameterizes a small library of typed **primitives**. The engine knows
primitives, not detectors. A contract test can verify the execution block is
well-formed and consistent with `required_fields`; it **cannot** verify it
semantically matches the prose — that equivalence is a human review gate on
the spec PR (recorded here so nobody pretends the test covers it).

Two primitives cover Phase 2; more are added only when a spec needs them:

- `window_match` — join left records to right records on ordered match keys
  (each with a declared quality label), filtered to a date window
  (`debarred_vendor_match`: exclusions × awards, UEI-exact then
  name+postal, `award_date ∈ [active_from, active_to]`).
- `duplicate_group` — group rows by keys, emit intra-group pairs passing
  similarity + date-proximity predicates (`duplicate_payment`:
  `(vendor_id, amount)`, invoice exact > normalized > amount-only,
  `≤ 90 days`).

Engine flow:

```python
# services/detector_engine/engine.py
def run_spec(spec_path, pipeline_run):
    spec = load_spec(spec_path)
    validate_contract(spec, REQUIRED_SPEC_FIELDS)          # exists today
    verify_version_hash(spec_path, spec["version"])        # refuse if file content changed
                                                           # without a version bump (03 §7.1.3)
    resolve_fields(spec["required_fields"])                # field registry: "vendor.uei" →
                                                           # (Vendor, uei); unresolvable ref =
                                                           # config error, refuse to run —
                                                           # never silently skip a field
    candidates = PRIMITIVES[spec["execution"]["strategy"]](spec["execution"]["params"])
    created = suppressed = 0
    for cand in candidates:                                # deterministic ORDER BY inside
        sev  = score_severity(spec["severity_inputs"], cand)     # 06 §2 bands
        conf = score_confidence(spec["confidence_inputs"], cand) # 06 §3; missing data
                                                                 # lowers, never raises
        evidence = build_evidence(cand)    # (source_document_id, source_record_locator,
                                           #  quoted fields_relied_on) per contributing row
        try:
            require_evidence(evidence)     # existing single gate — no evidence, no signal
        except MissingEvidenceError:
            suppressed += 1; continue      # counted + audited, never silently dropped
        key = signal_key(spec, cand)       # sha256(detector_id | version | subject_type |
                                           # subject NATURAL key | sorted evidence identity
                                           # facts) — natural keys, not surrogate ids, so
                                           # rebuilds reproduce the same key (03 §7.1.4)
        upsert_signal(key, spec, cand, sev, conf, evidence,
                      hypothesis=render_hypothesis(spec, cand),   # template from spec text;
                      pipeline_run_id=pipeline_run.id)            # no free-form generation
        created += 1
    emit_audit_event("detector_run", payload={
        "detector_id": spec["id"], "detector_version": spec["version"],
        "input_bounds": input_snapshot_bounds(), "signals_created": created,
        "signals_suppressed_by_evidence_gate": suppressed})       # 09 §2
```

Signal text is assembled only from spec-approved hypothesis templates plus
record identifiers — the language standard (EVIDENCE_STANDARD) is enforced by
construction, and `test_language.py` (§8) backstops it.

---

## 8. Test strategy

Layers, cheapest first. All fixtures are the **fictional** `data/sample/`
files (extended as needed, always clearly fictional) — real data never enters
tests or CI.

1. **Unit** — pure functions, no DB: normalization golden cases (extend the
   existing three tests), `clean_uei`, match-quality ordering, severity /
   confidence scoring against 06's worked examples (the doc's four examples
   become literal test cases), `signal_key` stability.
2. **Contract** — extend `test_detector_contracts.py`: existing field checks
   stay; add — `execution.strategy` names a registered primitive; every
   field the execution block references appears in `required_fields` and
   resolves in the field registry; version-hash guard fires when a spec file
   is edited without a version bump.
3. **Integration (the money tests)** — `conftest.py` builds a temp SQLite DB,
   runs migrations, ingests `data/sample/` through the *real* gated path
   (via `sample_fixture` fetcher), runs the engine, asserts: Sample Paving
   Co's in-window award yields exactly one `debarred_vendor_match` signal
   with `match_key=uei_exact` and resolvable evidence; a signal candidate
   with its evidence stripped is suppressed and counted; re-running ingest
   is `unchanged`; re-running detect creates zero new rows (idempotency);
   unregistered source raises before any byte is fetched.
4. **API** — TestClient: pagination envelope + limit cap; filters; 404s;
   `POST /cases/{id}/actions` legal and illegal transitions (409 + allowed
   list), dismiss-without-reason 422; every signal/case response carries
   disclaimer + evidence refs (generalizes the existing disclaimer test).
5. **Language gate** — `test_language.py`: walk all API response strings,
   packet output, and spec `hypothesis` fields for prohibited terms
   (`fraudulent`, `guilty`, `criminal`, `committed` + assertion-of-intent
   phrases per EVIDENCE_STANDARD). Cheap, blunt, catches regressions the
   humans miss.
6. **Determinism** — `test_rebuild_determinism.py` (M6): `rebuild` on the
   sample set twice ⇒ identical L1–L3 content modulo surrogate ids/run
   metadata (03 §7.1.5), same `signal_key` set.
7. **CI gates** — extend `ci.yml`:
   - keep the two existing jobs (backend ruff+pytest, frontend tsc);
   - **add `secrets-scan`**: gitleaks action over full history — the local
     `make secrets-scan` habit becomes a hard gate (pin the action version;
     verify current action name/inputs at implementation time — moderate
     confidence in the exact incantation, high that gitleaks has an official
     action);
   - **add `backend-postgres`**: same pytest run against a `postgres:16`
     service container with `DATABASE_URL` set — proves the two-dialect
     claim (03 §1.4) including upsert behavior (03 §10), needs `psycopg`
     added to requirements for this job;
   - determinism job on sample data lands with M6.

---

## 9. Verify-before-build register (do not code past these)

| Item | Blocks | Confidence today |
|---|---|---|
| SAM exclusions extract: exact headers, file name, whether download needs the operator's free account | `sam_exclusions.py` live run (fixture path is unblocked) | High the extract exists; format/account details unverified (inventory #2) |
| USAspending API: no key needed, pagination shape, award natural-key scope | `usaspending_awards.py`; the TODO-12 unique constraint | High API exists & is public; field spellings unverified (inventory #1, 05 §6) |
| gitleaks GitHub Action exact name/version | CI secrets-scan job | Moderate |
| SQLite ≥3.24 upsert on CI runners | all upsert paths | High; prove in CI, not by assertion (03 §10) |

Each verification lands as a short note in the source's registry entry or the
migration docstring — facts on file, not in memory.
