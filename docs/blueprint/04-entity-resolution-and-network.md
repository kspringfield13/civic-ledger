# Blueprint 04 — Entity Resolution & Network Intelligence

Status: DRAFT design, subordinate to the repo governance docs
(`LEGAL_AND_ETHICAL_BOUNDARIES.md`, `DATA_SOURCE_POLICY.md`,
`EVIDENCE_STANDARD.md`, `DETECTION_PRINCIPLES.md`, `GOVERNANCE.md`). Where this
document conflicts with those, they win. Cross-references:
[01-data-source-inventory.md](01-data-source-inventory.md) for the sources
that feed resolution, [05-data-model.md](05-data-model.md) for the relational
model, [06-risk-scoring.md](06-risk-scoring.md) for how link confidence enters
scoring.

**Core stance:** an identity claim ("these two records are the same vendor")
is itself a hypothesis with evidence, confidence, and known failure modes —
exactly like a risk signal. We therefore apply the `EVIDENCE_STANDARD.md`
discipline to entity resolution itself: every merge and every relationship
edge carries its method, its evidence pointers, and a confidence score, and
every merge is reversible. A wrong merge is the single most damaging error
this system can make, because it silently transfers risk signals from one
real-world organization to another. Everything below is designed around
preventing and undoing that error.

Conventions: **Confidence** annotations (high / moderate / low / unknown) on
real-world claims mean *our confidence the claim about the outside world is
accurate as written*, with a note on what to verify before reliance.
Numeric confidences on methods (e.g. `0.98`) are *proposed starting values*
for the `confidence` field — they are design parameters to be tuned against
labeled samples in Phase 1, not measured error rates. Do not present them as
measured until we have measured them.

---

## 1. What entity resolution does — and does not — claim

Entity resolution (ER) links raw records from ingested sources
(`SourceDocument`-backed rows) to canonical rows in `vendors`, `agencies`,
`person_officers`, and `addresses`, and creates typed `relationship_edges`
between canonical entities.

What an ER link asserts, at most: "record A and record B refer to the same
registered legal entity, according to method M applied to fields X, Y at
confidence C." It never asserts common ownership, control, collusion, or
intent. "Vendor P and vendor Q share a registered address" is a fact about
two public filings; whether it means anything is the reviewer's question, and
the innocent explanations (Section 7) travel with the edge.

Scope limits inherited from `LEGAL_AND_ETHICAL_BOUNDARIES.md`:

- **People are resolved only within official capacities.** We link
  `PersonOfficer` rows (officers, registered agents, contracting officers as
  named in public filings) — we never attempt to resolve a filing-listed
  officer to any person outside those filings, never enrich with private
  data, and never build person-centric profiles. Person-name matching is the
  weakest rung of the ladder (Section 2) and is *always* a weak link.
- **Only registered/public identifiers.** No device IDs, no emails or phone
  numbers unless they appear in the public registration record itself
  (SAM.gov entity data includes some POC fields; whether we ingest them at
  all is an operator decision — default is no).

## 2. Canonical identifier ladder

Matching proceeds top-down. A match at a higher rung short-circuits lower
rungs. Confidence is per-rung and recorded on the merge/edge (Section 5, 8).

| Rung | Key | Proposed confidence | Auto-merge? |
|---|---|---|---|
| 1 | UEI exact match | 0.98 | Yes |
| 2 | CAGE code exact match | 0.95 | Yes |
| 3 | Exact registry number within the same registry (e.g. state SOS filing number + state) | 0.93 | Yes |
| 4 | Normalized name + normalized address, both exact after normalization | 0.75 | No — queued for review, or auto-linked as `candidate_same_entity` weak edge |
| 5 | Normalized name only | 0.40 | Never. Candidate generation / blocking key only |

Rung details and caveats:

