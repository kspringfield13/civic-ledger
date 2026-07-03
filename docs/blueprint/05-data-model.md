# Blueprint 05 — Data Model v1 (Deliverable F)

Status: DESIGN. Starts from the existing SQLAlchemy models in
`backend/app/models/*.py` and extends them. **Divergences from current code
are never silently redefined** — each is listed as an explicit migration TODO
(§6) and marked `[TODO-n]` inline. Canonical schema authority is the
SQLAlchemy models + Alembic migrations (ROADMAP Phase 1); the DDL in §5 is a
reference rendering, not a competing source of truth.

Companion docs: `03-architecture-v1.md` (layers, lineage, idempotency),
`09-governance-and-safety-controls.md` §2 (audit events),
`01-data-source-inventory.md` (which real-world source feeds what — all field
mappings there are "pin on first pull").

Language rule applies to schema too: columns, enums, and comments say
*signal*, *lead*, *exclusion record*, *risk* — never accusation terms.

---

## 1. Conventions

- Surrogate `id INTEGER` PK on every table (matches current code). Natural
  business keys are enforced as UNIQUE constraints/indexes — they are the
  dedup keys that make re-ingestion idempotent (`03-…` §4.3).
- Money is `NUMERIC(14,2)`; Python side must map to `Decimal`, not `float`
  `[TODO-1]`.
- Timestamps are UTC. Current models use naive `datetime.utcnow` defaults;
  move to timezone-aware UTC `[TODO-2]`.
- `JSON` columns are `JSONB` on Postgres, `TEXT` holding JSON on SQLite
  (SQLAlchemy `JSON` type handles both).
- Polymorphic references (`subject_type`/`subject_id`, edge endpoints) carry
  `CHECK` constraints on the type value; they cannot have real FKs.
- Every layer-1 fact row carries provenance: `source_document_id` (exists) +
  `source_record_locator` (new, `[TODO-3]`) — see `03-…` §4.1.

Layer map (tables by layer):

```
L0 provenance : data_sources, source_documents, pipeline_runs
L1 facts      : contract_awards, grant_awards, payments, exclusion_records
L2 entities   : agencies, vendors, person_officers, addresses, relationship_edges
L3 risk       : risk_signals, evidence_items
L4 review     : case_leads, case_lead_signals, review_actions
cross-cutting : audit_events
```

---

## 2. L0 — Provenance

### 2.1 `data_sources` (exists)

Purpose: one row per registered, operator-approved source
(`DATA_SOURCE_POLICY.md`). The ingestion gate refuses any source whose
`approved_at` is null or `revoked_at` is set.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| name | varchar(200) UNIQUE | must match fetcher `SOURCE_NAME` exactly |
| slug | varchar(100) UNIQUE | `[TODO-4]` new: filesystem-safe key for `data/raw/<slug>/` |
| tier | int | 1/2/3 per policy |
| url | varchar(500) NULL | |
| license | varchar(200) NULL | |
| access_basis | varchar(100) | `public` \| `open_license` \| `operator_authorized` |
| terms_notes | text NULL | rate limits, ToU excerpt, account-holder note |
| approved_at | timestamp NULL | operator sign-off; NULL = not ingestible |
| revoked_at | timestamp NULL | `[TODO-4]` new: supports `source_revoked` flow |
| registry_commit | varchar(64) NULL | `[TODO-4]` new: git SHA of the approved inventory entry |

Populated by: operator, via the registry workflow. Never by fetchers.

### 2.2 `source_documents` (exists; tightened)

Purpose: one retrieved artifact (file, API response batch, upload) — the
chain-of-custody anchor (`EVIDENCE_STANDARD.md`).

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| data_source_id | FK → data_sources | |
| locator | varchar(1000) | URL / API request descriptor / `upload:<origin>` |
| sha256 | char(64) **NOT NULL** | currently nullable `[TODO-5]` — a document without a hash breaks custody; forbid |
| storage_path | varchar(500) NULL | `[TODO-5]` new: relative path under `data/raw/`; NULL only if raw deleted post-normalization per retention policy (provenance pointer must then allow re-retrieval) |
| size_bytes | bigint NULL | `[TODO-5]` new |
| content_type | varchar(100) NULL | `[TODO-5]` new (`text/csv`, `application/json`, …) |
| retrieved_at | timestamp | |
| retrieval_method | varchar(100) | `api` \| `bulk_download` \| `upload` |

Dedup key: `UNIQUE (data_source_id, sha256, locator)` `[TODO-5]` — identical
bytes from the same place are one document; identical bytes from a different
locator are a distinct provenance fact (`03-…` §4.2).

Populated by: `services/ingestion.py` only.

### 2.3 `pipeline_runs` (new `[TODO-6]`)

