# Blueprint 08 — Product & UX: the investigator-facing application

Status: DRAFT design, subordinate to the repo governance docs
(`LEGAL_AND_ETHICAL_BOUNDARIES.md`, `DATA_SOURCE_POLICY.md`,
`EVIDENCE_STANDARD.md`, `DETECTION_PRINCIPLES.md`, `GOVERNANCE.md`). Where this
document conflicts with those, they win. Cross-references:
[03-architecture-v1.md](03-architecture-v1.md) for the API layer,
[04-entity-resolution-and-network.md](04-entity-resolution-and-network.md) for
link strength and cluster semantics, [05-data-model.md](05-data-model.md) for
the tables every page reads, [06-risk-scoring.md](06-risk-scoring.md) for how
severity and confidence are computed, and
[09-governance-and-safety-controls.md](09-governance-and-safety-controls.md)
for the controls this UI must surface.

**Starting point (verified in code):** the frontend is a Vite + React +
React Router shell with five routed pages (`frontend/src/main.tsx`:
`/`, `/sources`, `/entities`, `/risk-signals`, `/cases`), a shared `Layout`
with the header disclaimer "Risk signals for human review — not determinations
of fraud", and two governance-aware components: `RiskBadge` (renders severity
and confidence as *separate* values, per `DETECTION_PRINCIPLES.md` #3) and
`EvidenceLink`. This blueprint evolves that shell; it does not replace it.

Epistemic note: backend endpoints `/sources`, `/entities`, `/risk-signals`,
`/cases` exist today (consumed via `frontend/src/api/client.ts`). Every other
endpoint named below is **proposed** and must be built (Phases 2–4 of
`ROADMAP.md`). Field names below are taken from `backend/app/models/*.py`
where they exist; fields marked *(proposed)* do not exist yet.

---

## 1. UX constitution — non-negotiable rendering rules

These rules are enforced in shared components, not left to page authors.
They are the UI translation of the governance docs.

