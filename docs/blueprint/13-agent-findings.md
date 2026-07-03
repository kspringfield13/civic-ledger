# Blueprint 13 — Agent Findings (Deliverable B)

Synthesis of the ten specialist agents' conclusions, disagreements, risks,
and assumptions. Each agent read the repo's governance docs and existing
code before writing; their full output is the numbered blueprint series.
The red-team pass is Blueprint 12; this document records what each agent
concluded and where they pushed back on the mission or on each other.

## Per-agent conclusions

**Mission Commander** (→ 00) — Defined v1 as a lead-generation and
human-review tool over federal procurement + exclusions data, with six
binding non-goals (no real-time ingestion, no probabilistic identity
merging, no scoring of people), seven measurable success criteria, and five
hard domain decisions: federal procurement first (D1), benefits fraud
deferred as disqualified by the boundaries docs (D2), campaign-finance
correlation deferred *indefinitely* pending a dedicated bias-risk review
(D3), grants as second domain post-Phase-3 (D4), IG/court records as
corroboration only (D5). Refused signal-volume and dollars-flagged as
vanity metrics.

**Legal / Ethics / Evidence** (→ 09) — Converted governance prose into
enforceable controls: four-role permission matrix with universal denials
and a two-party rule; append-only audit-event catalog; fail-closed evidence
citation at write, API, UI, and export layers; lead state machine; per-class
retention clocks; a seven-step entity-correction workflow with automatic
freeze and recompute; product-level prohibited uses; human-only escalation
paths with per-claim legal confidence labels (none lawyer-verified yet).

**Fraud Typology** (→ 02) — 19 patterns across six domains, each with
computable public-data signals, 2–4 innocent explanations, and an honest
detectability rating. Key finding: classic collusion (bid rigging,
complementary bidding) is a **structural gap** in award-level public data —
winners are published, losing bids are not; the strongest fully public
patterns are excluded-party matching and threshold splitting. Named four
schema extensions required before certain detectors can honestly exist.

**Public Data** (→ 01) — 16 prioritized Tier-1/Tier-2 sources, each with
access method, fields, cadence, difficulty, known quality issues
(USAspending lag and underreporting, DUNS→UEI 2022 transition, FSRS
subaward under-reporting, DoD ~90-day FPDS delay), per-entry confidence,
and verify-before-reliance items. Ranked SAM exclusions #1 (small, daily,
powers the flagship detector), USAspending #2. Eight-item DO-NOT-INGEST
list (data brokers, people-search, ToS-prohibited scraping, borrowed
credentials, individual-benefit payment categories).

**Data Architecture** (→ 03, 05) — Five-layer dataflow with write-once
SHA-256'd raw files, row-level lineage, idempotent re-ingestion, snapshot
semantics for exclusions; cron+make over Airflow and Python services over
dbt, both with written revisit triggers; full 18-table data model with
reference DDL and 20 numbered migration TODOs. Found three latent defects
in current code: money typed as float (correctness bug for exact-amount
detectors), `PersonOfficer` lacking provenance, and no CaseLead↔RiskSignal
link — the evidence chain broken exactly where humans act.

**Network Intelligence** (→ 04) — Five-rung identifier ladder with per-rung
confidence; deterministic-only matching in v1; strong/weak edge separation
with the non-negotiable rule that weak links never propagate risk (they
produce resolution-review tasks, not signals); registered-agent addresses
excluded from clustering entirely; merges pointer-based and reversible via
an append-only merge log with cascading `resolution_reverted` on unmerge.

**Detection** (→ 06, 07, 5 new YAML specs) — Ten detectors total, contract
tests green. Three of the five new specs honestly declare themselves
blocked on schema extensions. Scoring framework keeps seven factors
separate and combines them into a hand-reproducible triage order
(`score = min((p_max + 0.25·Σ top-4)·C, 1.0)`) with worked examples,
hard review-status gates, and an explicit no-fraud-labels statement.

**Product / UX** (→ 08) — 12-route page map on the existing React shell.
Governance rules became component contracts: confidence renders only
paired with severity, aggregates require a base-rate denominator prop,
evidence-less signals render as error states, red is reserved for system
integrity failures (never for subjects), no browsable per-entity risk
scores anywhere, dismissals use structured reason codes fed from the
spec's own FP-mode list, packets are server-side watermarked.