Purpose: operational lineage + reproducibility record for every ingest,
transform/rebuild, and detector execution (`03-…` §7.1). Not the audit log
(that is `audit_events`); audit events reference runs in their payload.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| kind | varchar(20) | `ingest` \| `transform` \| `detect` (CHECK) |
| data_source_id | FK NULL | set for ingest runs |
| code_git_sha | char(40) | repo commit the run executed |
| params | JSON | CLI/config parameters, detector list, date bounds |
| input_document_ids | JSON | source_document ids read (detector/transform runs) |
| started_at / finished_at | timestamp / NULL | |
| outcome | varchar(20) | `running` \| `ok` \| `unchanged` \| `partial` \| `failed` (CHECK) |
| error | text NULL | |

Dedup: none — every execution is a row. The `running` row doubles as the
overlap mutex (`03-…` §5).

---

## 3. L1 — Facts, L2 — Entities

### 3.1 `agencies` (exists)

Purpose: awarding/funding/paying government bodies.

Fields today: `id`, `name` (indexed), `canonical_code` (nullable). Add:
`UNIQUE(canonical_code)` where not null (partial index) and
`parent_agency_id FK NULL` for sub-agency rollups `[TODO-7]`.

Dedup key: `canonical_code` when present (federal agency/sub-agency codes from
the source), else normalized name — normalization rules live in
`services/normalization.py`, not the schema.

Populated by: USAspending award records (awarding/funding agency fields);
state/local checkbook agency columns; sample data in dev.

### 3.2 `vendors` (exists; extended)

Purpose: recipient organizations (and sole proprietors as they appear in the
public spending record — no enrichment beyond the record,
`LEGAL_AND_ETHICAL_BOUNDARIES.md`).

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| name | varchar(300) idx | as first seen |
| normalized_name | varchar(300) idx | via `normalize_vendor_name` |
| uei | varchar(12) | `UNIQUE` partial (WHERE uei IS NOT NULL) `[TODO-8]` |
| cage_code | varchar(10) NULL idx | `[TODO-8]` new; from SAM entity data (verify format on first pull) |
| legacy_duns | varchar(13) NULL idx | `[TODO-8]` new; pre-2022 records key on DUNS — needed for the UEI/DUNS crosswalk noted in `01-…` |
| primary_address_id | FK → addresses NULL | |
| registration_date / registration_expiry | date NULL | `[TODO-8]` new; from SAM entity extract; feeds "newly registered vendor" style detectors |
| first_seen_document_id | FK → source_documents NULL | `[TODO-8]` new: entity rows currently have **no provenance**; minimum viable fix. Full mention/alias tracking is specified in blueprint 04 (entity resolution) — this column is not a substitute for it |

Dedup key: `uei` when present. Without UEI, automated merge only on
`(normalized_name, postal_code)` exact match per
`services/entity_resolution.py`; anything fuzzier becomes a
`relationship_edges` row `possible_same_entity` for human review — never an
automatic merge.

Populated by: SAM entity management public extract (master data),
USAspending recipient fields, exclusion records (name-only vendors), state
checkbooks.

### 3.3 `person_officers` (exists; extended)

Purpose: named individuals **in official/registered capacities only**
(contracting officers, registered agents, listed principals/POCs). By policy
this table stores nothing about a person beyond what the public record states
in that capacity: no personal addresses, no birthdates, no enrichment fields —
and the schema deliberately has nowhere to put them.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| name | varchar(300) | as recorded |
| normalized_name | varchar(300) idx | `[TODO-9]` new; needed for VEND-4-style rotating-principal matching, same normalization caveats as vendors |
| role | varchar(100) | `registered_agent` \| `principal` \| `poc` \| `contracting_officer` \| … |
| vendor_id | FK NULL | capacity anchor |
| agency_id | FK NULL | capacity anchor |
| capacity_start / capacity_end | date NULL | `[TODO-9]` new; when the record says the capacity held (registry filings) |
| source_document_id | FK → source_documents NULL→NOT NULL later | `[TODO-9]` new: **currently missing entirely** — an officer row with no provenance violates the evidence standard; backfill then require |

Dedup key: `(normalized_name, role, vendor_id, agency_id,
source_document_id)` — deliberately narrow. Two same-named officers at
different vendors stay separate rows; cross-record identity is an
entity-resolution *hypothesis* expressed as a `relationship_edges`
`possible_same_person` edge for human confirmation, never a merged row.

Populated by: SAM entity public extract (POCs), state corporate registries
(officers/agents), award records naming contracting officers where public.

### 3.4 `addresses` (exists)

Fields today: `id`, `raw`, `normalized` (idx), `city`, `region`,
`postal_code`. Add `country_code varchar(2) NULL` and dedup
`UNIQUE(normalized, postal_code)` where normalized is not null `[TODO-10]`.