1. **UEI (Unique Entity ID).** 12-character alphanumeric identifier issued by
   SAM.gov; since April 2022 the authoritative federal entity identifier,
   replacing DUNS. *Confidence in this description: high. Verify before
   reliance:* current SAM.gov policy on UEI persistence and whether a UEI is
   ever reissued or reassigned; whether one legal entity can hold multiple
   UEIs (under DUNS, distinct physical locations/divisions of one company had
   distinct numbers — confirm the UEI analogue, because it means rung 1
   resolves to *registration*, not necessarily to *legal entity*, and two
   UEIs may legitimately belong to one company). Not 1.0 even at rung 1:
   data-entry errors in non-SAM sources that transcribe UEIs, and the
   registration-vs-entity distinction above.
2. **CAGE code.** 5-character code assigned per facility (Defense Logistics
   Agency administers it). *Confidence: high that it exists and is
   facility-scoped; verify* current assignment/reuse rules. Slightly below
   UEI because it is facility-level and appears less consistently across our
   sources.
3. **Exact registry number in the same registry.** A state corporate filing
   number is only unique *within that state's registry*; the key is
   `(registry_id, registry_number)`, never the number alone. High confidence
   as a method; the practical risk is registry-side renumbering after
   conversions or redomestications (verify per registry when a state source
   is admitted — none are admitted yet per Blueprint 01).
4. **Normalized name + normalized address.** After the normalization of
   Section 3, an exact match on both. This is where the serious failure modes
   live (registered-agent addresses, franchises — Section 7), which is why it
   does not auto-merge in v1. Guardrails from Section 7 (address-role check,
   cluster caps) apply before even the weak link is written.
5. **Name only.** Used solely as a blocking key to generate candidate pairs
   for rung-4 evaluation or human review. A name-only match is never a merge
   and never an edge stronger than `candidate_same_entity` with
   `strength=weak`. For `PersonOfficer` this is the *only* available rung in
   most sources, which is why person links are structurally weak links.

Proposed schema note: `Vendor` today carries only `uei`. Rungs 2–3 require
adding `cage_code` and a `(registry_id, registry_number)` pair (or a
one-to-many `vendor_identifiers` table, which is the better shape since one
vendor accrues identifiers over time — recommended for
[05-data-model.md](05-data-model.md)).

## 3. Normalization rules

Normalization is deterministic, versioned (`normalizer_version` recorded on
outputs), and never destructive — the `raw` value is always retained
(`Address.raw` exists; `Vendor` should likewise keep the as-published name
alongside `normalized_name`, which the current model already does via
`name` + `normalized_name`).

### 3.1 Name normalization (vendors, agencies)

Ordered pipeline; each step is a pure function with unit tests
(`services/normalization.py` per `EVIDENCE_STANDARD.md`):

1. **Unicode normalization:** NFKC, then strip diacritics to ASCII where
   unambiguous (record that folding happened; keep the pre-fold form).
2. **Case folding:** uppercase (casefold, then upper, to handle non-ASCII
   edge cases).
3. **Punctuation & whitespace:** strip `.,'"`, collapse runs of whitespace,
   normalize `&` → `AND` (single canonical direction).
4. **Legal-suffix stripping:** remove a maintained, versioned suffix list
   (`LLC`, `L.L.C.`, `INC`, `INCORPORATED`, `CORP`, `CO`, `LTD`, `LP`,
   `LLP`, `PLLC`, `PC`, `GMBH`, `SA`, `PTY`, …) **into a separate field**
   (`legal_suffix`), not into the void. `ACME LLC` and `ACME INC` normalize
   to the same `normalized_name` but *differ* on `legal_suffix` — that
   difference is a live feature at rung 4 (same name, different suffix at
   the same address is a classic successor/sibling pattern, and also a
   classic false-merge trap). The suffix list is a reviewable data file in
   the repo, not code constants.
5. **DBA/trade-name splitting:** `X DBA Y`, `X D/B/A Y`, `X T/A Y` split into
   two name candidates, both pointing at the same raw record.
6. **Stop-token handling:** do **not** strip generic tokens (`SERVICES`,
   `GROUP`, `HOLDINGS`) in v1 — stripping them collapses too many distinct
   entities. Revisit with data.