**Engineering** (→ 10, 11) — Build plan on the existing stack with a
machine-readable `execution:` block added to the spec contract (typed
primitives; prose stays the reviewer-facing truth), stdlib CLI + make
targets, `pipeline_runs` as the audit-linked job table, full ingest and
engine pseudocode, 7-layer test strategy, and a 52-task M1–M6 backlog
sized for the mobile /goal workflow. Found that routers are placeholders
with no DB wiring, Alembic is uninitialized, and CORS blocks POSTs — and
scoped M1 accordingly.

**QA / Red Team** (→ 12) — The dedicated agent run was cut short by a
session limit; the command model performed the pass instead. Sixteen
findings; highest severity: name-only individual exclusion matches (RT-1),
merge errors outrunning the correction workflow (RT-2), and float-typed
money breaking exact-amount grouping (RT-8). Verdict: no boundary
violations in any draft; the likeliest real failures are unglamorous data
bugs, all with cheap M1–M3 fixes.

## Disagreements worth preserving

1. **Detectability honesty vs. mission ambition.** The mission listed bid
   rigging as a target; the typology agent downgraded it to a weak proxy
   (losing bids aren't public) and the detection agent encoded that
   disclaimer verbatim in `bid_rotation_pattern`'s hypothesis. Resolved in
   favor of honesty — the system claims rotation-shaped award histories,
   never collusion.
2. **Name+address as a merge rung.** The task framing implied name+address
   could auto-merge; network-intel demoted it to review-queue only, calling
   it the most likely source of wrongful risk transfer. Stands.
3. **Entity-level scores in the UI.** The scoring doc defines composite
   scores; product-UX prohibits browsable per-entity scores and allows them
   only to order queues. Stands — scores order attention, never label
   organizations.
4. **Grants reuse.** The schema makes running procurement detectors on
   `GrantAward` trivial; the mission brief bars it (D4) because the
   innocent-explanation profiles differ. Stands until grant-specific specs
   exist.
5. **`taxonomy_ref` required vs. optional.** Typology wanted it required in
   the spec contract; detection made it optional to avoid breaking the five
   existing specs. Backfill filed as an M3 task (RT-13).
6. **Person-level signals.** Legal-ethics constrained rather than banned
   them: allowed only when the official-capacity record itself is the
   pattern, hypothesis naming the capacity, never the person. Mission brief
   went further for v1: no person-subject signals at all (N6). V1 follows N6.
7. **Engineering vs. ROADMAP literalism.** "Engine reads YAML generically"
   is not literally achievable against prose logic; the execution-block
   compromise keeps prose authoritative for humans and primitives
   authoritative for machines, with the semantic-equivalence check named as
   a human review gate.

## Shared assumptions (binding until falsified)

- SAM.gov public exclusions extract and USAspending bulk/API exist and are
  publicly accessible (high confidence) — but current formats, field names,
  auth requirements, and rate limits are unverified (moderate); every
  ingestion PR is gated on verification against live documentation.
- A human reviewer exists to generate dispositions; without one, the
  precision metrics and the Principle-8 tuning loop are unmeasurable.
- All numeric thresholds anywhere in the blueprint (rung confidences,
  scoring constants, detector gates, retention clocks) are declared
  starting defaults for operator tuning, not calibrated values.
- Single-operator deployment is the compensating control until Phase-5
  auth; the platform must not be multi-tenant before then.

## Top risks (consolidated)

1. Wrongful implication via identity error — mitigated by deterministic-only
   merging, weak-link non-propagation, the freeze-and-recompute correction
   workflow, and RT-1/RT-2 fixes; this remains the system's most harmful
   failure mode and every phase must treat it as such.
2. Unverified source mechanics stalling Phase 1 — mitigated by
   fixture-first milestones (M1–M3 close on fictional data alone).
3. Reviewer scarcity stalling the feedback loop — flagged to operator
   (open question 2 in the brief).
4. Float money / schema defects corrupting exact-match detectors —
   RT-8, fix scheduled M1.
5. On-paper controls creating false assurance before enforcement lands —
   each control's enforcement point and phase is tabled in 09 §10; gaps are
   restated per release rather than silently normalized.
