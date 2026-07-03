# Executive Mission Brief — civic-ledger v1

**Deliverable A of the blueprint series. Status: adopted unless the operator overrides.**
This brief builds on — and defers to — `CLAUDE.md`, `LEGAL_AND_ETHICAL_BOUNDARIES.md`,
`DATA_SOURCE_POLICY.md`, `EVIDENCE_STANDARD.md`, `DETECTION_PRINCIPLES.md`,
`GOVERNANCE.md`, and `ROADMAP.md`. Where this document is silent, those govern.
Where this document appears to conflict with them, they win.

---

## 1. Purpose in plain language

Public spending data is published, but it is published in volumes no human can
read. civic-ledger reads it so a human doesn't have to read all of it — and then
hands the human a short, evidence-linked list of things worth a closer look.

Concretely: the system ingests lawful public records (federal award data,
official exclusion/debarment lists), normalizes them, runs transparent
rule-based detectors over them, and produces **risk signals** bundled into
**case leads** for a human review queue. Every signal links to the exact source
records that produced it, carries a confidence score, and lists the innocent
explanations that could produce the same pattern.

The product of this system is a *better-prioritized reading list for a human
reviewer*. Nothing more. The value proposition is triage, not judgment.

## 2. What v1 IS

- A **lead-generation and human-review tool** over public procurement and
  exclusion data (federal first — see prioritization below).
- A **provenance machine**: every stored record keeps its source locator,
  retrieval timestamp, and SHA-256 hash (`SourceDocument`); every signal keeps
  its evidence chain (`EvidenceItem`). A signal without resolvable evidence is
  invalid and is not persisted.
- A **transparent detector runner**: declarative YAML specs
  (`detectors/*.yml`) a reviewer can read, each stating its hypothesis, its
  known false-positive modes, and how severity and confidence are computed.
- A **review workflow with an audit trail**: assign, disposition with
  structured reasons (`ReviewAction`), export a case packet per
  `EVIDENCE_STANDARD.md`.
- Runnable end-to-end on **fictional sample data** (`data/sample/`) so every
  feature is testable without touching a live source.

## 3. What v1 is NOT

- **Not proof.** Outputs are hypotheses for human review. No output states or
  implies that anyone committed fraud. The words "fraudulent," "criminal,"
  "guilty," and "committed" are banned from code, UI, exports, and docs
  (enforced language standard in `EVIDENCE_STANDARD.md`).
- **Not surveillance.** No monitoring of individuals, no tracking, no
  aggregation of personal data beyond what the public record itself contains.
  Individuals appear only in official/registered capacities (`PersonOfficer`),
  exactly as recorded in public documents.
- **Not a people-tracking or investigation-of-persons tool.** Analysis
  centers on transactions and organizations. There is no "person page," no
  person-centric search, and no enrichment of private individuals in v1.
- **Not a publishing platform.** Nothing leaves the system without a human
  drafting or approving it (`GOVERNANCE.md`). No public dashboards of named
  entities, no automated referrals, no target lists.
