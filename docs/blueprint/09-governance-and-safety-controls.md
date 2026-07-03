# 09 — Governance & Safety Controls (Deliverable K)

Operationalizes `GOVERNANCE.md`, `LEGAL_AND_ETHICAL_BOUNDARIES.md`,
`EVIDENCE_STANDARD.md`, and `DATA_SOURCE_POLICY.md` into enforceable
platform controls. This document **extends** those docs; it does not replace
them. If anything here conflicts with a root governance doc, the root doc
wins and this document must be corrected.

Everything the platform emits is a **risk signal** or **case lead** for human
review. Nothing in this document authorizes any output that states or implies
wrongdoing by any person or entity.

Scope note: roles, states, and events below are the *target* operational
model. Phase 0 code (see `backend/app/models/`) implements only fragments
(`ReviewAction`, `CaseLead.status`, `RiskSignal.status`); the build plan
(`10-build-plan.md` / `11-backlog.md`) sequences the rest. Where this doc
names a required enforcement point, it cites the module that must own it.

---

## 1. Role-based permissions matrix

Four roles. One human may hold multiple roles, but the **two-party rule**
applies: the person who authored or configured a detector may not be the sole
disposition authority on leads that detector produced (self-review bias).
Until the platform has multiple humans, the operator holds viewer + reviewer
+ admin and the two-party rule is satisfied by written rationale in
`ReviewAction.note` plus the git audit trail — an explicitly acknowledged
weakness, recorded here so it is not mistaken for a design intent.

Roles are enforced in the API layer (Phase 5 auth per `ROADMAP.md`); until
auth lands, the single-operator deployment model is the compensating control
and the platform must not be multi-tenant.

| Capability | Viewer | Reviewer | Admin | Engineering agent |
|---|---|---|---|---|
| View dashboards, base-rate context | Yes | Yes | Yes | No (no UI access) |
| View signals + full evidence chain | Yes | Yes | Yes | Read via code/tests only |
| View case leads and review queue | Yes | Yes | Yes | No |
| Triage a lead (new → triaged) | No | Yes | Yes | No |
| Take a lead in-review, disposition it | No | Yes | Yes | **Never** |
| Export a case packet | No | Yes | Yes | No |
| Approve/register a data source | No | No | Yes (human) | **Never** — may only draft the inventory entry |
| Enable/disable a detector version | No | No | Yes | May propose via PR; never activate |
| Run ingestion/detector jobs | No | No | Yes | Yes, on registered sources only, in dev/test; production runs require admin approval |
| Modify detector specs | No | No | Via reviewed change | Draft + tests via PR only |
| Manage users/roles | No | No | Yes | **Never** |
| Modify governance docs | No | No | Only on explicit operator instruction (`GOVERNANCE.md`) | **Never** (may quote, never edit) |
| Delete/redact records (per §5, §7) | No | No | Yes, logged | Only via reviewed migration/script approved by admin |
| Escalate a lead outside the system (FOIA draft, IG referral) | No | Initiates; final send is human, outside the platform | Same | **Never** |
| Access raw `data/raw/` pulls | No | Via evidence viewer only | Yes | Yes (implementation work) |
| Add non-registered data sources or scrape anything | No | No | No | **No — refuse, cite `DATA_SOURCE_POLICY.md`** |

Universal denials (no role has these):
- Publishing signals or leads to any public or third-party destination.
- Automated referral of any lead to any external body.
- Creating records about individuals outside official/registered capacity.
- Editing or deleting audit-log rows (§2 append-only rule).

---

## 2. Audit log — mandatory events and fields

`GOVERNANCE.md` requires ingestion runs, detector runs, and review actions be
recorded. The current `ReviewAction` model covers only review actions; this
section defines the full target event set. Implementation: a single
append-only `audit_events` table (proposed in `05-data-model.md`), written
from the service layer so no API path can skip it.