Purpose: shared-address clustering (`shared_address_cluster.yml`, NET-1).
Populated by: vendor registrations, exclusion records, award recipient
addresses. Note: registered-agent and virtual-office addresses legitimately
host many entities — that FP mode belongs to the detector spec, but the model
supports it by keeping address *type* discoverable via the edge relation
(`registered_at`, `mailing_address_of`, …) rather than collapsing all
address links to one meaning.

### 3.5 `relationship_edges` (exists; constrained)

Purpose: generic typed graph edges — both *recorded* facts
(`officer_of`, `registered_at`, `awarded_by`) and *derived* hypotheses
(`possible_same_entity`, `shared_address`).

Fields today: `src_type`, `src_id`, `dst_type`, `dst_id`, `relation` (idx),
`weight`, `source_document_id` (nullable FK). Add `[TODO-11]`:

- `CHECK (src_type IN ('vendor','agency','person_officer','address'))`, same
  for `dst_type`;
- `derived_by_run_id FK → pipeline_runs NULL` — derived edges cite the run
  (and its code SHA) that produced them; recorded edges cite
  `source_document_id`. `CHECK (source_document_id IS NOT NULL OR
  derived_by_run_id IS NOT NULL)`: every edge has provenance of one kind;
- dedup `UNIQUE (src_type, src_id, dst_type, dst_id, relation,
  source_document_id)` so re-ingestion doesn't multiply edges.

Populated by: registries/extracts (recorded) and
`services/entity_resolution.py` (derived).

### 3.6 `contract_awards` (exists; extended)

Purpose: prime contract awards — the main transaction universe.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| award_key | varchar(100) | rename intent of current `award_id` `[TODO-12]`: the *source's* award identifier (PIID for federal). Keep column name `award_id` in code until migration; semantics documented here |
| agency_id / vendor_id | FK | |
| description | varchar(1000) NULL | free text; often uninformative (known quality issue) |
| amount | numeric(14,2) | obligated amount; verify exact semantics per source (obligated vs potential value differ in USAspending — pin on first pull) |
| award_date | date | |
| award_type | varchar(50) NULL | `[TODO-13]` new |
| naics_code | varchar(6) NULL idx | `[TODO-13]` new; needed by vendor-concentration and spec-tailoring detectors |
| psc_code | varchar(4) NULL | `[TODO-13]` new (federal); verify width |
| competition_extent | varchar(50) NULL | `[TODO-13]` new; sole-source signals (PROC-4). Exact source field name must be pinned — do not guess |
| pop_start / pop_end | date NULL | `[TODO-13]` new: period of performance |
| source_document_id | FK | first document that produced the row |
| source_record_locator | varchar(200) | `[TODO-3]` |
| last_seen_document_id | FK NULL | `[TODO-3]` updated on re-ingestion upsert |

Dedup key: `UNIQUE (agency_id, award_key)` `[TODO-12]`. Confidence
**moderate** that PIID is unique within an awarding agency; federal award IDs
have known edge cases (IDVs, modifications). Verify against the USAspending
data dictionary before pinning; if modifications must be distinct rows, the
key grows a modification number — decide at ingestion PR time, record in the
registry entry.

Populated by: USAspending bulk/API (federal); state procurement portals.

### 3.7 `grant_awards` (exists; extended)

Same shape and lineage columns as contracts, minus contract-specific codes;
add `assistance_listing_number varchar(10) NULL` (federal program number;
verify current name/format in the USAspending dictionary — confidence
moderate) and `recipient_type varchar(50) NULL` `[TODO-14]`.
Dedup key: `UNIQUE (agency_id, award_key)` (FAIN scope — same verification
caveat as PIID). Populated by: USAspending assistance data; state grant
portals.

### 3.8 `payments` (exists; extended)

Purpose: individual disbursements — the base table for duplicate-payment and
split-invoice detectors.

Reality check (important): invoice-level federal payment data is generally
**not** public at this granularity; realistic v1 populations are state/local
"checkbook" portals and operator-provided authorized data (confidence:
moderate-high; the inventory doc carries the source-by-source detail). The
sample data in `data/sample/` covers dev.

Adds to current model `[TODO-3, TODO-15]`: `source_record_locator`,
`last_seen_document_id`, and `description varchar(500) NULL`.

Dedup key: `UNIQUE (agency_id, payment_ref, source_document_id)` — payment
reference schemes vary wildly across checkbook portals; scoping uniqueness to
the document is the honest v1 key. Tightening to
`(agency_id, payment_ref)` per source is a per-source decision once a portal's
key semantics are verified. Note: `duplicate_payment.yml` treats repeated
refs as *signal input*, so the dedup key must not silently collapse genuinely
repeated payment rows — that is why it includes the document scope.

### 3.9 `exclusion_records` (exists; extended)