*Confidence in this pipeline as a method: high that it is standard practice;
the suffix list itself must be built from our actual ingested data, not
assumed complete.*

### 3.2 Address standardization

Two credible open-source options; we should pick per phase:

- **usaddress** (Python, DataMade): CRF-based tagger that splits a US address
  string into labeled components. Lightweight (pip install, small model),
  US-only, tags but does not canonicalize (it won't tell you `STREET` ≡
  `ST`). *Confidence: high that the library exists and works as described;
  verify current maintenance status.*
- **libpostal** (C library with Python bindings via the `postal` package):
  multi-national parsing *and* expansion/normalization, trained on
  OpenStreetMap/OpenAddresses-scale data. Substantially better at
  canonicalization; cost is a native dependency and a large model download
  (on the order of a couple of gigabytes — *verify current size*), which
  complicates the SQLite-default, mobile-driven dev workflow in `CLAUDE.md`.
  *Confidence: high on characteristics, moderate on exact footprint.*

**Recommendation:** Phase 1 uses `usaddress` for component tagging plus our
own small, versioned canonicalization table (USPS-style suffix and
directional abbreviations: `STREET→ST`, `AVENUE→AVE`, `NORTH→N`, secondary
units `SUITE→STE`, `#→STE` heuristics) and ZIP5 extraction from ZIP+4. That
is testable, dependency-light, and adequate for exact-match rung 4. Introduce
libpostal only if measured rung-4 recall on real data is poor, and as an
optional service (Docker) rather than a hard dependency. If USPS address
verification APIs are ever considered, they are a new data source requiring a
`DATA_SOURCE_POLICY.md` registry entry and operator sign-off first.

Normalized address key: `(normalized_line1, city_upper, region, zip5)`.
Secondary-unit designators (suite/apt) are kept as a separate component —
matching *with* unit and *without* unit are different-strength facts (a
shared building is much weaker than a shared suite), and Section 7's
registered-agent guardrail needs the building-level key.

### 3.3 Person-name normalization (`PersonOfficer`)

Case/unicode folding, punctuation stripping, suffix isolation
(`JR/SR/II/III`), and first/middle/last splitting only. **No nickname
expansion, no phonetic matching (Soundex/metaphone) in v1** — person
identities are the highest-harm surface and the lowest-quality identifiers we
have. Person matches never exceed weak-link status regardless of string
similarity (Section 5).

## 4. Match scoring: deterministic v1, probabilistic later

### 4.1 Why v1 is deterministic

`DETECTION_PRINCIPLES.md` #1 requires transparent, reviewer-readable rules,
and the reasons apply with more force to ER than to detectors:

1. **Every downstream signal inherits ER errors.** A probabilistic matcher's
   errors are diffuse and hard to audit; a deterministic ladder's errors are
   enumerable ("this merged because both had UEI ABC123DEF456") and every
   merge can cite the exact fields per `EVIDENCE_STANDARD.md`.
2. **We have no labeled data yet.** Fellegi–Sunter m/u probabilities or
   feature weights estimated without labels (e.g. via EM) are unverifiable
   at exactly the moment we can least afford silent error. Deterministic v1
   *produces* the labeled data (reviewer confirmations/rejections of rung-4
   candidates, merge-log outcomes) that a probabilistic phase needs.