**Append-only invariant:** no UPDATE or DELETE on audit rows. Corrections are
new events referencing the erroneous event's id. Enforce with DB permissions
in Postgres (Phase 5); until then, by code review of `services/`.

Common required fields on every event:

| Field | Requirement |
|---|---|
| `event_id` | Unique, monotonic per deployment |
| `event_type` | From the closed enum below |
| `actor` | User id or `agent:<session-ref>`; never blank, never shared accounts |
| `actor_role` | Role exercised for the action |
| `at` | UTC timestamp |
| `object_type` / `object_id` | What was acted on (lead, signal, source, export…) |
| `payload` | Event-specific fields below (JSON) |
| `prev_event_hash` | Hash chain over prior event, so tampering is detectable (Phase 5; optional before Postgres) |

Event types and their payload minimums:

| Event | Required payload fields |
|---|---|
| `ingestion_run` | data_source_id, run parameters, records fetched/stored/rejected, SourceDocument ids + sha256s produced, terms/rate-limit compliance note, outcome (ok/partial/failed) |
| `detector_run` | detector_id, detector_version, input snapshot bounds (which SourceDocuments/date range), signals created (ids), signals suppressed by evidence gate, runtime errors |
| `signal_view` | risk_signal_id, viewer, surface (dashboard/API/export preview). Purpose: proves what a human saw before acting; also deters casual browsing of named entities |
| `lead_state_change` | case_lead_id, from_state, to_state, reason_code (required for dismiss/disposition), note |
| `disposition` | case_lead_id, disposition value, structured reason_code, innocent explanations considered (per `EVIDENCE_STANDARD.md` packet fields) |
| `export` | export_id, type (case packet/dataset/report), object ids included, redactions applied (§6), destination stated by the human, content sha256 |
| `source_registered` / `source_revoked` | data_source_id, approving admin, inventory-entry commit hash; on revoke: dependent signal ids flagged `source_revoked` |
| `entity_correction` | see §7 — dispute id, entities affected, action taken |
| `retention_deletion` | data class, object ids or count, rule applied (§5), approving admin |
| `role_change` | subject user, old/new roles, approving admin |

Retention of the audit log itself: longest of any data class it references
(§5), minimum 3 years. Deleting underlying data never deletes its audit
events — events reference deleted objects by id and hash, not content.

---

## 3. Source-citation requirements (API and UI)