Purpose: debarment/suspension records (SAM exclusions extract) — input to
`debarred_vendor_match`.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| excluded_name | varchar(300) idx | |
| normalized_name | varchar(300) idx | `[TODO-16]` new; matching runs on this |
| uei | varchar(12) NULL idx | many older/individual records lack it (dominant FP mode) |
| classification | varchar(50) NULL | `[TODO-16]` new: firm vs individual — individuals handled under official-capacity policy only |
| exclusion_type | varchar(100) NULL | |
| excluding_agency | varchar(200) NULL | `[TODO-16]` new |
| active_from / active_to | date NULL | |
| address_id | FK → addresses NULL | `[TODO-16]` new; extract includes addresses — feeds shared-address matching |
| source_document_id | FK | which daily snapshot |
| source_record_locator | varchar(200) | `[TODO-3]` |

Snapshot semantics (`03-…` §4.3): dedup key
`UNIQUE (source_document_id, source_record_locator)`; the *current* exclusion
set is defined as rows from the latest successfully ingested extract. Old
snapshots persist so signals stay resolvable. The extract may expose a stable
per-record key — if verified on first pull, add it as a cross-snapshot
identity column then, not speculatively now.

Populated by: SAM.gov exclusions extract (Tier 1).

---

## 4. L3 — Risk, L4 — Review, audit

### 4.1 `risk_signals` (exists; extended)

Purpose: one detector-produced hypothesis with computed severity and
confidence. Never persisted without evidence (`services/evidence.py` gate).

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| detector_id / detector_version | varchar idx / varchar(20) | exists |
| signal_key | char(64) | `[TODO-17]` new: deterministic fingerprint (hash of detector_id + detector_version + subject + identifying evidence facts). `UNIQUE` — makes detector re-runs and rebuilds upsert instead of duplicate, and preserves review state across `make rebuild` |
| subject_type / subject_id | varchar(50) / int | CHECK subject_type ∈ {vendor, agency, payment, contract_award, grant_award, person_officer, relationship_edge} `[TODO-17]` |
| hypothesis | text | reviewable sentence; language standard applies |
| severity / confidence | float | computed, never hand-set |
| severity_inputs / confidence_inputs | JSON | `[TODO-17]` new: `EVIDENCE_STANDARD.md` requires "the inputs that produced them" — currently unstored |
| false_positive_modes | JSON | `[TODO-17]` new: snapshot of the spec's FP modes at creation, per the standard ("inherited from the detector spec") — snapshotted so later spec edits don't rewrite what a past signal claimed |
| pipeline_run_id | FK → pipeline_runs NULL→required | `[TODO-17]` reproducibility link |
| status | varchar(30) | `open` \| `dismissed` \| `superseded` \| `source_revoked` (per 09 §4) |
| created_at | timestamp | |

Populated by: detector engine only. No human, no API route, writes this table.

### 4.2 `evidence_items` (exists; tightened)

Purpose: the signal→source-record links required by `EVIDENCE_STANDARD.md`.

Adds `[TODO-18]`: `source_record_locator varchar(200) NULL` (points inside the
document, same scheme as facts) and a documented JSON shape for
`fields_relied_on` (stays `TEXT`/JSON): a list of
`{"field": "...", "value": "<quoted verbatim>"}` objects — quoted, not
paraphrased. Locator, retrieval timestamp, and method resolve via the
`source_documents` join and must be embedded in every API serialization
(09 §3); they are not duplicated here.

Dedup: `UNIQUE (risk_signal_id, source_document_id, source_record_locator)`.

### 4.3 `case_leads` (exists) and `case_lead_signals` (new)

`case_leads` today: `title`, `summary`, `status` (default `new`), `assignee`,
`created_at`. Status values follow the 09 §4 state machine
(`new/triaged/in_review/confirm_worthy/dismissed/needs_more_data`); add the
CHECK once Phase 3 lands `[TODO-19]`.

**Gap in current code:** nothing links a lead to its signals — a lead is
currently an orphan bundle, which breaks the evidence chain at the exact
layer humans act on. Add `case_lead_signals` `[TODO-19]`:

| Field | Type | Notes |
|---|---|---|
| case_lead_id | FK → case_leads | composite PK |
| risk_signal_id | FK → risk_signals | composite PK |
| added_at | timestamp | |
| added_by | varchar(100) | `system:lead_assembly` or a reviewer id |

A lead with zero signal links must not be creatable (service-layer rule, same
spirit as the evidence gate).

### 4.4 `review_actions` (exists)