3. **Reproducibility** (`DETECTION_PRINCIPLES.md` #6): same inputs + same
   ladder version → same merges. Trivially true for rules; requires model
   pinning and more machinery for learned matchers.
4. The federal-first source mix (Blueprint 01) is identifier-rich (UEI on
   both USAspending and SAM exclusions), so deterministic rungs 1–3 should
   cover the bulk of volume. *Confidence: moderate — this is an expectation
   about field-population rates that Phase 1 must measure, not assume.*

### 4.2 Deterministic v1 (Phases 1–2)

Exactly the ladder of Section 2: rungs 1–3 auto-merge; rung 4 produces
review-queue candidates and weak `candidate_same_entity` edges; rung 5 is
blocking only. All thresholds and the ladder itself live in a versioned
config, not scattered constants.

### 4.3 Probabilistic later phase (Phase 5+, gated)

When we have (a) reviewer-labeled candidate pairs from rung 4 and (b) a
measured need (recall gap on identifier-poor sources such as future
state/local checkbooks), introduce a Fellegi–Sunter-style linear model:
weighted agreement/disagreement features (name token overlap, suffix
agreement, address component agreement, ZIP agreement, identifier
presence/absence) summed to a match weight with two thresholds
(link / review / non-link). Candidate implementation: **Splink** (open-source
Fellegi–Sunter implementation from the UK Ministry of Justice, runs on
DuckDB/Spark backends). *Confidence that Splink exists and fits this shape:
high; verify current backend support and license before adoption.* A simple
hand-weighted feature sum is an acceptable intermediate step and keeps
DETECTION_PRINCIPLES transparency.

Hard gates on the probabilistic phase, whenever it lands:

- Probabilistic scores **never auto-merge**. Above-threshold pairs go to the
  review queue; only a human confirmation (or a rung 1–3 identifier hit)
  merges.
- Feature weights, thresholds, and evaluation metrics (precision/recall on a
  held-out labeled set) are committed artifacts, versioned like detector
  specs.
- Probabilistic links are stored as weak edges with `method='probabilistic'`
  and the score in `confidence` — visibly distinct from deterministic links
  everywhere they surface.

## 5. Strong vs weak links on `relationship_edge`

### 5.1 Schema

The current `RelationshipEdge` model (`backend/app/models/entity.py`) has
`src/dst type+id`, `relation`, `weight`, `source_document_id`. That is not
enough to enforce the strong/weak discipline. Proposed extension (Alembic
migration, coordinate with [05-data-model.md](05-data-model.md)):

| Column | Type | Meaning |
|---|---|---|
| `edge_type` | str, indexed | replaces/renames `relation`; controlled vocabulary below |
| `strength` | enum `strong` / `weak` | derivation class, not a score |
| `confidence` | float 0–1 | method-derived starting value (Section 2/9), tunable |
| `method` | str | e.g. `uei_exact`, `name_addr_exact_v3`, `registry_officer_listing`, `probabilistic_splink_v1` |
| `evidence_refs` | one-to-many to `EvidenceItem` (or a join table `edge_evidence`) | the specific source fields relied on, quoted — same standard as risk signals |
| `created_by_run` | FK to the resolution/ingestion run record | reproducibility + bulk rollback (Section 8) |
| `valid_from` / `valid_to` | date, nullable | filings change; edges are temporal facts |
| `superseded_by` | self-FK, nullable | edges are never hard-deleted, only superseded |

`source_document_id` stays for the single-document common case;
`evidence_refs` is authoritative. An edge with no resolvable evidence is
invalid and must not be persisted — the same `services/evidence.py` gate that
protects `RiskSignal`.

### 5.2 Edge-type vocabulary (initial, controlled)

**Strong** (directly asserted by an authoritative record, rungs 1–3 or an
explicit field in a Tier-1/Tier-2 document):

- `same_entity` — merge-grade identity (in practice realized as a merge,
  Section 8, but recorded as an edge in the merge log)
- `awarded_by` (vendor ↔ agency, via a specific `ContractAward`/`GrantAward`)
- `paid_by` (vendor ↔ agency, via `Payment`)
- `officer_of`, `registered_agent_of` (person ↔ vendor, as listed in a
  registry filing — the edge asserts *the filing says so*, nothing more)
- `registered_at` (vendor ↔ address, from the registration record itself)
- `excluded_as` (vendor ↔ `ExclusionRecord`, rung 1–3 identifier match)

**Weak** (inferred, correlational, or low-rung):

- `candidate_same_entity` (rung-4/5 or probabilistic)
- `shares_address` (derived: two vendors resolve to the same normalized
  address key — after guardrails)
- `shares_officer_name` (derived: officer-name match across vendors —
  name-only, so always weak)
- `succeeded_by_candidate` (Section 7, mergers/successors heuristic)

### 5.3 The propagation rule (non-negotiable)

**Weak links never propagate risk on their own.** Concretely, enforced in the
detector engine and scoring layer ([06-risk-scoring.md](06-risk-scoring.md)):

1. No detector may traverse a weak edge to attach a signal to an entity on
   the far side. A debarred-vendor match found via `candidate_same_entity`
   does not create a `RiskSignal` on the candidate — it creates a
   *resolution review task* ("possible identity with excluded entity —
   confirm or reject the match first").
2. Weak edges may contribute **context** displayed to a reviewer (the network
   panel shows them, visually distinct, labeled with method + confidence and
   the innocent explanations from Section 7).
3. Two or more *independent* weak edges (different methods, different source
   documents) between the same pair may trigger a detector whose subject is
   the *pair/cluster itself* (e.g. `corroborated_link_review`), producing a
   signal whose hypothesis is "these records may be related — worth
   resolving," not any FWA hypothesis. Independence is asserted by the
   detector spec and checked against `evidence_refs` overlap.
4. Strong edges propagate only what their `edge_type` semantically supports:
   `awarded_by` supports concentration/rotation analysis;
   `registered_agent_of` supports *nothing* by itself (see Section 7 —
   registered agents are a service industry).

## 6. Network analysis over the relational model (graph DB deferred)

The graph questions v1 asks are small-diameter (1–2 hops) and run in batch.
They are expressible as SQL + Python jobs over `relationship_edges` and the
spend tables, materialized into ordinary tables that detectors and the UI
read. A graph database adds an operational dependency, a second source of
truth, and a sync problem — with no v1 query that needs it. Defer until a
concrete query (3+ hop traversal, interactive subgraph exploration at scale)
is measured to be impractical; even then, an in-process
NetworkX-on-extracted-subgraph step likely covers Phase-4 needs.
*Confidence in this deferral: high for the stated v1 query set.*

Initial computed jobs (each is a versioned batch job writing a materialized
table + weak/derived edges with `created_by_run` set):

1. **Shared-address clusters** (`address_clusters`): group vendors by
   normalized building-level address key; emit clusters with size, member
   list, and address-role classification (Section 7). SQL `GROUP BY` +
   `HAVING count BETWEEN 2 AND cap`. Feeds `shares_address` weak edges and
   the taxonomy's shell-network patterns — as *context*, per Section 5.3.
2. **Repeated officers / registered agents** (`officer_overlap`): pairs of
   vendors sharing normalized officer names (weak) or, where a registry
   provides a stable officer identifier, that identifier (stronger; verify
   per registry — most US state registries do **not** expose stable person
   IDs; *confidence: moderate*). Registered-agent overlap is computed but
   flagged non-signal by default (Section 7).
3. **Rotating winners within a buying agency** (`agency_vendor_rotation`):
   for each agency (or sub-agency/office code once ingested), the time
   series of award winners in a NAICS/PSC band; features like "same small
   set of vendors alternating wins" computed with window functions. This
   consumes only **strong** `awarded_by` facts, so it can feed a detector
   directly — the detector spec still must list innocent explanations
   (small qualified-vendor pools, IDIQ rotation being *by design*, regional
   monopolies).
4. **Award/payment concentration** (`vendor_agency_concentration`):
   Herfindahl-style shares per agency-NAICS cell; denominator honesty per
   `DETECTION_PRINCIPLES.md` #7 (always store the population size next to
   the flagged share).

All derived tables record `run_id`, input snapshot hashes, and
`normalizer_version`/ladder version so results are reproducible.

## 7. Known failure modes and guardrails

Each failure mode below is also a mandatory "innocent explanation" line item
wherever the corresponding edge or cluster surfaces in the UI or a case
packet.

| Failure mode | What goes wrong | Guardrails |
|---|---|---|
| **Common names** | `SMITH CONSTRUCTION` exists independently in 40 states; name-only match merges strangers | Rung 5 never merges or edges beyond candidates; rung 4 requires full address agreement; jurisdiction (state/registry) mismatch is a hard blocker for auto-anything; person names never exceed weak |
| **Registered-agent addresses** | Thousands of unrelated, legitimate companies share one agent's address (e.g. large commercial registered agents in Wilmington, DE — a single street address there serves an enormous number of entities; *confidence: moderate on any specific count — verify before citing one*) | (a) address-role classification: an address arriving via a `registered_agent_of` filing field is typed `agent_address` and **excluded from `shares_address` derivation entirely**; (b) a maintained **registered-agent address allowlist** (seeded from observed high-frequency agent addresses, reviewer-curated, versioned in-repo) suppresses cluster emission; (c) cluster-size cap (below) |
| **Virtual offices / mail drops / coworking** | Hundreds of small firms share one suite | **Cluster-size cap:** shared-address clusters above N members (propose N=15, tune with data) are auto-classified `high_occupancy_address`, emit no pairwise weak edges, and appear only as an address-level annotation; unit-level (suite) agreement required for any cluster of size > 3 to emit edges |
| **Franchises** | `SUBWAY #4412` and `SUBWAY #883` share brand name but are independent owners | Numbered-unit pattern detection in name normalization (`#\d+`, `STORE \d+`) marks `franchise_candidate`; brand-token match without matching registry number never passes rung 4; franchise flag displayed on any candidate pair |
| **Mergers / successors** | Old entity's history wrongly continues (or wrongly stops) at acquirer; UEI may change or persist across a merger (*confidence: unknown — verify SAM.gov practice*) | Successor links are their own weak edge type `succeeded_by_candidate` (name/address continuity + registration date adjacency), never an automatic merge; temporal validity (`valid_from`/`valid_to`) on edges so pre-merger conduct stays attached to the pre-merger entity; merges of entities with non-overlapping active registration periods require human review always |
| **UEI/DUNS transition artifacts** | Pre-April-2022 records key on DUNS, later on UEI; crosswalk gaps break longitudinal identity (Blueprint 01 flags this for USAspending) | Treat DUNS as a rung-3-class identifier in a `vendor_identifiers` table, never fabricate a DUNS↔UEI equivalence without a crosswalk field from an authoritative record (SAM entity data historically carried both — *verify field availability*); where no crosswalk exists, the pre/post entities remain linked only by `candidate_same_entity` and longitudinal detectors must state the gap |
| **Data-entry noise in identifiers** | Transposed UEI/CAGE characters in secondary sources cause false rung-1/2 hits | Checksum/format validation before trusting an identifier (verify whether UEI has a check character — *unknown*); identifier match with wildly disagreeing names (token overlap ≈ 0) drops to review instead of auto-merge |
| **Agencies reorganize** | Sub-agency codes and names change across administrations | Agencies resolve on official code sets per source (e.g. USAspending agency codes) with temporal validity; never name-only for agencies |

## 8. Merge decisions: recorded and reversible

### 8.1 Merge mechanics

Merges use a **survivorship-free, non-destructive** design: we do not rewrite
`vendor_id` foreign keys on awards/payments at merge time in a way that loses
the original resolution.

- Every raw-source entity mention resolves to an `entity_mention` (or keeps
  its original `vendor` row) that is **never deleted**.
- A merge writes a `merge_log` row and repoints a *canonical pointer*
  (`vendor.canonical_id` self-FK, or a `vendor_canonical_map` table): all
  members of a merge set point at one surviving canonical row. Queries and
  detectors always resolve through the pointer.
- Attribute survivorship (which name/address displays on the canonical row)
  is a pure function of source tier + recency, recomputed on demand — not a
  hand-edited copy.

### 8.2 `merge_log` (append-only)

| Column | Meaning |
|---|---|
| `id`, `created_at` | |
| `merged_ids` | the entity ids folded in |
| `surviving_id` | canonical target |
| `method` + `ladder_version` | e.g. `uei_exact @ ladder_v2` |
| `rung` / `confidence` | from Section 2 |
| `evidence_refs` | the exact matched field values, quoted (EvidenceItem standard) |
| `created_by_run` | resolution run id (for bulk rollback) |
| `actor` | `system` for rung 1–3 auto-merges; reviewer identity for human-confirmed merges (`GOVERNANCE.md` audit-trail requirement) |
| `status` | `active` / `reversed` |
| `reversal_of` / `reversed_by` | self-FKs linking a merge to its unmerge |

### 8.3 Unmerge procedure (the correction workflow)

Trigger: a reviewer flags a wrong merge (from the resolution review queue, a
case-lead review, or an external correction), or a source correction/
`source_revoked` event (per `DATA_SOURCE_POLICY.md`) invalidates the evidence
a merge relied on.

1. Reviewer opens an **unmerge action** citing the `merge_log` id and a
   structured reason (wrong-identifier-in-source, franchise, agent-address,
   successor-confusion, other) — structured reasons feed ladder tuning,
   mirroring `DETECTION_PRINCIPLES.md` #8.
2. System writes a new `merge_log` row (`status` on the original →
   `reversed`, linked via `reversed_by`) and repoints canonical pointers back
   to the pre-merge state — possible precisely because mentions were never
   destroyed and pointers, not row rewrites, carried the merge.
3. **Cascade audit:** every `RiskSignal`, `CaseLead`, derived edge, and
   materialized network row whose `created_by_run` consumed the merged
   identity is flagged `resolution_reverted` and re-queued for
   recomputation; open case leads get an automatic reviewer note. Exported
   case packets cannot be recalled, so the packet template must state the
   merge basis (method + confidence) at export time — the reader was warned.
4. The unmerge reason is added, where applicable, to the guardrail data files
   (e.g. a newly discovered registered-agent address goes to the allowlist).

Bulk rollback: because merges carry `created_by_run`, an entire faulty
resolution run (bad normalizer release, corrupted source file) can be
reversed as a unit, then re-run after the fix.

*Confidence that this pointer-based reversible design is sound and standard
(it mirrors common master-data-management practice): high. Cost: every entity
read path must resolve the canonical pointer — accept this; correctness of
identity beats query convenience.*

## 9. Method confidence summary

Proposed starting `confidence` values; all are design parameters pending
Phase-1 measurement against reviewer-labeled samples.

| Method | Proposed confidence | Strength class | Auto-action |
|---|---|---|---|
| `uei_exact` | 0.98 | strong | merge |
| `cage_exact` | 0.95 | strong | merge |
| `registry_number_exact` (same registry) | 0.93 | strong | merge |
| `agency_code_exact` (official code sets) | 0.97 | strong | merge (agencies) |
| `name_addr_exact` (post-normalization, guardrails passed) | 0.75 | weak | candidate edge + review queue |
| `name_addr_exact` at unit level (suite match) | 0.80 | weak | candidate edge + review queue |
| `shares_address` derived edge (guardrails passed) | 0.55 | weak | context only |
| `shares_officer_name` | 0.35 | weak | context only |
| `succeeded_by_candidate` | 0.40 | weak | context only |
| `name_only` | 0.40 | — | blocking only, no edge |
| `probabilistic_*` (Phase 5+) | model score | weak | review queue only |

## 10. Verify-before-reliance checklist (carried into Phase 1 tickets)

1. SAM.gov UEI persistence/reuse policy; one-entity-multiple-UEIs semantics;
   whether UEI includes a check character.
2. CAGE assignment/reuse rules and field availability in our admitted sources.
3. DUNS↔UEI crosswalk field availability in SAM entity data and USAspending
   historical files.
4. usaddress maintenance status; libpostal model size and license, before
   any adoption decision.
5. Field-population rates (share of award rows with usable UEI) on the first
   real USAspending pull — this decides how much weight rungs 4–5 must carry.
6. Any specific count cited for shared registered-agent addresses — do not
   put a number in UI or docs without a citable source.
7. Splink license/backends, only when the probabilistic phase is actually
   scheduled.