- **Not an ML product.** v1 scoring is transparent rules only. Any future ML
  assists triage *ordering* and never creates signals by itself
  (`DETECTION_PRINCIPLES.md` #1).

## 4. Explicit non-goals for v1

Stated as decisions, not aspirations:

| # | Non-goal | Rationale |
|---|----------|-----------|
| N1 | Real-time / streaming ingestion | Public sources update daily-to-monthly; batch is honest about the data's actual cadence and far cheaper to make correct. |
| N2 | Multi-tenant SaaS, external users, or public API | One operator, one reviewer role. Auth and hardening are Phase 5 (`ROADMAP.md`); scaling before governance maturity multiplies the harm of any mistake. |
| N3 | Automated escalation or referral | Escalation beyond the review queue is a human decision made outside this system (`LEGAL_AND_ETHICAL_BOUNDARIES.md`). |
| N4 | Sub-federal (state/local) source integrations | State checkbook portals vary wildly in schema, license, and terms; each needs its own source-inventory entry and operator sign-off. Federal-first keeps the ingestion surface small. Deferred, not rejected. |
| N5 | Entity-resolution "cleverness" (probabilistic identity merging across sources) | Wrong merges create false signals against real organizations. v1 uses conservative matching: exact UEI, then normalized-name + address with visible match rationale. Fuzzy-only matches cap confidence low. |
| N6 | Any scoring of *people* | Signals attach to transactions and organizations (`RiskSignal.subject_type`). No detector may take a person as its subject in v1. |

## 5. Success criteria (measurable, not vanity)

Vanity metrics we explicitly refuse to optimize: number of signals generated,
total dollars "flagged," dataset row counts, dashboard pageviews. All of these
go *up* when the system gets *worse* (noisier). The metrics below are the
contract:

| # | Metric | Definition | v1 target | Measured how |
|---|--------|------------|-----------|--------------|
| S1 | **Review-queue precision** | Of leads a human dispositioned, fraction marked `confirm-worthy` or `needs-data` (i.e., not `dismissed`) | ≥ 30% after two tuning cycles; if it stays below ~10% the detector thresholds are wrong and tuning is the priority | `ReviewAction` reason codes, per detector |
| S2 | **Evidence-link completeness** | Fraction of persisted `RiskSignal` rows with ≥1 resolvable `EvidenceItem` whose `SourceDocument` locator still dereferences | 100% at write time (hard gate in `services/evidence.py`); ≥ 99% on scheduled re-resolution checks | Automated audit job |
| S3 | **Time-to-triage** | Median wall-clock time from lead creation to first `ReviewAction` | Baseline in first 30 review days, then reduce 25% | `CaseLead.created_at` → first `ReviewAction.at` |
| S4 | **Reproducibility** | Re-running a detector version on the same input snapshot yields byte-identical signal sets | 100%; any diff is a release-blocking bug | CI regression test on sample data |
| S5 | **Structured-dismissal coverage** | Fraction of dismissals carrying a `reason_code` (not just free text) | ≥ 95% | `ReviewAction` audit |
| S6 | **Provenance integrity** | Fraction of `SourceDocument` rows with SHA-256 recorded at ingestion | 100% (hard gate) | Schema constraint + audit |
| S7 | **False-positive-mode accounting** | Every dismissal reason maps to either a known FP mode in the detector spec or triggers a spec update adding the new mode | Every unmatched dismissal reason produces a spec change or a documented decision not to | Monthly review of dismissal codes vs. specs |

S1 is deliberately a *floor with an alarm*, not a ceiling: precision measured
against reviewer judgment is itself uncertain (reviewers see only what the
system surfaces). We do not claim it measures true fraud detection — only
whether the queue wastes reviewer time.

## 6. Hard prioritization: domains for v1

**Decision D1 — First target: federal procurement + exclusions.**
v1 detectors run over federal contract awards, payments, and official
exclusion/debarment records. Rationale:

- **Data availability.** USAspending publishes award data with bulk download
  and a public API; SAM.gov publishes a public exclusions extract. Both are
  Tier-1 authoritative sources under `DATA_SOURCE_POLICY.md` and are already
  named in `ROADMAP.md` Phase 1 as the recommended first sources.
  *Confidence: high that both exist and are public; moderate on exact current
  file formats, field names, and API-key requirements — verify against live
  documentation before writing ingestion code, and complete a
  `docs/data-source-inventory-template.md` entry per source with operator
  sign-off before any ingestion code merges (GOVERNANCE decision rule).*
- **Sample compatibility.** The fictional samples in `data/sample/`
  (contract awards, exclusions, vendors) already mirror this domain, so the
  full pipeline is testable offline today.
- **Model fit.** The existing schema (`ContractAward`, `Payment`,
  `ExclusionRecord`, `Vendor`, `Agency`) and all five committed detector specs
  (`debarred_vendor_match`, `duplicate_payment`, `split_purchase`,
  `shared_address_cluster`, `vendor_concentration`) target this domain.
- **Ethical fit.** Subjects are organizations and transactions, which is
  exactly where the boundaries docs want analysis centered.

Within the domain, detector order: `debarred_vendor_match` first (crispest
hypothesis, authoritative match target, lowest FP surface), then
`duplicate_payment`. The other three specs wait until Phase 3 review data
exists to tune against. This matches `ROADMAP.md` Phase 2 exactly.

**Decision D2 — Deferred: benefits/program fraud (unemployment, healthcare
claims, SNAP, etc.).** Reason: meaningful detection requires claim-level or
beneficiary-level data that is not public and centers on individuals — both
disqualifying under `LEGAL_AND_ETHICAL_BOUNDARIES.md`. Public aggregates (e.g.
agency improper-payment reporting) are context (Tier 3 at best for signal
purposes), not detection substrate. Revisit only if an operator arrives with
documented authorization over their own program data, and even then only after
a governance review, because the individual-subject prohibition (N6) would be
under pressure.

**Decision D3 — Deferred: campaign-finance / political-donation correlation
with contract awards.** Reason: highest political-bias risk of any candidate
domain. Donation-then-award patterns have a massive innocent base rate, the
"detector" output would inherently name individuals in a politically charged
frame, and a false signal is reputationally weaponizable in a way procurement
anomalies are not. This domain is deferred indefinitely, not queued: it needs
a dedicated bias-risk review, per-detector political-neutrality tests, and
explicit operator acceptance of the risk before a single line of code.

**Decision D4 — Deferred: grant-award analytics.** `GrantAward` exists in the
schema and grants data flows through the same federal sources, so this is the
natural *second* domain — but not before Phase 3 review workflow exists.
Grants have different innocent-explanation profiles (formula grants, renewals)
that require their own detector specs; reusing procurement detectors on grants
would violate DETECTION_PRINCIPLES #2 and #4.

**Decision D5 — Deferred: IG-report and court-record corroboration
(CourtListener, agency IG releases).** Legitimate Tier-1/Tier-2 sources, but
they are corroboration for open leads, not signal generators. They enter in a
post-v1 phase once there are leads to corroborate.

## 7. 30/60/90-day roadmap (maps to ROADMAP.md phases)

**Days 1–30 — Phase 1: Data foundation.**
- Alembic baseline migration; SQLAlchemy persistence wired end-to-end.
- Source-inventory entries drafted for SAM.gov exclusions and USAspending;
  operator sign-off obtained (blocking gate before ingestion code).
- Ingestion service for both sources: hash-at-ingest, provenance rows, raw →
  `data/raw/`, normalized → `data/processed/`. Full pipeline proven against
  `data/sample/` fixtures first.
- Name/address canonicalization in `services/normalization.py` with tests.
- Exit criteria: `make test`/`make lint` green; sample data round-trips
  ingest → normalize → DB with 100% provenance (S6).

**Days 31–60 — Phase 2: First working detectors.**
- Generic detector engine reading YAML specs (no per-detector hardcoding).
- `debarred_vendor_match` and `duplicate_payment` live: spec → engine →
  `RiskSignal` + `EvidenceItem` rows, gated by `services/evidence.py`.
- Contract tests promoted into runtime spec validation.
- Reproducibility regression test (S4) in CI.
- Exit criteria: signals on sample data are byte-reproducible and 100%
  evidence-linked; conservative matching rules of N5 implemented with match
  rationale stored on the signal.

**Days 61–90 — Phase 3 + start of Phase 4: Review workflow, then dashboard.**
- Case queue: assign, disposition with structured `reason_code`s, full
  `ReviewAction` audit trail; case-packet markdown export per
  `EVIDENCE_STANDARD.md`.
- Begin S1/S3 measurement the day the queue opens; first threshold-tuning
  cycle from structured dismissal reasons before day 90.
- Dashboard work (Phase 4) starts only after the queue has real dispositions:
  evidence drill-down and base-rate context (flagged vs. total population)
  are the first two dashboard features, per DETECTION_PRINCIPLES #7.
- Phase 5 (Postgres default, API auth, CI gates, deployment) intentionally
  stays outside the 90-day window unless Phases 1–3 land early.

## 8. Top 10 immediate next actions (input to deliverable L)

1. Write the Alembic baseline migration for the existing models and wire
   `make db-up` to apply it. (Blocks everything.)
2. Build the sample-data ingestion path: load `data/sample/*.csv` through the
   real ingestion service (hashing, `DataSource`/`SourceDocument` rows) so the
   pipeline is exercised before any live source is touched.
3. Draft the `docs/data-source-inventory-template.md` entry for the SAM.gov
   public exclusions extract — verify current file format, field names
   (UEI vs. legacy identifiers), and access terms against live SAM.gov
   documentation; do not code from memory. Submit for operator sign-off.
4. Draft the inventory entry for USAspending award data — verify current bulk
   download formats and API terms/rate limits from live docs. Operator
   sign-off before ingestion code.
5. Implement `services/normalization.py` name/address canonicalization with a
   test suite of adversarial cases (punctuation, suffixes like LLC/Inc,
   address abbreviation variants), using the fictional samples.
6. Implement the generic YAML detector engine skeleton: load spec, validate
   against `docs/detector-spec-template.md` contract, execute against the DB,
   emit nothing yet.
7. Implement `services/evidence.py` gating: persisting a `RiskSignal` without
   ≥1 `EvidenceItem` referencing a real `SourceDocument` must be impossible,
   with a test proving it.
8. Wire `debarred_vendor_match` end-to-end on sample data: exact-UEI match at
   high confidence, normalized-name+address at lower confidence, match
   rationale recorded per signal.
9. Add the reproducibility regression test (S4): run the detector twice on
   fixture data in CI, assert identical output.
10. Add a language-standard lint check: CI fails if prohibited accusation
    vocabulary ("fraudulent", "guilty", "criminal", "committed fraud") appears
    in UI strings, API responses, or export templates.

## 9. Decision log (this brief)

| ID | Decision | Rationale summary |
|----|----------|-------------------|
| D1 | Federal procurement + exclusions is the only v1 detection domain | Bulk-available Tier-1 data, sample-compatible, matches schema and committed detector specs, organization-centric |
| D2 | Benefits fraud deferred | Needs non-public, individual-level data — disqualified by boundaries docs |
| D3 | Campaign-finance correlation deferred indefinitely | Highest political-bias and reputational-weaponization risk; needs dedicated governance review first |
| D4 | Grants are the designated second domain, post-Phase-3 | Same sources and schema, but needs its own detector specs and FP modes |
| D5 | IG reports / court records enter as corroboration only, post-v1 | They corroborate leads; they don't generate signals |
| N1–N6 | Non-goals table above adopted as binding for v1 | See table |
| S1–S7 | Success criteria adopted; vanity metrics refused | Metrics must get worse when the system gets noisier, not better |

## 10. Open questions for the operator

1. Confirm D3's indefinite deferral of campaign-finance correlation, since it
   is the domain most often requested of tools like this.
2. Who is the reviewer for the first S1 measurement cycle — the operator, or
   is a second human available? S1 is meaningless without real dispositions.
3. Acceptable staleness window for exclusion data (drives ingestion cadence
   and the wording of `debarred_vendor_match` confidence inputs).