1. **Confidence is always adjacent to severity.** No component may render
   severity without confidence in the same visual group, ever. The two are
   different quantities (`DETECTION_PRINCIPLES.md` #3) and separating them is
   how a UI silently converts "big contract, weak evidence" into "bad vendor."
   Enforced by making `SeverityConfidencePair` (the evolved `RiskBadge`) the
   *only* exported way to render either number; a lint rule
   (Section 9) rejects direct rendering of `signal.severity`.
2. **Base-rate context on every aggregate.** Any count of flagged things is
   rendered with its denominator (`DETECTION_PRINCIPLES.md` #7): "14 signals
   across 2,304 payments analyzed (0.6%)", never "14 signals." Enforced by
   the `BaseRateStat` component, which *requires* a `population` prop — there
   is no variant without one.
3. **False-positive modes are shown on every signal**, everywhere a signal
   appears — collapsed to one line on cards ("3 innocent explanations —
   expand"), fully expanded on detail pages. Sourced from the detector spec
   version recorded on the signal (`RiskSignal.detector_version`), never
   hand-written per signal.
4. **Evidence links are mandatory and must resolve.** A signal whose evidence
   items cannot be fetched, or whose `SourceDocument` locator/hash is missing,
   renders as an **error state, not a signal card**: a `SignalIntegrityError`
   panel saying "This signal has no resolvable evidence and is invalid per
   EVIDENCE_STANDARD.md — do not act on it," with a one-click "report data
   defect" action. The backend should never produce such a row
   (`services/evidence.py` gates persistence), so the UI treating it as a
   defect — not degrading gracefully — is deliberate defense in depth.
5. **Neutral language only.** The word set from `EVIDENCE_STANDARD.md`
   ("risk signal", "pattern consistent with…", "warrants review", "matches
   exclusion record") is the vocabulary of every label, tooltip, empty state,
   and export. Prohibited terms ("fraudulent", "criminal", "guilty",
   "committed", assertions of intent) are linted out (Section 9).
6. **Humans decide; the UI never pre-decides.** No auto-escalation, no
   "recommended action: refer", no default-selected dispositions. Buttons
   describe the reviewer's act ("Mark confirm-worthy"), not a conclusion
   about the subject.

---

## 2. Route map

Existing routes evolve in place; new routes nest under the same `<App />`
layout route in `frontend/src/main.tsx`.

| Route | Page | Status |
|---|---|---|
| `/` | Dashboard | exists — evolve |
| `/sources` | Sources registry | exists — evolve |
| `/sources/:id` | Source detail (documents, hashes, terms) | new |
| `/entities` | Entity search/list | exists — evolve |
| `/entities/vendors/:id` | Vendor profile | new |
| `/entities/agencies/:id` | Agency profile | new |
| `/risk-signals` | Signal triage list | exists — evolve |
| `/risk-signals/:id` | Signal detail | new |
| `/cases` | Case queue | exists — evolve |
| `/cases/:id` | Case detail | new |
| `/cases/:id/export` | Case packet export flow | new |
| `/network` | Network / cluster view (`?focus=vendor:123` deep link) | new |

Proposed `main.tsx` additions (matching the existing nested-route style):

```tsx
<Route element={<App />}>
  <Route index element={<Dashboard />} />
  <Route path="sources" element={<Sources />} />
  <Route path="sources/:id" element={<SourceDetail />} />
  <Route path="entities" element={<Entities />} />
  <Route path="entities/vendors/:id" element={<VendorProfile />} />
  <Route path="entities/agencies/:id" element={<AgencyProfile />} />
  <Route path="risk-signals" element={<RiskSignals />} />
  <Route path="risk-signals/:id" element={<SignalDetail />} />
  <Route path="cases" element={<CaseQueue />} />
  <Route path="cases/:id" element={<CaseDetail />} />
  <Route path="cases/:id/export" element={<CaseExport />} />
  <Route path="network" element={<NetworkView />} />
</Route>
```

`Layout.tsx` nav gains one item (`/network`); detail routes are reached by
navigation from lists, not from the nav bar. The header disclaimer line stays
on every page — it is part of the layout, not the pages.

### Shared component inventory (evolved + new)

| Component | Replaces/extends | Contract |
|---|---|---|
| `SeverityConfidencePair` | `RiskBadge` | Renders both numbers plus banded labels ("severity: high (0.82) · confidence: moderate (0.55)"). Neutral gray/slate chip — never red (Section 9). Tooltip lists the declared inputs that produced each number. |
| `EvidencePanel` / `EvidenceLink` | `EvidenceLink` | Link form navigates to the evidence section of signal detail; panel form lists each `EvidenceItem` with source name + tier, locator, SHA-256 (truncated, copyable), retrieval timestamp, and the quoted `fields_relied_on`. Renders `SignalIntegrityError` if any item fails to resolve. |
| `SignalCard` | new | The only sanctioned way to render a signal in a list: hypothesis text, `SeverityConfidencePair`, detector id+version, FP-modes collapsed line, `EvidenceLink` with count, subject link. |
| `SignalIntegrityError` | new | Error card for rule 4 above. |
| `BaseRateStat` | new | `flagged` + `population` required props; renders count, denominator, percentage. |
| `FpModeList` | new | FP modes from the detector spec, each with its "how to distinguish" validation note. |
| `DispositionForm` | new | Structured dismissal UI (Section 6). |
| `AssignmentControl` | new | Assign/claim a lead (Section 6). |
| `NetworkCanvas`, `EdgeLegend`, `ClusterWarningBanner` | new | Section 7. |
| `ExportStepper`, `WatermarkFrame` | new | Section 8. |
| `ProvenanceFooter` | new | On every detail page: source documents involved, hashes, retrieval timestamps. |

---

## 3. Pages — existing five, evolved

For each page: purpose, key components, data needed, uncertainty-visibility
requirements ("UV").

### 3.1 Dashboard (`/`)

- **Purpose:** situational awareness for the operator: what was ingested,
  what ran, what needs review. It is a workload view, not a threat board.
- **Key components:** `BaseRateStat` tiles (signals open / population
  analyzed, per detector); ingestion freshness table (source → last
  `SourceDocument.retrieved_at`); detector run log (spec version, rows
  scanned, signals emitted); review-throughput strip (leads opened /
  dispositioned this week); "needs attention" list (stale assigned leads,
  `source_revoked` flags per `DATA_SOURCE_POLICY.md`).
- **Data needed:** *(proposed)* `GET /stats/overview` aggregating
  `RiskSignal` counts by detector + status with population denominators;
  `GET /stats/ingestion`; `GET /stats/review`.
- **UV requirements:** every tile is a `BaseRateStat` — a raw "open signals: N"
  tile is prohibited. Per-detector tiles show the detector's historical
  dismissal rate next to its open count *(requires `ReviewAction` aggregation;
  proposed)* so a noisy detector is visibly noisy. No ranking of vendors or
  agencies anywhere on this page (Section 9).

### 3.2 Sources (`/sources`) + Source detail (`/sources/:id`)

- **Purpose:** the provenance registry made visible — the reviewer's answer to
  "where did this data come from and are we allowed to have it."
- **Key components:** source table (name, `tier` with the tier legend from
  `DATA_SOURCE_POLICY.md`, `access_basis`, `license`, `approved_at`); detail
  page adds terms notes, document list (`locator`, `sha256`,
  `retrieved_at`, `retrieval_method`), and the completed inventory-template
  entry link.
- **Data needed:** existing `GET /sources`; *(proposed)* `GET /sources/:id`,
  `GET /sources/:id/documents` (paginated).
- **UV requirements:** tier is always shown with its meaning ("Tier 2 —
  corroboration only, weighted lower in confidence"), because tier feeds
  confidence and a reviewer must see it. A source with `approved_at` null
  or revoked shows a blocking banner; signals resting on it inherit a
  `source_revoked` chip everywhere they render.

### 3.3 Entities (`/entities`)

- **Purpose:** search and browse canonical entities; entry point to profiles.
- **Key components:** search box (name / UEI / normalized name); results table
  with entity type, identifiers, and *counts with denominators* ("2 open
  signals · 47 awards on record"); link to `/network?focus=vendor:ID`.
- **Data needed:** existing `GET /entities`; *(proposed)* query params
  `?q=&type=`, and per-row signal/award counts.
- **UV requirements:** an entity row never renders a summary "risk score."
  Per [06-risk-scoring.md](06-risk-scoring.md), scores order queues; a
  browsable per-vendor score invites the leaderboard failure mode
  (Section 9). Rows show *counts of open signals*, each click-through
  revealing full severity/confidence detail. Merged-entity rows show a
  "merged from N records" chip linking to merge evidence (per Blueprint 04,
  identity claims are themselves hypotheses).

### 3.4 Risk signals (`/risk-signals`)

- **Purpose:** triage list of open hypotheses, ordered for review.
- **Key components:** `SignalCard` list; filters (detector, status, subject
  type, confidence band, severity band — filterable *independently*, which
  itself teaches that they differ); sort control defaulting to the triage
  ordering from Blueprint 06; `BaseRateStat` header ("Showing 14 of 14 open
  signals from 2,304 payments analyzed").
- **Data needed:** existing `GET /risk-signals`; *(proposed)* filter/sort
  params, per-signal evidence counts and FP-mode summaries (join through
  `EvidenceItem` and detector spec).
- **UV requirements:** all of Section 1 rules on every card; cards for
  signals with unresolvable evidence render `SignalIntegrityError` in place;
  status chips are workflow words (`open`, `in_review`, `dismissed`,
  `confirmed_worthy` *— worthy of escalation, not "confirmed fraud"*), never
  outcome words.

### 3.5 Case queue (`/cases`)

- **Purpose:** the human-review work surface (Phase 3 of `ROADMAP.md`).
  Detailed workflow in Section 6.
- **Key components:** lead table (title, status chip, assignee, age, bundled
  signal count with min/max confidence range); "my queue / unassigned / all"
  tabs; `AssignmentControl` inline.
- **Data needed:** existing `GET /cases`; *(proposed)* `?status=&assignee=`,
  bundled-signal aggregates, `POST /cases/:id/actions` for the audit trail
  (`ReviewAction`).
- **UV requirements:** a lead's headline never states the pattern as fact —
  lead titles are generated from the hypothesis template ("Possible duplicate
  payments — Vendor X / Agency Y — warrants review"). The confidence *range*
  of bundled signals is visible in the queue row so a lead built on three
  low-confidence signals is not mistaken for a strong one.

---

## 4. Pages — new

### 4.1 Vendor profile (`/entities/vendors/:id`) and Agency profile (`/entities/agencies/:id`)

- **Purpose:** everything the system knows about one organization, with
  provenance, so a reviewer can evaluate signals in context rather than in
  isolation. This page exists to *reduce* false accusations: most signals die
  here when context explains them.
- **Key components (vendor):**
  - Identity header: `name`, `normalized_name`, `uei`, addresses
    (`Address.raw` + `normalized`), merge history chip ("resolved from N
    source records — view merge evidence").
  - Awards & payments tab: `ContractAward` / `GrantAward` / `Payment` tables,
    each row linking to its `SourceDocument`.
  - Officers tab: `PersonOfficer` rows, **rendered with their registered
    capacity as part of the name line** ("J. Smith — registered agent, per
    <state filing>"), never as a bare person list. No photos, no contact
    data, no links out to person search. This is the `LEGAL_AND_ETHICAL_
    BOUNDARIES.md` individuals rule made structural.
  - Signals tab: `SignalCard` list scoped to this subject.
  - Relationships tab: `RelationshipEdge` list with edge type, strength, and
    evidence pointer; "open in network view" button.
  - Exclusions panel: matching `ExclusionRecord` rows, shown as "matches
    exclusion record (name/UEI match, confidence C)" — the match itself is a
    signal with FP modes (name collisions), not a status of the vendor.
  - `ProvenanceFooter`.
- **Data needed:** *(proposed)* `GET /entities/vendors/:id` (+ `/awards`,
  `/payments`, `/officers`, `/signals`, `/edges`, `/exclusion-matches`).
- **UV requirements:** no aggregate vendor risk score (see 3.3). Every
  cross-source assertion (address match, exclusion match) shows its method
  and confidence inline. The signals tab shows the vendor's *base-rate
  context*: "3 signals across 47 awards; median vendor in this dataset: 0."
- Agency profile mirrors this with awards issued, contracting officers
  (official capacity), and signals where the agency is the subject.

### 4.2 Signal detail (`/risk-signals/:id`)

- **Purpose:** one signal, fully accountable: hypothesis, evidence, innocent
  explanations, computation inputs. This page *is* the evidence standard as
  a screen; it is also the page from which packet sections are generated, so
  its structure mirrors `docs/case-packet-template.md` sections 2–5.
- **Key components (in order, matching the packet template):**
  1. Hypothesis block: verbatim from the detector spec, with `detector_id`
     + `detector_version` and a link to the YAML spec.
  2. `SeverityConfidencePair` — expanded form showing the declared inputs
     that produced each number (`EVIDENCE_STANDARD.md`: "computed severity
     and confidence *with the inputs that produced them*").
  3. `EvidencePanel` — every `EvidenceItem`: source name + tier, locator
     (resolvable link or document ID), SHA-256, retrieval timestamp/method,
     and the quoted `fields_relied_on`. Quotes render as quotes
     (monospace, quoted), visually distinct from paraphrase.
  4. `FpModeList` — the spec's innocent explanations, each with its
     validation approach and a per-signal checklist state ("checked /
     not yet checked") *(checklist state proposed; needs a small
     `signal_fp_checks` table or JSON column)*.
  5. Uncertainty statement: auto-generated "what is NOT established by this
     signal" block (template per detector).
  6. Actions: attach to existing lead / open new lead; visible to reviewer
     role only (Section 10). There is no "dismiss" on a raw signal —
     dispositions happen on leads, where the audit trail lives.
- **Data needed:** *(proposed)* `GET /risk-signals/:id` with evidence items
  joined to `SourceDocument`, plus detector-spec metadata (hypothesis text,
  FP modes) resolved by `detector_id`+`detector_version`.
- **UV requirements:** this page is the maximal case of Section 1; if *any*
  evidence item fails to resolve, the whole page renders as
  `SignalIntegrityError` with the raw row shown read-only for debugging.
  Spec-version drift (signal produced by v1.2, spec now at v1.4) shows a
  notice: "produced by spec v1.2 — view that version," per
  `DETECTION_PRINCIPLES.md` #6.

### 4.3 Case detail (`/cases/:id`)

- **Purpose:** the reviewer's workbench for one lead: bundled signals, notes,
  actions, audit trail, and the gateway to export.
- **Key components:** lead header (`title`, `status`, `assignee`, opened
  date); bundled `SignalCard` list (each expandable to inline signal detail);
  reviewer notes thread (each note stamped with actor + time → persisted as
  `ReviewAction` rows with `action="note"`); `DispositionForm` (Section 6);
  `AssignmentControl`; full audit-trail timeline rendered from
  `ReviewAction` (actor, action, `reason_code`, note, timestamp — read-only,
  append-only); "Generate case packet" button (gated, Section 8).
- **Data needed:** *(proposed)* `GET /cases/:id` (+ `/signals`, `/actions`);
  `POST /cases/:id/actions`; `PATCH /cases/:id` for status/assignee, which
  itself writes a `ReviewAction`. A `case_lead_signals` join table is needed
  — today nothing links `CaseLead` to `RiskSignal` (flag for
  [05-data-model.md](05-data-model.md)).
- **UV requirements:** the disposition control is disabled until the reviewer
  has opened every bundled signal's evidence at least once in this case's
  context (tracked client-side per session and recorded as a `ReviewAction`
  `action="evidence_viewed"`); tooltip explains why. The lead inherits the
  *lowest* evidence-integrity state of its signals: one unresolvable
  evidence item marks the whole lead "integrity hold — cannot disposition."

### 4.4 Network / cluster view (`/network`)

Section 7 in full. Deep-linkable: `/network?focus=vendor:123&hops=2`.

### 4.5 Export view (`/cases/:id/export`)

Section 8 in full.

---

## 5. Data-needed summary (backend work the UI implies)

Beyond the four existing endpoints: entity profile reads, signal detail with
joined evidence + spec metadata, case detail with join table + actions POST,
aggregate stats with denominators, network subgraph query
(`GET /network?focus=&hops=` returning nodes + typed edges with strength and
evidence pointers), and packet generation (`POST /cases/:id/packet`). None of
these require new *kinds* of data — every field maps to existing models plus
the two proposed additions (case↔signal join table; FP-checklist state).

---

## 6. Case queue workflow UI

### States

Aligned with `ROADMAP.md` Phase 3 and `docs/case-packet-template.md` §6:

```
new ──assign──▶ in_review ──disposition──▶ dismissed(reason_code)
                    │                  ├─▶ needs_more_data(what_data)
                    │                  └─▶ confirm_worthy ──human export──▶ escalated
                    └──unassign──▶ new
```

- `needs_more_data` returns to `in_review` when the named data arrives; the
  "what data is missing" field is structured (source + field), so it can
  drive the FOIA-planning backlog (a lawful, human-executed process).
- `escalated` is set only as a side effect of a completed packet export
  (Section 8) — the UI has no standalone "escalate" button, because
  escalation beyond the queue is a human act outside this system
  (`LEGAL_AND_ETHICAL_BOUNDARIES.md`).
- Every transition writes a `ReviewAction` row; the UI renders the timeline
  from that table only (no client-side state that isn't in the audit trail).

### Structured dismissal (`DispositionForm`)

Per `DETECTION_PRINCIPLES.md` #8, dismissals are tuning data, so free text
alone is prohibited. The form is: **reason dropdown (required) + notes
(optional) + confirm**.

Proposed starting `reason_code` vocabulary (stored on
`ReviewAction.reason_code`; extend via config, not free text):

| Code | Meaning |
|---|---|
| `fp_known_mode:<mode_id>` | Matches a declared FP mode of the detector (sub-select populated from the spec) |
| `fp_data_quality` | Underlying record wrong/duplicated at the source |
| `fp_entity_resolution` | Signal caused by a bad merge/link (also files an ER defect per Blueprint 04) |
| `explained_by_context` | Innocent explanation verified from evidence (note required) |
| `below_materiality` | Pattern real but impact too small to pursue |
| `duplicate_lead` | Same underlying facts as another lead (link required) |
| `other` | Note required; reviewed weekly to grow the vocabulary |

The dropdown for `fp_known_mode` is populated from the detector spec's FP
list — closing the loop between spec design and reviewer feedback. A
dismissal summary per detector feeds the Dashboard noise indicator (3.1).

### Assignment

`AssignmentControl`: claim (self-assign), assign-to (operator only), release.
Single assignee (`CaseLead.assignee`), matching the current model. Stale
assignments (no action in N days) surface on the Dashboard rather than
auto-unassigning — no silent state changes.

---

## 7. Network map rules (`/network`)

The network view renders `RelationshipEdge` data (typed edges:
`shared_address`, `officer_of`, `awarded_by`, `candidate_same_entity`, …)
with the semantics defined in Blueprint 04. The design goal is to make weak
inference *look* weak.

- **Weak vs strong links are visually distinct, redundantly.** Strong edges
  (registered-identifier-backed: UEI/CAGE/registry match, `awarded_by` from a
  Tier-1 record): solid line, full opacity, labeled. Weak edges (name-only
  person links, `candidate_same_entity`, single-source shared attributes):
  dashed line, reduced opacity, *and* an explicit "weak" tag on hover/tap —
  never encoded by color alone (accessibility, Section 11). Edge click opens
  a panel with the edge's method, confidence, and evidence pointer
  (`RelationshipEdge.source_document_id`); an edge with no evidence pointer
  renders as an error edge (crossed style + warning), mirroring the
  signal-integrity rule.
- **Cluster-size warnings.** When a focus expansion would pull in a cluster
  above a threshold (proposed: 25 nodes), the canvas stops and shows
  `ClusterWarningBanner`: "This address/officer connects N entities — large
  clusters usually indicate a shared-service hub, not a scheme." The user
  must explicitly expand. Per Blueprint 04, oversized clusters are a known
  ER failure mode; the UI treats them as a caution, never as a finding.
- **Registered-agent-address flags.** Addresses known or suspected to be
  registered-agent / virtual-office / mail-forwarding locations (flagged in
  ER per Blueprint 04's address-role check) render with a distinct glyph and
  the label "registered-agent address — shared addresses here are expected
  and are weak evidence." Any `shared_address` edge through such an address
  is automatically demoted to weak styling regardless of stored weight.
- **No global "risk overlay."** Nodes are not colored by risk. A node shows a
  small neutral count chip ("2 open signals") linking to its profile. A
  red-node graph is a leaderboard in disguise (Section 9).
- **Person nodes** render only with role + capacity ("registered agent of…")
  and link nowhere except the filings that name them.
- **Hops are bounded** (default 1, max 3) and the URL encodes the query so a
  reviewer's view is reproducible in the case notes.
- Implementation note: `NetworkCanvas` should be a thin wrapper over a force
  layout with a list-view fallback (`EdgeLegend` + edge table) — the table is
  the accessible and mobile-primary representation (Section 11); the canvas
  is progressive enhancement.

---

## 8. Case packet export flow (`/cases/:id/export`)

Mirrors `docs/case-packet-template.md` exactly — the export is that template
populated, nothing more. UI is a stepper (`ExportStepper`) whose steps map
1:1 to the template's six sections:

1. **Lead summary** — prefilled from the lead; the one-paragraph description
   is reviewer-written in the neutral-language editor (lint-as-you-type,
   Section 9).
2. **Hypothesis under review** — verbatim spec text + id + version;
   read-only.
3. **Evidence** — auto-populated from `EvidenceItem`s: source name + tier,
   locator, SHA-256, retrieval timestamp, quoted fields. Read-only. If any
   item fails integrity resolution, the export is blocked (not warned —
   blocked).
4. **Innocent explanations considered** — the spec's FP modes with the
   reviewer's per-mode check status; every mode must be marked
   checked / not-checked-because before proceeding.
5. **Assessment** — severity + confidence with inputs (read-only) plus the
   required "what is NOT known" free-text field.
6. **Reviewer disposition** — the recorded disposition and the recommended
   next lawful step (e.g. FOIA draft, IG referral draft) with the fixed
   reminder that execution happens by humans outside this system.

**Gates and stamps:**

- **Reviewer identity is required.** The export button is disabled until the
  authenticated reviewer confirms their name for the packet; identity is
  written into §1 and into a `ReviewAction` (`action="packet_exported"`).
  Pre-auth (before ROADMAP Phase 5), identity comes from a mandatory
  confirm-your-name step — weaker, and flagged as such in
  [09-governance-and-safety-controls.md](09-governance-and-safety-controls.md).
- **Every export is watermarked** — header and footer of every page/section:
  *"Risk signals for human review — not findings."* The watermark is applied
  server-side in packet generation (`POST /cases/:id/packet`), not by the
  client, so no client modification can omit it.
- **Language lint runs on the whole assembled packet** before generation;
  prohibited terms block export with the offending span highlighted.
- Output is markdown per `ROADMAP.md` Phase 3, stamped with generation time,
  lead id, spec versions, and the SHA-256 of the packet itself (so a packet
  circulating outside the system can be verified against the audit trail).
- Exports append to the lead's audit trail and set status `escalated`.

---

## 9. Anti-recklessness design patterns

Design decisions that make the reckless path unavailable, not merely
discouraged:

- **No red "FRAUD" badges — no red anything for subjects.** Severity and
  confidence render as neutral slate/gray chips with text labels
  (`SeverityConfidencePair`). Red is reserved for *system* errors
  (`SignalIntegrityError`, revoked sources) — i.e., red means "distrust the
  system's data," never "distrust the vendor."
- **No leaderboards.** No "top riskiest vendors," no per-entity score
  rankings, no sortable aggregate-risk column anywhere. Queues are ordered
  by triage priority (Blueprint 06) *within the signal list*, which is a
  work-ordering, not a public ranking; entity pages show counts with
  denominators only.
- **Prohibited-terms lint, three layers:**
  1. CI: a repo lint (grep-based, wordlist in `EVIDENCE_STANDARD.md` plus
     inflections) over `frontend/src` string literals and packet templates —
     fails the build.
  2. Runtime: reviewer-authored free text (notes, packet paragraphs) passes
     through the same wordlist client-side (highlight + explain) and
     server-side (reject on save).
  3. Export: whole-packet lint as the final gate (Section 8).
  The wordlist is a versioned config file so governance changes to the
  language standard propagate to all three layers from one place.
- **Innocent explanations travel with the pattern.** There is no rendering
  of a signal or edge that can suppress its FP modes below one visible line.
- **No screenshots-friendly accusation surfaces.** The page `<title>` and
  any shareable/exported view carry the disclaimer line; deep links to
  signal detail render the watermark banner at top.
- **Friction where it protects.** Disposition requires evidence opened;
  export requires FP-mode checklist; large-cluster expansion requires a
  click-through. Everywhere else the UI should be fast — friction is spent
  only on the actions that can harm a real organization.

---

## 10. Role-based access effects on the UI

Roles from `GOVERNANCE.md` (operator, reviewer) plus one proposed addition.
Note: real authentication arrives in ROADMAP Phase 5; until then the UI
implements the *shape* of these gates (role from a local config), which is a
known weakness to be recorded, not a substitute for auth.

| Capability | Viewer *(proposed role)* | Reviewer | Operator |
|---|---|---|---|
| Browse dashboard, sources, entities, signals, network | ✔ read-only | ✔ | ✔ |
| Open/attach signals to leads | — | ✔ | ✔ |
| Claim / be assigned leads; add notes | — | ✔ | ✔ |
| Disposition leads (confirm-worthy / dismiss / needs-data) | — | ✔ | ✔ |
| Generate case packet export | — | ✔ (identity stamped) | ✔ |
| Assign leads to others | — | — | ✔ |
| Approve/revoke data sources (registry actions) | — | — | ✔ (UI links to the inventory-template process; no one-click source admission) |
| Edit detector thresholds / reason-code vocabulary | — | — | ✔ (via config change process, not in-app editing in v1) |

UI effects: gated controls render disabled with a "requires reviewer role"
tooltip rather than disappearing — hidden controls make the governance model
invisible; disabled ones teach it. All read surfaces stay available to every
role because transparency of evidence is the point; what roles gate is
*action*, not *sight* (within the deployment's own user base — nothing here
is public-facing in v1).

---

## 11. Accessibility and mobile review

The operator's primary control surface is an iPhone (`CLAUDE.md`), so mobile
is a first-class review context, not a breakpoint afterthought.

**Mobile-review priorities (in order):** case queue → case detail → signal
detail evidence panel → dispositions. These four must be fully operable
one-handed on a phone:

- Single-column layouts throughout; the current 960px `Layout` container
  becomes `max-width: 960px; width: 100%` with fluid padding.
- Touch targets ≥ 44px for disposition buttons, assignment, and evidence
  links; `DispositionForm` uses native `<select>` for the reason dropdown
  (best mobile ergonomics, free accessibility).
- `SignalCard` collapses gracefully: hypothesis line, chips row, evidence
  link — no horizontal scrolling ever for core review surfaces.
- The network canvas is **not** a mobile priority; on small screens
  `/network` defaults to the edge-table representation with the same
  strength/flag semantics (7). The canvas is desktop enhancement.
- Export stepper works on mobile but is expected to be used on desktop;
  every step's state persists server-side so a review started on the phone
  finishes on a laptop.

**Accessibility requirements:**

- Never color-only encoding: severity/confidence bands carry text labels;
  weak edges are dashed *and* labeled; source tiers are numbered *and*
  named. Target WCAG 2.1 AA contrast for all chips on both backgrounds.
- All chips and badges have `aria-label`s that state both quantities in
  words ("severity high 0.82, confidence moderate 0.55") — a screen-reader
  user must get the severity-vs-confidence distinction, not one merged
  "risk" utterance.
- `SignalIntegrityError` and `ClusterWarningBanner` use `role="alert"` /
  `role="status"` appropriately.
- Full keyboard operability for the queue and forms; the network canvas gets
  a skip-link to its table equivalent.
- The audit-trail timeline is a semantic `<ol>`; evidence quotes use
  `<blockquote>` with source citation — the semantics that matter if a
  packet or page is ever consumed by assistive tech or converted to a
  document.

---

## 12. Open questions for the operator

1. Should Tier-3 (contextual) sources appear on entity profiles at all in
   v1? Policy says never the basis of a signal; showing them as "context"
   risks anchoring reviewers. Recommendation: omit from v1 UI.
2. Reason-code vocabulary (Section 6): approve the starting list or amend
   before Phase 3 implementation.
3. Cluster-warning threshold (25 nodes) and network hop cap (3): starting
   values to tune, flagging per the epistemic convention that these are
   design parameters, not measured values.
4. Viewer role: include in v1 config-based gating, or defer entirely to
   Phase 5 auth?