Fields today are adequate for Phase 3 (`case_lead_id`, `actor`, `action`,
`reason_code`, `note`, `at`). Two notes, no schema change now: `action`
values must be the transition names from 09 §4; `reason_code` for dismissals
comes from a closed vocabulary (defined in the Phase 3 PR) so dismissals are
tunable data, not free text (`DETECTION_PRINCIPLES.md` #8).

### 4.5 `audit_events` (new `[TODO-20]`)

Exactly as specified in `09-governance-and-safety-controls.md` §2 — defined
there, rendered here once so DDL exists in one place: `id`, `event_type`
(closed enum, CHECK), `actor`, `actor_role`, `at`, `object_type`,
`object_id`, `payload JSON`, `prev_event_hash char(64) NULL` (hash chain;
optional before Postgres). Append-only: no UPDATE/DELETE, enforced by DB
permissions in Phase 5, code review until then.

---

## 5. Reference DDL

Postgres-flavored; SQLite-compatible except where flagged. Alembic migrations
generated from the SQLAlchemy models are canonical — this block is for
review, not execution. `/* PG */` marks Postgres-only syntax; on SQLite,
`GENERATED BY DEFAULT AS IDENTITY` is dropped (`INTEGER PRIMARY KEY`
autoincrements), `JSONB` becomes `TEXT`, and partial indexes work as written
(SQLite ≥ 3.8).

```sql
-- L0 ─ provenance ────────────────────────────────────────────────
CREATE TABLE data_sources (
    id              INTEGER PRIMARY KEY /* PG: GENERATED BY DEFAULT AS IDENTITY */,
    name            VARCHAR(200) NOT NULL UNIQUE,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    tier            INTEGER      NOT NULL CHECK (tier IN (1, 2, 3)),
    url             VARCHAR(500),
    license         VARCHAR(200),
    access_basis    VARCHAR(100) NOT NULL DEFAULT 'public'
                    CHECK (access_basis IN ('public','open_license','operator_authorized')),
    terms_notes     TEXT,
    approved_at     TIMESTAMP,            -- NULL = not ingestible
    revoked_at      TIMESTAMP,            -- set on source_revoked
    registry_commit VARCHAR(64)
);

CREATE TABLE source_documents (
    id                INTEGER PRIMARY KEY,
    data_source_id    INTEGER NOT NULL REFERENCES data_sources(id),
    locator           VARCHAR(1000) NOT NULL,
    sha256            CHAR(64) NOT NULL,
    storage_path      VARCHAR(500),
    size_bytes        BIGINT,
    content_type      VARCHAR(100),
    retrieved_at      TIMESTAMP NOT NULL,
    retrieval_method  VARCHAR(100) NOT NULL DEFAULT 'api',
    UNIQUE (data_source_id, sha256, locator)
);

CREATE TABLE pipeline_runs (
    id                  INTEGER PRIMARY KEY,
    kind                VARCHAR(20) NOT NULL CHECK (kind IN ('ingest','transform','detect')),
    data_source_id      INTEGER REFERENCES data_sources(id),
    code_git_sha        CHAR(40) NOT NULL,
    params              JSONB,   -- SQLite: TEXT
    input_document_ids  JSONB,
    started_at          TIMESTAMP NOT NULL,
    finished_at         TIMESTAMP,
    outcome             VARCHAR(20) NOT NULL DEFAULT 'running'
                        CHECK (outcome IN ('running','ok','unchanged','partial','failed')),
    error               TEXT
);

-- L2 ─ entities ──────────────────────────────────────────────────
CREATE TABLE agencies (
    id               INTEGER PRIMARY KEY,
    name             VARCHAR(300) NOT NULL,
    canonical_code   VARCHAR(50),
    parent_agency_id INTEGER REFERENCES agencies(id)
);
CREATE INDEX ix_agencies_name ON agencies(name);
CREATE UNIQUE INDEX ux_agencies_code ON agencies(canonical_code)
    WHERE canonical_code IS NOT NULL;      -- partial: PG + SQLite ≥3.8

CREATE TABLE addresses (
    id            INTEGER PRIMARY KEY,
    raw           VARCHAR(500) NOT NULL,
    normalized    VARCHAR(500),
    city          VARCHAR(100),
    region        VARCHAR(100),
    postal_code   VARCHAR(20),
    country_code  VARCHAR(2)
);
CREATE UNIQUE INDEX ux_addresses_norm ON addresses(normalized, postal_code)
    WHERE normalized IS NOT NULL;

CREATE TABLE vendors (
    id                       INTEGER PRIMARY KEY,
    name                     VARCHAR(300) NOT NULL,
    normalized_name          VARCHAR(300),
    uei                      VARCHAR(12),
    cage_code                VARCHAR(10),
    legacy_duns              VARCHAR(13),
    primary_address_id       INTEGER REFERENCES addresses(id),
    registration_date        DATE,
    registration_expiry      DATE,
    first_seen_document_id   INTEGER REFERENCES source_documents(id)
);
CREATE INDEX ix_vendors_normname ON vendors(normalized_name);
CREATE UNIQUE INDEX ux_vendors_uei ON vendors(uei) WHERE uei IS NOT NULL;
CREATE INDEX ix_vendors_cage ON vendors(cage_code);
CREATE INDEX ix_vendors_duns ON vendors(legacy_duns);

CREATE TABLE person_officers (
    id                  INTEGER PRIMARY KEY,
    name                VARCHAR(300) NOT NULL,   -- official/registered capacity only
    normalized_name     VARCHAR(300),
    role                VARCHAR(100) NOT NULL,
    vendor_id           INTEGER REFERENCES vendors(id),
    agency_id           INTEGER REFERENCES agencies(id),
    capacity_start      DATE,
    capacity_end        DATE,
    source_document_id  INTEGER REFERENCES source_documents(id)  -- NOT NULL after backfill
);
CREATE INDEX ix_person_officers_normname ON person_officers(normalized_name);

CREATE TABLE relationship_edges (
    id                  INTEGER PRIMARY KEY,
    src_type            VARCHAR(50) NOT NULL
        CHECK (src_type IN ('vendor','agency','person_officer','address')),
    src_id              INTEGER NOT NULL,
    dst_type            VARCHAR(50) NOT NULL
        CHECK (dst_type IN ('vendor','agency','person_officer','address')),
    dst_id              INTEGER NOT NULL,
    relation            VARCHAR(100) NOT NULL,
    weight              REAL NOT NULL DEFAULT 1.0,
    source_document_id  INTEGER REFERENCES source_documents(id),
    derived_by_run_id   INTEGER REFERENCES pipeline_runs(id),
    CHECK (source_document_id IS NOT NULL OR derived_by_run_id IS NOT NULL),
    UNIQUE (src_type, src_id, dst_type, dst_id, relation, source_document_id)
);
CREATE INDEX ix_edges_relation ON relationship_edges(relation);
CREATE INDEX ix_edges_dst ON relationship_edges(dst_type, dst_id);

-- L1 ─ facts ─────────────────────────────────────────────────────
CREATE TABLE contract_awards (
    id                     INTEGER PRIMARY KEY,
    award_key              VARCHAR(100) NOT NULL,   -- code column currently named award_id
    agency_id              INTEGER NOT NULL REFERENCES agencies(id),
    vendor_id              INTEGER NOT NULL REFERENCES vendors(id),
    description            VARCHAR(1000),
    amount                 NUMERIC(14,2) NOT NULL,
    award_date             DATE NOT NULL,
    award_type             VARCHAR(50),
    naics_code             VARCHAR(6),
    psc_code               VARCHAR(4),
    competition_extent     VARCHAR(50),
    pop_start              DATE,
    pop_end                DATE,
    source_document_id     INTEGER NOT NULL REFERENCES source_documents(id),
    source_record_locator  VARCHAR(200) NOT NULL,
    last_seen_document_id  INTEGER REFERENCES source_documents(id),
    UNIQUE (agency_id, award_key)          -- verify PIID scope before relying on it
);
CREATE INDEX ix_contract_awards_vendor_date ON contract_awards(vendor_id, award_date);
CREATE INDEX ix_contract_awards_naics ON contract_awards(naics_code);

CREATE TABLE grant_awards (
    id                        INTEGER PRIMARY KEY,
    award_key                 VARCHAR(100) NOT NULL,
    agency_id                 INTEGER NOT NULL REFERENCES agencies(id),
    vendor_id                 INTEGER NOT NULL REFERENCES vendors(id),
    amount                    NUMERIC(14,2) NOT NULL,
    award_date                DATE NOT NULL,
    assistance_listing_number VARCHAR(10),   -- verify current name/format
    recipient_type            VARCHAR(50),
    source_document_id        INTEGER NOT NULL REFERENCES source_documents(id),
    source_record_locator     VARCHAR(200) NOT NULL,
    last_seen_document_id     INTEGER REFERENCES source_documents(id),
    UNIQUE (agency_id, award_key)
);

CREATE TABLE payments (
    id                     INTEGER PRIMARY KEY,
    payment_ref            VARCHAR(100) NOT NULL,
    vendor_id              INTEGER NOT NULL REFERENCES vendors(id),
    agency_id              INTEGER NOT NULL REFERENCES agencies(id),
    contract_award_id      INTEGER REFERENCES contract_awards(id),
    amount                 NUMERIC(14,2) NOT NULL,
    paid_date              DATE NOT NULL,
    invoice_number         VARCHAR(100),
    description            VARCHAR(500),
    source_document_id     INTEGER NOT NULL REFERENCES source_documents(id),
    source_record_locator  VARCHAR(200) NOT NULL,
    last_seen_document_id  INTEGER REFERENCES source_documents(id),
    UNIQUE (agency_id, payment_ref, source_document_id)
);
CREATE INDEX ix_payments_vendor_amount ON payments(vendor_id, amount);  -- duplicate_payment grouping
CREATE INDEX ix_payments_invoice ON payments(invoice_number);
CREATE INDEX ix_payments_paid_date ON payments(paid_date);

CREATE TABLE exclusion_records (
    id                     INTEGER PRIMARY KEY,
    excluded_name          VARCHAR(300) NOT NULL,
    normalized_name        VARCHAR(300),
    uei                    VARCHAR(12),
    classification         VARCHAR(50),          -- firm | individual (verify vocab)
    exclusion_type         VARCHAR(100),
    excluding_agency       VARCHAR(200),
    active_from            DATE,
    active_to              DATE,
    address_id             INTEGER REFERENCES addresses(id),
    source_document_id     INTEGER NOT NULL REFERENCES source_documents(id),
    source_record_locator  VARCHAR(200) NOT NULL,
    UNIQUE (source_document_id, source_record_locator)   -- snapshot semantics
);
CREATE INDEX ix_exclusions_normname ON exclusion_records(normalized_name);
CREATE INDEX ix_exclusions_uei ON exclusion_records(uei);

-- L3 ─ risk ──────────────────────────────────────────────────────
CREATE TABLE risk_signals (
    id                    INTEGER PRIMARY KEY,
    detector_id           VARCHAR(100) NOT NULL,
    detector_version      VARCHAR(20) NOT NULL,
    signal_key            CHAR(64) NOT NULL UNIQUE,   -- deterministic fingerprint
    subject_type          VARCHAR(50) NOT NULL
        CHECK (subject_type IN ('vendor','agency','payment','contract_award',
                                'grant_award','person_officer','relationship_edge')),
    subject_id            INTEGER NOT NULL,
    hypothesis            TEXT NOT NULL,              -- signal language only, never accusation
    severity              REAL NOT NULL,
    confidence            REAL NOT NULL,
    severity_inputs       JSONB,
    confidence_inputs     JSONB,
    false_positive_modes  JSONB,                      -- snapshot from spec at creation
    pipeline_run_id       INTEGER REFERENCES pipeline_runs(id),
    status                VARCHAR(30) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','dismissed','superseded','source_revoked')),
    created_at            TIMESTAMP NOT NULL
);
CREATE INDEX ix_signals_detector ON risk_signals(detector_id);
CREATE INDEX ix_signals_subject ON risk_signals(subject_type, subject_id);

CREATE TABLE evidence_items (
    id                     INTEGER PRIMARY KEY,
    risk_signal_id         INTEGER NOT NULL REFERENCES risk_signals(id),
    source_document_id     INTEGER NOT NULL REFERENCES source_documents(id),
    source_record_locator  VARCHAR(200),
    fields_relied_on       TEXT NOT NULL,   -- JSON list of {"field","value"} quoted verbatim
    note                   TEXT,
    UNIQUE (risk_signal_id, source_document_id, source_record_locator)
);

-- L4 ─ review ────────────────────────────────────────────────────
CREATE TABLE case_leads (
    id          INTEGER PRIMARY KEY,
    title       VARCHAR(300) NOT NULL,
    summary     TEXT,
    status      VARCHAR(30) NOT NULL DEFAULT 'new'
        CHECK (status IN ('new','triaged','in_review',
                          'confirm_worthy','dismissed','needs_more_data')),
    assignee    VARCHAR(100),
    created_at  TIMESTAMP NOT NULL
);

CREATE TABLE case_lead_signals (
    case_lead_id    INTEGER NOT NULL REFERENCES case_leads(id),
    risk_signal_id  INTEGER NOT NULL REFERENCES risk_signals(id),
    added_at        TIMESTAMP NOT NULL,
    added_by        VARCHAR(100) NOT NULL,
    PRIMARY KEY (case_lead_id, risk_signal_id)
);

CREATE TABLE review_actions (
    id            INTEGER PRIMARY KEY,
    case_lead_id  INTEGER NOT NULL REFERENCES case_leads(id),
    actor         VARCHAR(100) NOT NULL,
    action        VARCHAR(50) NOT NULL,     -- transition names per 09 §4
    reason_code   VARCHAR(100),             -- closed vocabulary; required on dismiss
    note          TEXT,
    at            TIMESTAMP NOT NULL
);

-- cross-cutting ─ audit (see 09-governance-and-safety-controls.md §2)
CREATE TABLE audit_events (
    id               INTEGER PRIMARY KEY,
    event_type       VARCHAR(50) NOT NULL
        CHECK (event_type IN ('ingestion_run','detector_run','signal_view',
                              'lead_state_change','disposition','export',
                              'source_registered','source_revoked',
                              'entity_correction','retention_deletion','role_change')),
    actor            VARCHAR(100) NOT NULL,
    actor_role       VARCHAR(50)  NOT NULL,
    at               TIMESTAMP    NOT NULL,
    object_type      VARCHAR(50),
    object_id        INTEGER,
    payload          JSONB NOT NULL,
    prev_event_hash  CHAR(64)     -- hash chain; Phase 5
);
-- Append-only: REVOKE UPDATE, DELETE ON audit_events FROM app_role;  /* PG, Phase 5 */
```

---

## 6. Migration TODOs (divergences from current code, in dependency order)

Each becomes an Alembic migration + model change; none is done by this doc.

1. **[TODO-1]** Money columns: map to `Decimal` (`Mapped[Decimal]`), not
   `float`, on `contract_awards.amount`, `grant_awards.amount`,
   `payments.amount`. Current code declares `Numeric(14,2)` but types as
   `float` — silent precision risk in duplicate-amount grouping.
2. **[TODO-2]** Replace naive `datetime.utcnow` defaults with timezone-aware
   UTC (`DateTime(timezone=True)` on PG; documented-UTC convention on SQLite).
3. **[TODO-3]** Add `source_record_locator` (+ `last_seen_document_id`) to all
   four fact tables; backfill from raw files where possible, else mark rows
   `locator='unbackfilled:v0'` and exclude them from evidence use.
4. **[TODO-4]** `data_sources`: add `slug` (unique), `revoked_at`,
   `registry_commit`; CHECK on `access_basis`.
5. **[TODO-5]** `source_documents`: `sha256` NOT NULL (backfill by re-hashing
   stored files; any row whose bytes are gone and unre-retrievable is a
   custody incident to surface, not silently null); add `storage_path`,
   `size_bytes`, `content_type`; add `UNIQUE (data_source_id, sha256, locator)`.
6. **[TODO-6]** New table `pipeline_runs`.
7. **[TODO-7]** `agencies`: partial unique on `canonical_code`;
   `parent_agency_id`.
8. **[TODO-8]** `vendors`: partial unique on `uei`; add `cage_code`,
   `legacy_duns`, `registration_date/expiry`, `first_seen_document_id`.
9. **[TODO-9]** `person_officers`: add `normalized_name`,
   `capacity_start/end`, `source_document_id` (nullable → NOT NULL after
   backfill).
10. **[TODO-10]** `addresses`: `country_code`; partial unique
    `(normalized, postal_code)`.
11. **[TODO-11]** `relationship_edges`: type CHECKs, `derived_by_run_id`,
    provenance CHECK, dedup unique.
12. **[TODO-12]** `contract_awards`/`grant_awards`: rename `award_id` →
    `award_key` (avoids reading it as an FK); add `UNIQUE (agency_id,
    award_key)` **only after** key scope is verified against real data.
13. **[TODO-13]** `contract_awards`: add `award_type`, `naics_code`,
    `psc_code`, `competition_extent`, `pop_start/end`.
14. **[TODO-14]** `grant_awards`: add `assistance_listing_number`,
    `recipient_type`.
15. **[TODO-15]** `payments`: add `description`; document-scoped dedup unique.
16. **[TODO-16]** `exclusion_records`: add `normalized_name`,
    `classification`, `excluding_agency`, `address_id`; snapshot dedup unique.
17. **[TODO-17]** `risk_signals`: add `signal_key` (unique),
    `severity_inputs`, `confidence_inputs`, `false_positive_modes`,
    `pipeline_run_id`; CHECKs on `subject_type` and `status`.
18. **[TODO-18]** `evidence_items`: add `source_record_locator`; standardize
    `fields_relied_on` JSON shape; dedup unique.
19. **[TODO-19]** New table `case_lead_signals`; CHECK on `case_leads.status`
    (with Phase 3).
20. **[TODO-20]** New table `audit_events` (schema owned by 09 §2).

Sequencing note: TODO-5/6 (provenance + runs) come first — everything else
references them. TODO-12's unique constraint is the only one gated on
external verification; ship the column rename without the constraint if the
key scope is still unverified at migration time, and record that in the
migration docstring.

## 7. What this model deliberately does not contain

- **No merged-person identity.** Cross-record "same person" is only ever a
  reviewable edge hypothesis (§3.3). No table stores attributes of a private
  individual beyond the public record's official-capacity fields.
- **No verdict fields.** There is no column anywhere for "confirmed fraud" or
  equivalents; the strongest state in the system is `confirm_worthy` on a
  lead, which hands off to humans outside the system (09 §9).
- **No entity-mention/alias tables.** Deferred to blueprint 04 (entity
  resolution) to avoid two agents defining the same tables; `vendors.
  first_seen_document_id` is the interim minimum, flagged as such.
- **No partitions, no object-store columns, no graph store.** The scaling
  seams are documented in `03-architecture-v1.md` §9; building them now would
  be speculative complexity.