Rule (from `DETECTION_PRINCIPLES.md` #5 and `EVIDENCE_STANDARD.md`):
**a signal without resolvable evidence pointers is invalid.** Operationally:

**Write path** — `services/evidence.py` is the single gate. A `RiskSignal`
may not be persisted unless it has ≥1 `EvidenceItem` whose
`source_document_id` resolves to a `SourceDocument` with a locator and (for
files) a sha256. This is a hard failure, not a warning; the detector run logs
the suppression (`detector_run.signals_suppressed`).

**API level** — every response object that carries a signal, lead, or derived
claim must embed its evidence references inline:

- `RiskSignal` serializations always include `evidence: [{evidence_item_id,
  source_document_id, locator, retrieved_at, sha256, fields_relied_on}]`.
- There is **no** API shape that returns a signal without its evidence array.
  If evidence fails to load (integrity error), the API returns the signal id
  with `status: "evidence_unresolvable"` and no hypothesis text, and logs an
  incident — it never returns the claim bare.
- Aggregates (counts, dashboards) must be decomposable: any aggregate
  endpoint offers a drill-down parameter returning the underlying signal ids.

**UI level** — *no evidence pointer, no render*:

- Every rendered signal shows a citation affordance (source name, locator
  link, retrieval date) within one interaction of the claim text.
- If the evidence array is empty or unresolvable, the UI renders a
  placeholder ("evidence unavailable — signal suppressed pending integrity
  review"), never the hypothesis.
- Quoted field values (per `EVIDENCE_STANDARD.md`, quoted not paraphrased)
  are visually distinguished from platform-generated hypothesis text.
- Tier-3 (contextual) sources render with an explicit "context only — not a
  basis for this signal" label and can never appear as the sole citation
  (`DATA_SOURCE_POLICY.md` tiers).

**Exports** — a case packet or report that would contain any claim lacking a
resolvable citation must fail to generate, with the failing item identified.

---

## 4. Review state machine

Applies to `CaseLead.status`. Current model default `"new"` is compatible.
The disposition vocabulary comes from `ROADMAP.md` Phase 3:
`confirm_worthy | dismissed | needs_more_data`.

```
                 ┌────────────┐
   (system) ───▶ │    new     │
                 └─────┬──────┘
                       │ triage (reviewer/admin)
                 ┌─────▼──────┐
        ┌────────│  triaged   │◀───────────────┐
        │        └─────┬──────┘                │
        │              │ take (reviewer/admin) │ reopen / more data arrived
        │        ┌─────▼──────┐                │
        │        │ in_review  │                │
        │        └─────┬──────┘                │
        │              │ disposition           │
        │        ┌─────▼────────────────┐      │
        └───────▶│ disposed:            │──────┘
   fast-dismiss  │  confirm_worthy      │
   (triage only, │  dismissed(reason)   │
    reason req.) │  needs_more_data     │
                 └──────────────────────┘
```

Allowed transitions and actors:

| From | To | Who | Required data |
|---|---|---|---|
| (creation) | `new` | System only (detector engine / lead assembly) | Linked signals with evidence |
| `new` | `triaged` | Reviewer, admin | Priority, optional assignee |
| `new` | `dismissed` | Reviewer, admin (fast-dismiss of clear FP) | Structured `reason_code` mandatory |
| `triaged` | `in_review` | Reviewer, admin (self-assign or assigned) | Assignee set |
| `in_review` | `confirm_worthy` | Reviewer, admin | Written rationale; innocent explanations considered; triggers §8 escalation path (human, outside system) |
| `in_review` | `dismissed` | Reviewer, admin | Structured `reason_code` (feeds threshold tuning per `DETECTION_PRINCIPLES.md` #8) |
| `in_review` | `needs_more_data` | Reviewer, admin | What data, from which lawful source, or FOIA-planning note |
| `needs_more_data` | `triaged` | Reviewer, admin (data arrived) or system (flagged when new SourceDocuments match) | Reference to new evidence |
| Any disposed | `triaged` (reopen) | Admin only | Written rationale; prior disposition preserved in history |

Hard rules:
- Every transition emits a `lead_state_change` audit event (§2). No direct
  DB edits of `status`.
- The engineering agent may create test fixtures in any state in dev/test
  databases, but may never transition production leads.
- A lead cannot reach `confirm_worthy` if any of its signals is flagged
  `source_revoked` or has unresolved evidence integrity errors.
- Dispositions never delete signals; `RiskSignal.status` mirrors the outcome
  (`open`, `dismissed`, `superseded`, `source_revoked`) but the row persists
  for tuning and audit (subject to §5 retention).

---

## 5. Retention & deletion per data class

Extends `DATA_SOURCE_POLICY.md` handling/retention rules. Baseline periods
are **operator-adjustable defaults**, not legal requirements — no statute is
claimed to mandate them (confidence: high that no single federal retention
statute governs a private analytic tool; a lawyer should confirm nothing in
the operator's jurisdiction or data-source terms imposes stricter rules).

| Data class | Where | Baseline retention | Deletion rule |
|---|---|---|---|
| Raw pulls | `data/raw/` (git-ignored) | Until normalized + verified, then deletable **if** the provenance locator allows re-retrieval (per `DATA_SOURCE_POLICY.md`); else retain while any dependent signal is open | Automated job allowed; emits `retention_deletion` event; sha256 stays on `SourceDocument` forever |
| Normalized records | DB (`data/processed/` staging) | Life of the dataset; refreshed on re-ingestion | Superseded rows replaced in place only if no evidence item points at them; otherwise versioned |
| SourceDocument rows (provenance pointers + hashes) | DB | Indefinite while referenced by any EvidenceItem or audit event | Only via §7 correction or source-terms takedown; never silent |
| Risk signals (open) | DB | While open | Not deletable; only status changes |
| Risk signals (dismissed) + dismissal reasons | DB | 3 years default — required for FP-mode tuning and for detecting re-flagging of previously cleared entities | After window: aggregate into anonymized tuning stats, then delete signal rows naming entities |
| Dismissed leads | DB | Same as dismissed signals; the structured reason outlives the entity-named row | Same |
| Case packets (exports) | Operator-controlled storage | While the escalated matter is live + 3 years default | Deletion logged with export_id; §7 flagging obligations survive via the audit log |
| Audit log | DB | ≥ longest referenced class, min 3 years | Never selectively; only whole-log archival by admin, logged |
| Person-officer records | DB | Only while the underlying public record supports the official capacity | If a person leaves the official role, the record is retained as historical fact of the public record — but no new signals may target them in that capacity after the source shows the change |
| Entity-resolution dispute records (§7) | DB | Indefinite | Never — they are the guard against repeating the error |

Principles:
- **Deletion is an audited event**, never a side effect.
- **Nothing named survives past its purpose.** Entity-named negative data
  (dismissed signals about a vendor) has a clock; anonymized tuning data
  does not.
- Source terms can shorten but never lengthen access: if a source's terms
  require deletion of redistributed data, that wins (record it in the
  source's inventory entry and act on `source_revoked`).

---

## 6. Privacy controls

Extends `LEGAL_AND_ETHICAL_BOUNDARIES.md` §Individuals vs. entities and
`DATA_SOURCE_POLICY.md` (no enrichment of private individuals).

1. **Official capacity only, enforced structurally.** `PersonOfficer` is the
   only model that may hold a natural person's name, and each row must be
   traceable (via `RelationshipEdge.source_document_id` or an evidence item)
   to a public document showing that capacity. Ingestion code that would
   write a person outside this path must be rejected in review.
2. **No enrichment.** No detector, ingestion job, or manual workflow may
   join a person to home addresses, personal social media, family members,
   or any dataset about them as a private individual — even if such data is
   technically public. "Public" is necessary but not sufficient
   (`LEGAL_AND_ETHICAL_BOUNDARIES.md`: legality is the floor).
3. **Signals target transactions and organizations.** `RiskSignal.subject_type`
   of a person-type is prohibited except where the official-capacity record
   itself is the pattern (e.g. the same registered agent across excluded
   entities), and then the hypothesis text must name the *capacity*, not
   characterize the person.
4. **Redaction rules for exports:**
   - Case packets include person names only in official capacity, with the
     citing public document adjacent to every mention.
   - Exports strip: any personal contact details that ride along in public
     records (personal phone/email fields sometimes present in registries),
     any Tier-3 material naming individuals, and any free-text reviewer note
     not explicitly marked export-safe.
   - Dataset-level exports (CSV/JSON) exclude `PersonOfficer` rows by
     default; including them requires an admin flag, logged in the `export`
     event's `redactions_applied` field.
5. **Search restraint.** The UI must not offer person-first search as a
   primary affordance; entity and transaction search are primary, and person
   lookups always display the official-capacity framing and source.
6. **Aggregation limit.** Building any profile of a person that aggregates
   across capacities/roles beyond what a single accountability question
   requires is prohibited (this is the doxxing-adjacent failure mode named
   in the boundaries doc).

---

## 7. Correction / appeal workflow (entity-resolution errors)

Entity resolution will produce wrong links (shared names, stale addresses,
UEI transcription noise). A wrong link is the platform's most harmful
failure mode because every downstream signal inherits it. The workflow:

**7.1 Intake.** Anyone — reviewer noticing a mismatch, the operator, or an
affected vendor/person contacting the operator — can open a **dispute
record**: `{dispute_id, reporter_type (internal/external), entities and
edges challenged, claimed error, supporting locators, opened_at}`. External
contacts are logged verbatim; the operator never promises an outcome, only
review.

**7.2 Freeze.** On dispute open, affected entities' signals are flagged
`under_correction_review`; any leads containing them cannot move to
`confirm_worthy`, and they are excluded from new exports until resolved.
This is automatic, not discretionary.

**7.3 Review.** A reviewer (not the person who authored the resolution rule
in question — two-party rule, §1) re-derives the link from source documents
only. Outcome is one of: `link_correct` (with written basis),
`link_incorrect`, `indeterminate` (treated as incorrect for signal purposes:
uncertain links do not support signals).

**7.4 Correction.** If incorrect/indeterminate:
- The `RelationshipEdge` / merge is reversed or split; the correction is a
  new record referencing the old (no silent rewrite of history).
- **Recompute:** every detector whose signals touched the affected entities
  is re-run over the corrected graph (`detector_run` events reference the
  dispute_id). Signals that no longer reproduce are set
  `superseded_by_correction`, never deleted (until §5 clock).
- Leads containing superseded signals return to `triaged` with a system note.

**7.5 Downstream flagging of prior exports.** From the audit log's `export`
events, identify every export whose object ids include affected signals.
For each: record a `correction_notice` linked to the export_id, and the
**operator (human)** notifies each recipient the operator sent it to, with a
correction statement. The platform prepares the notice text; a human sends
it. Case packets get an errata page on regeneration.

**7.6 Recurrence guard.** Every `link_incorrect` outcome must produce either
a normalization/resolution test case or a documented reason why not, before
the dispute closes. Dispute records are retained indefinitely (§5).

**7.7 External reply.** The operator's reply to an external disputant states:
what the platform is (risk signals for internal review, not public
accusations), what was corrected, and that no assertion of wrongdoing was
ever made or implied. No admission language beyond the factual correction.

---

## 8. Prohibited uses of the product itself

`LEGAL_AND_ETHICAL_BOUNDARIES.md` bounds inputs and language; this bounds
**what the product may be used for**. Build no feature that enables, and
refuse any request for:

1. **Public shaming feeds** — no public-facing feed, leaderboard, "wall of
   flagged vendors," social publishing, or RSS of signals/leads.
2. **Automated referrals** — no integration that transmits leads to law
   enforcement, IGs, journalists, or any third party without a human
   composing and sending each item outside the platform.
3. **Target lists** — no export or view that functions as a list of
   individuals for contact, investigation, harassment, or enforcement
   targeting. Vendor-level worklists exist only inside the review queue.
4. **Adverse-action feeds** — no use of signals as an input to automated
   decisions about anyone (payment blocking, delisting, scoring services).
   Signals are hypotheses; using them as verdicts is the accusation policy
   violated by machine. (If a signal were ever used in decisions about
   individuals — e.g. employment or credit-like contexts — consumer-reporting
   law such as the FCRA could be implicated; confidence moderate that FCRA
   applies to that misuse pattern and high that avoiding it entirely is the
   correct control. Lawyer must verify before any decisioning use is even
   discussed.)
5. **Opposition research / competitive intelligence** — the mission is
   public-spending accountability; using the graph to profile competitors,
   political opponents, or private persons is out of scope regardless of
   data legality.
6. **Circumvention staging** — the platform must not store or organize
   credentials, session tokens, or scraped-behind-auth material even if a
   user supplies them; ingestion rejects such material and the incident is
   logged.
7. **Marketing of outputs as findings** — no sales copy, README, or demo may
   describe outputs as "fraud detected." Approved language list in
   `EVIDENCE_STANDARD.md` governs all surfaces, including marketing.

Enforcement: these are checked in code review (agent must refuse per
`CLAUDE.md` rule 1–3), in the export gate (§3), and in the audit log (§2
makes misuse visible).

---

## 9. Escalation paths (what happens after `confirm_worthy`)

Per `LEGAL_AND_ETHICAL_BOUNDARIES.md`, escalation is a human decision made
**outside this system**. The platform's role ends at producing a case packet.

**Step 0 — inside the platform (last automated step):** reviewer dispositions
the lead `confirm_worthy`; the platform generates the case packet per
`docs/case-packet-template.md` and `EVIDENCE_STANDARD.md` (hypothesis,
evidence with locators, innocent explanations considered, uncertainty
language). The `export` audit event records it. Everything after this line
is human, offline, and logged only as free-text operator notes.

**Path A — FOIA / public-records request (fill an evidence gap).**
Often the right move for `needs_more_data` as well. The human drafts the
request; the platform may store the draft as a document but never sends it.
- Federal: FOIA, 5 U.S.C. § 552, provides a statutory right to request
  federal agency records; agencies have a statutory response window
  (20 business days, commonly extended in practice) and nine exemption
  categories. Confidence: **high** on the statute's existence and general
  mechanics; **moderate** on any specific agency's procedures. Verify before
  reliance: the correct agency FOIA office, current fee schedule/waiver
  practice, and exemption posture for procurement-sensitive records
  (exemption 4 issues around contractor commercial information —
  confidence moderate; lawyer should assess for the specific request).
- State/local: every US state has some public-records regime (confidence:
  **high**), but scope, fees, response deadlines, and requester-standing
  rules vary widely (confidence in any specific state's details without
  lookup: **low**). A lawyer or direct statute check is required per state
  before drafting.

**Path B — Inspector General / agency hotline referral.**
Federal agencies have Offices of Inspector General accepting public
complaints (confidence: **high**; e.g. hotlines operated by agency OIGs),
and GAO operates FraudNet for reporting concerns about federal funds
(confidence: **moderate** on current intake mechanics — verify the live
submission channel before use). Rules: the human drafts the referral from
the case packet; it transmits *observations and records*, never conclusions;
the platform is cited as the analytic method, with evidence locators, so the
recipient can verify independently. The operator owns all external
communication (`GOVERNANCE.md`).

**Path C — data-provider correction.** When the strongest explanation is a
source-data error (e.g. a mistaken exclusion record), the human reports it
to the publishing agency's correction channel. This is an escalation too:
it fixes the public record instead of acting on a bad one.

**Never paths:** direct contact with the flagged vendor's counterparties,
media distribution of leads, posting to public forums, or any contact with
named individuals. These are prohibited uses (§8).

**PACER / court-records note** (relevant when packets cite dockets): PACER
is the fee-based public access system for federal court records; usage is
governed by its user agreement and fee schedule (confidence: **high** that
fees and terms exist; **moderate** on current per-page rates and fee-waiver
thresholds — verify at time of use). CourtListener/RECAP redistributes
already-purchased documents under its own terms (confidence: **moderate**;
verify current API terms before automated retrieval). Neither may be
accessed with shared/borrowed credentials, and bulk-access must follow the
provider's stated bulk channels.

---

## 10. Control-to-enforcement map (build checklist)

| Control | Enforcement point | Phase (per `ROADMAP.md`) |
|---|---|---|
| Evidence gate (§3) | `services/evidence.py`, hard-fail | 2 |
| Review state machine (§4) | Service layer + `lead_state_change` events | 3 |
| Audit events (§2) | `audit_events` table, service-layer writes | 3 (review events), 5 (hash chain, DB perms) |
| Role enforcement (§1) | API auth middleware | 5 |
| Retention jobs (§5) | Scheduled task + `retention_deletion` events | 5 |
| Export redaction (§6) | Packet/export generator, fail-closed | 3 |
| Dispute workflow (§7) | Dispute model + freeze flag + recompute hook | post-3 |
| Prohibited-use guardrails (§8) | Code review, agent refusal, no such endpoints exist | continuous |

Until an enforcement point ships, the compensating control is the
single-operator deployment plus the git audit trail — and that gap should be
restated in each phase's release notes so it is never silently normalized.
