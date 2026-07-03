# FWA Pattern Taxonomy (Blueprint D)

Status: draft v0.1 · Feeds: `detectors/*.yml` specs, `DETECTION_PRINCIPLES.md`
Prereqs: this document extends `LEGAL_AND_ETHICAL_BOUNDARIES.md`,
`DATA_SOURCE_POLICY.md`, `EVIDENCE_STANDARD.md`, and `DETECTION_PRINCIPLES.md`.
It never overrides them.

## How to read this document

Every entry below is a **hypothesis pattern**, not an allegation category.
A pattern match is a *risk signal*: an observable data arrangement that is
*consistent with* a misuse scenario **and also** consistent with the innocent
explanations listed. Per the Evidence Standard, no signal derived from this
taxonomy may use conclusory language.

Each pattern carries:

- **ID** — stable key referenced by detector specs (`taxonomy_ref` field,
  to be added to the spec schema).
- **Definition** — the misuse scenario the pattern would represent *if*
  corroborated by human review.
- **Observable public-data signals** — concrete, computable features. Field
  names are given conceptually against our models
  (`ContractAward`, `GrantAward`, `Payment`, `ExclusionRecord`, `Vendor`,
  `Address`, `PersonOfficer`, `RelationshipEdge`) and, where relevant, against
  real public sources (USAspending/FPDS-derived fields, SAM.gov exclusions).
  Exact upstream field names **must be verified against the current
  USAspending data dictionary / SAM.gov extract layout before ingestion code
  is written** — concepts here are high-confidence, exact spellings moderate.
- **Innocent explanations / FP modes** — at least two per pattern; these are
  design inputs (Detection Principle 4).
- **Mitigation / human check** — the corroboration step that distinguishes
  the misuse scenario from the innocent ones.
- **Detector coverage** — existing spec in `detectors/`, or a plausible new
  spec name (marked *proposed*).
- **Data confidence** — an honest statement of whether public data can reveal
  the pattern at all, rated **High / Moderate / Low / Structural gap**.
  - *High*: the defining signal exists in Tier-1 public data.
  - *Moderate*: a proxy exists; the signal is suggestive, not defining.
  - *Low*: public data occasionally reveals it (jurisdiction-dependent).
  - *Structural gap*: the defining evidence (e.g., private bid documents,
    intent, bank records) is not public; we can only surface weak proxies
    and must say so in the detector spec and UI.

---

## 1. Procurement patterns

### PROC-1 · Bid rigging / bid rotation

**Definition.** A set of vendors coordinates so that a predetermined member
wins each solicitation, often taking turns across a buyer's solicitations.

**Observable public-data signals.**
- Rotation structure in the winner sequence: for a given `agency_id` and
  product/service category (NAICS code or PSC, or v0 keyword category per
  `vendor_concentration`), the same small vendor set wins in a repeating or
  near-round-robin order over time (`award.vendor_id`, `award.award_date`,
  category code).
- Stable market shares within the vendor set across periods (each member's
  share of category dollars barely moves year over year).
- Low competition indicators on the awards: USAspending/FPDS-derived
  `extent_competed` and `number_of_offers_received` (verify exact field
  names; concept high-confidence) showing few offers despite an apparently
  competitive market.
- Cross-links among the winner set from network patterns (NET-1/NET-2 below):
  shared `address.normalized`, overlapping `PersonOfficer` records.

**Innocent explanations / FP modes.**
1. Thin markets: only 2–4 qualified vendors exist for the category or region,
   so alternation is natural.
2. IDIQ/BPA task-order allocation or small-business set-aside pools that
   deliberately distribute work among pre-qualified holders.
3. Capacity cycling: small firms decline work when at capacity, producing
   alternation without coordination.
4. Category misclassification making unrelated awards look like one market.

**Mitigation / human check.** Reviewer verifies market breadth (how many
vendors *ever* won or registered in this category/region), checks whether
awards sit under a multiple-award vehicle, and — where the jurisdiction
publishes them — pulls bid tabulations to compare losing bids. Signals should
never escalate on rotation shape alone; require at least one independent
corroborating link (network edge or competition anomaly).

**Detector coverage.** Partially: `vendor_concentration` (steering side),
`shared_address_cluster` (coordination side). *Proposed:*
`winner_rotation` — sequence analysis over (agency, category) winner series.

**Data confidence: Structural gap, with Moderate proxies.** True bid rigging
is proven with bid-level data (all bids, amounts, bidder identities) and
communications evidence. USAspending/FPDS record **winners only**, plus an
offer count; losing-bid data exists only on some state/local portals that
publish bid tabulations. Be explicit in any `winner_rotation` spec that the
detector surfaces *rotation-shaped award histories*, which is a weak proxy.

---

### PROC-2 · Complementary (cover) bidding

**Definition.** Co-conspiring vendors submit intentionally losing bids
(too high, or with disqualifying terms) to create the appearance of
competition around a designated winner.

**Observable public-data signals.**
- Where bid tabulations are published (some state/local portals): losing bids
  clustered at a near-constant percentage above the winning bid across many
  solicitations; identical line-item errors or round-number losing bids.
- In federal data (no losing bids): `number_of_offers_received` consistently
  small and constant (e.g., always exactly 3) for a (agency, category) pair,
  combined with the same winner — a weak proxy.
- Network links (NET-1/NET-2) among the apparent competitors.

**Innocent explanations / FP modes.**
1. Standard markup conventions in an industry produce naturally similar
   spreads between bidders.
2. Agencies soliciting a fixed shortlist (e.g., three quotes required by
   policy) mechanically produce constant offer counts.
3. Subcontracting relationships: a "losing" bidder later works for the winner
   lawfully and disclosed.

**Mitigation / human check.** Requires bid-tabulation documents; reviewer
inspects actual losing-bid amounts and bidder identities, checks corporate
registry for relationships among bidders, and confirms the quote-count policy
of the buyer. Without bid-level data this pattern must not generate signals
above low confidence.

**Detector coverage.** None existing. *Proposed:* `cover_bid_spread`
(only enabled for sources providing bid tabulations; source-gated per
`DATA_SOURCE_POLICY.md`).

**Data confidence: Structural gap federally; Low–Moderate where bid
tabulations are public.** Do not build the detector until a registered
Tier-1/Tier-2 source with bid-level data exists.

---

### PROC-3 · Contract splitting (threshold avoidance)

**Definition.** One requirement is divided into multiple smaller awards or
purchases so each stays under a competition, approval, or micro-purchase
threshold.

**Observable public-data signals.**
- ≥2 awards from one `agency_id` to one `vendor_id` within a short window
  (`award.award_date` spread ≤ 30 days in the current spec), each amount
  within a band just below a configured threshold (`config.thresholds`), with
  combined amount exceeding it — exactly as specified in
  `detectors/split_purchase.yml`.
- Similar or overlapping `award.description` text among the set.
- Amount distributions for an agency showing a spike ("bunching") just below
  known thresholds — a population-level companion signal.
- Sequential or near-sequential award identifiers (`award.award_id`) issued
  the same day (portal-dependent; verify identifier semantics per source).

**Innocent explanations / FP modes.**
1. Genuinely distinct needs that price near a common threshold (thresholds
   sit near natural price points for many goods).
2. BPAs/blanket orders with lawful frequent small calls.
3. Wrong threshold assumption for that jurisdiction, agency class, or fiscal
   year — thresholds change and vary; the spec already flags this.
4. Card-purchase consolidation artifacts in checkbook data (many small
   transactions posted together).

**Mitigation / human check.** Per `split_purchase.yml`: verify the applicable
threshold and period, read descriptions for distinct scope, check whether a
competed vehicle covered the need. Maintain thresholds as versioned config
with source citations, never hardcoded.

**Detector coverage.** `split_purchase` (existing). *Proposed companion:*
`threshold_bunching` — distributional test per agency, which is more robust
to description noise but needs a base-rate display (Detection Principle 7).

**Data confidence: High.** Award amounts, dates, and parties are core public
fields. The main verification burden is threshold correctness, not data
availability.

---

### PROC-4 · Sole-source abuse

**Definition.** Non-competitive awards are used where competition was
feasible, to direct work to a preferred vendor.

**Observable public-data signals.**
- Competition fields on federal awards: `extent_competed` = not competed
  codes, `other_than_full_and_open_competition` reason codes,
  `solicitation_procedures`, `number_of_offers_received` = 1 (concepts
  high-confidence in FPDS/USAspending; verify exact code lists).
- A vendor or (agency, vendor) pair whose share of dollars via
  non-competed actions is far above peer baseline.
- Repeated use of the same justification code across many awards to one
  vendor, especially "urgency" used serially over years.
- Escalating award sizes to the same vendor with competition indicators
  absent throughout.

**Innocent explanations / FP modes.**
1. Lawful sole-source categories: genuine single supplier, patented/
   proprietary items, mandated sources, national-security carve-outs.
2. Follow-on awards where switching vendors carries real technical risk
   (logically sole-source, documented in a public J&A).
3. Set-aside programs (e.g., certain 8(a) directed awards are lawful
   non-competed actions by design — verify program rules before flagging).
4. Data-entry defaults: competition fields are notoriously unevenly coded;
   a missing code is not a non-competed award.

**Mitigation / human check.** Reviewer looks for the published Justification
& Approval or equivalent public record, verifies the code against the actual
award context, and compares against peer agencies buying the same category.
Missing/placeholder competition codes must reduce, not raise, confidence.

**Detector coverage.** Partially: `vendor_concentration` (its
`competition_indicator_availability` confidence input anticipates this).
*Proposed:* `noncompete_share` — explicit rate-of-non-competed-dollars test
per (agency, vendor) and per vendor, with justification-code breakdown.

**Data confidence: Moderate–High federally** (codes exist but are unevenly
populated and require careful code-list mapping); **Low at many state/local
portals** which often omit competition method entirely.

---

### PROC-5 · Spec-tailoring / vendor favoritism

**Definition.** Requirements or evaluation criteria are written so only a
favored vendor can win, producing competition in form but not substance.

**Observable public-data signals.**
- "Competed but one offer": awards coded as competitive with
  `number_of_offers_received` = 1, repeatedly, for the same
  (agency, vendor) — the most computable public proxy.
- Very short solicitation-open windows where solicitation dates are public
  (federal opportunities data provides posting and response dates; verify
  availability and joinability to awards before relying on it — moderate
  confidence).
- Incumbent lock-in shape: same vendor wins the recompete every cycle with
  one offer each time.
- High agency-category concentration (`vendor_concentration`) combined with
  nominally competitive coding.

**Innocent explanations / FP modes.**
1. Legitimately specialized requirements where only one vendor is qualified
   and everyone in the market knows it (single offer despite honest specs).
2. Incumbent advantage without tailoring: transition costs deter challengers.
3. Small solicitations that competitors rationally ignore.
4. Amended/extended solicitations that reset response windows in ways the
   data snapshot misses.

**Mitigation / human check.** Reviewer reads the actual solicitation text
(public on opportunity portals) for brand-name-or-equal abuse, unusually
specific requirements, or evaluation criteria matching one vendor's public
capabilities; checks protest history where public. Signal language must stay
at "competition outcome inconsistent with market breadth."

**Detector coverage.** Partially: `vendor_concentration`. *Proposed:*
`competed_single_offer` — repeated (competitive-code, offers=1) awards per
(agency, vendor).

**Data confidence: Moderate.** The *outcome* (single-offer competition) is
public and computable; the *mechanism* (tailored spec text) requires human
document reading. Detectors surface the outcome only.

---

### PROC-6 · Change-order / modification abuse

**Definition.** A contract is won with a low bid, then grown substantially
through modifications, evading the competition that the true scope would
have required ("low-ball and grow").

**Observable public-data signals.**
- Federal award data includes modification records: `modification_number`,
  action obligation amounts per transaction, `base_and_all_options_value`
  vs. cumulative obligations (concepts high-confidence; verify exact fields
  and how the chosen ingestion endpoint rolls up transactions).
- Computable ratio: cumulative modified value ÷ initial award value, flagged
  above a percentile among comparable contracts.
- Timing: large upward modification shortly after award (scope was arguably
  known at bid time).
- Repetition: the same (agency, vendor) pair showing high growth ratios
  across multiple contracts.

**Innocent explanations / FP modes.**
1. Lawful option-year exercises and incremental funding actions that look
   like growth but were in the original ceiling.
2. Genuine requirement changes (site conditions, regulation changes,
   emergencies).
3. Administrative modifications (novations, PoP extensions, funding source
   changes) with little competitive significance.
4. Transaction-rollup errors: mistaking de-obligations/corrections for
   growth.

**Mitigation / human check.** Reviewer separates option exercises and
funding mods from scope mods (action-type codes exist federally; verify code
list), compares final value to the original *ceiling* not just the initial
obligation, and checks the modification descriptions. Note: our current
`ContractAward` model has no modification/ceiling fields — this pattern
requires a schema extension (e.g., `ContractModification` child table or
`initial_amount` / `current_total` columns) before a detector is feasible.

**Detector coverage.** None existing. *Proposed:* `modification_growth`
(blocked on modification-level ingestion).

**Data confidence: Moderate–High federally** (modification transactions are
public but rollup is error-prone); **Low at most state/local portals**, which
frequently publish only final or current values.

---

## 2. Vendor integrity patterns

### VEND-1 · Shell-vendor indicators

**Definition.** A vendor exists primarily on paper — minimal operations,
staff, or history — inconsistent with the size or nature of the awards it
receives.

**Observable public-data signals.**
- Registration age vs. first award: corporate-registry incorporation date or
  SAM registration date shortly before a large award (registry dates are
  Tier-2 per `DATA_SOURCE_POLICY.md`; SAM registration date availability in
  public extracts must be verified — moderate confidence).
- Address type: `address.normalized` resolving to residential, virtual-office,
  or registered-agent addresses (requires the agent/coworking allowlist
  already anticipated by `shared_address_cluster`).
- Breadth anomaly: awards across many unrelated NAICS codes for a young
  vendor with no visible specialization.
- Single-customer dependence: all of a vendor's public awards come from one
  agency (computable from `award.agency_id` distribution).
- Missing web/registry footprint — **context only (Tier 3), never a signal
  basis on its own** per `DATA_SOURCE_POLICY.md`.

**Innocent explanations / FP modes.**
1. Legitimate startups and small home-based businesses — very common,
   especially among small-business set-aside awardees; a residential address
   is normal for them.
2. Holding-company or SPV structures used lawfully for a single project
   (common in construction/energy).
3. Recent lawful restructuring (new entity, continuing business).
4. Registry data staleness or bad address normalization.

**Mitigation / human check.** Reviewer pulls the corporate registry record
(officers, filing history), checks whether the award's set-aside type
explains the profile, and looks for a disclosed parent. Because the base
rate of innocent matches is high, VEND-1 should act mainly as a *confidence
booster on other signals*, not a standalone lead generator.

**Detector coverage.** Partially: `shared_address_cluster`. *Proposed:*
`young_vendor_large_award` (registration-to-award gap × amount percentile),
explicitly weighted low.

**Data confidence: Moderate.** Each indicator is individually weak and
public; the composite is only suggestive. State registry coverage and API
access vary widely — inventory each registry before ingestion.

---

### VEND-2 · Excluded-party participation

**Definition.** An award or payment goes to a party during an active
suspension/debarment window, directly or via name/identifier variation.

**Observable public-data signals.**
- Exactly as specced in `detectors/debarred_vendor_match.yml`: `vendor.uei`
  vs `exclusion.uei` (high confidence), or `vendor.normalized_name` +
  postal-code agreement (medium), with `award.award_date` inside
  [`exclusion.active_from`, `exclusion.active_to`].
- SAM.gov exclusion records carry classification/exclusion-type and CAGE
  codes usable to strengthen matches (verify extract layout; high confidence
  the fields exist).

**Innocent explanations / FP modes.**
1. Name collision with an unrelated entity (the spec's `name_commonality`
   input).
2. Stale snapshot: exclusion rescinded/lapsed after our ingest.
3. Lawful successor entity post-resolution.
4. Exclusions scoped to specific programs/agencies that don't cover the
   flagged award (exclusion scope varies — verify classification semantics).

**Mitigation / human check.** Reviewer re-checks the live authoritative
record, verifies identifiers, and confirms exclusion scope covers the awarding
program, per the existing spec's `validation_approach`.

**Detector coverage.** `debarred_vendor_match` (existing; Phase-2 build
target per `ROADMAP.md`).

**Data confidence: High.** This is the strongest pattern in the taxonomy:
both sides of the join are Tier-1 public data with official identifiers.

---

### VEND-3 · Pass-through / front arrangements

**Definition.** A qualifying entity (e.g., set-aside-eligible firm) wins the
award but the work substantially flows to another firm; the awardee takes a
margin for eligibility, not performance.

**Observable public-data signals.**
- Federal subaward reporting (FFATA/FSRS-derived, published via
  USAspending): subaward amount ÷ prime award amount near 1.0
  (high confidence the dataset exists; known to be under-reported — treat
  missing subawards as unknown, not clean).
- Same-day or near-simultaneous prime and subaward dates.
- Network edges (NET-1/NET-2) between prime and sub: shared address,
  shared officers, prime formerly an officer of the sub or vice versa.
- Prime's award history shows no performance in that NAICS before or after.

**Innocent explanations / FP modes.**
1. Lawful teaming and mentor-protégé arrangements that are disclosed and
   compliant with applicable subcontracting-limit rules.
2. Prime performing management/integration functions whose value isn't
   visible in dollar ratios.
3. Subaward data quality: duplicates, mis-keyed amounts, or reporting
   covering only part of the prime award.

**Mitigation / human check.** Reviewer verifies the applicable
performance/subcontracting-limit rule for that program and year (rules vary
— verify before citing any percentage), checks disclosed teaming
relationships, and reads award descriptions for the prime's stated role.

**Detector coverage.** None existing. *Proposed:* `subaward_passthrough`
(requires subaward ingestion — schema currently lacks a Subaward model;
extension needed).

**Data confidence: Moderate federally** (subaward data exists but is
incomplete); **Low elsewhere** — most state/local portals publish no
subaward data.

---

### VEND-4 · Rotating principals

**Definition.** The same individuals reappear as officers/agents across a
succession of vendor entities — including successors to troubled or excluded
firms — obscuring continuity of control.

**Observable public-data signals.**
- `PersonOfficer.name` (normalized) linked to ≥2 `vendor_id`s via
  `RelationshipEdge(relation="officer_of")`, where the vendors' award
  histories are sequential rather than overlapping (entity B's awards begin
  as entity A's end).
- Entity A appears in `ExclusionRecord` or stops winning; entity B with an
  overlapping officer and/or shared `address` begins winning from the same
  `agency_id` shortly after.
- Corporate registry filings showing officer succession (Tier 2).

**Innocent explanations / FP modes.**
1. Serial entrepreneurs lawfully running successive or parallel businesses —
   extremely common.
2. Professional directors, registered agents, or incorporators listed on
   many unrelated entities as a service.
3. Name collisions between distinct individuals (we have no personal
   identifiers beyond names in official capacities, by policy — see
   `LEGAL_AND_ETHICAL_BOUNDARIES.md` "Individuals vs. entities").
4. Disclosed corporate reorganizations/novations.

**Mitigation / human check.** Reviewer confirms the officer link in primary
registry documents (not just our normalization), checks for a professional-
agent role, and requires the succession-timing element plus one more link
(address, exclusion adjacency) before escalation. Analysis must stay framed
on **entity continuity**, with individuals referenced only in their
registered capacities.

**Detector coverage.** None existing; `shared_address_cluster`'s
`overlap_of_officers` confidence input is a hook. *Proposed:*
`principal_succession` — officer-linked vendor pairs with sequential award
histories, weighted up if the earlier entity intersects `ExclusionRecord`.

**Data confidence: Low–Moderate.** Officer data quality varies enormously by
state registry; name-only person matching is inherently noisy. Confidence
scoring must penalize common names heavily (mirror
`debarred_vendor_match.name_commonality`).

---

## 3. Payment patterns

### PAY-1 · Duplicate payments

**Definition.** The same obligation is paid more than once (error or abuse).

**Observable public-data signals.** As specced in
`detectors/duplicate_payment.yml`: grouping by (`payment.vendor_id`,
`payment.amount`), invoice-number match quality (exact > normalized >
amount-only), `paid_date` proximity ≤ 90 days, same `agency_id`.

**Innocent explanations / FP modes.** (from the spec)
1. Legitimate recurring charges (rent, subscriptions).
2. Progress payments reusing an invoice prefix.
3. Credit-and-rebill corrections.

**Mitigation / human check.** Per spec: pull both payment records, check
contract terms for recurrence, look for a reversal/credit in-period.

**Detector coverage.** `duplicate_payment` (existing; Phase-2 build target).

**Data confidence: Moderate — jurisdiction-dependent.** Payment-level data
with invoice numbers is common in state/local "checkbook" portals but
**federal spending data is award/obligation-level; USAspending does not
publish invoice-level disbursements** (high confidence). This detector's
scope is therefore checkbook-style sources and operator-provided data.

---

### PAY-2 · Split invoices

**Definition.** One deliverable is billed as multiple smaller invoices to
stay under payment-approval limits (the invoice-side sibling of PROC-3).

**Observable public-data signals.**
- Multiple `Payment` rows to one `vendor_id` from one `agency_id` on the same
  or adjacent `paid_date`s, each below a payment-approval limit
  (`config.thresholds` analog), with sequential or patterned
  `invoice_number`s (e.g., `1001-A`, `1001-B`).
- Combined same-day payments to a vendor exceeding the limit that any single
  payment respects.

**Innocent explanations / FP modes.**
1. Line-of-business billing conventions: one project lawfully billed per
   task, site, or funding line.
2. Funding-source splits required by accounting (one deliverable charged to
   two appropriations), which *must* appear as separate payments.
3. Batch payment runs posting many distinct invoices the same day.

**Mitigation / human check.** Reviewer inspects invoice numbering and
descriptions, and verifies the agency's payment-approval limit actually
exists at the assumed level (as with PROC-3, thresholds are the fragile
assumption).

**Detector coverage.** None existing; `split_purchase` logic generalizes.
*Proposed:* `split_invoice` — same engine pattern over `Payment` instead of
`ContractAward`.

**Data confidence: Moderate**, same caveat as PAY-1: requires invoice-level
public data, which is portal-dependent.

---

### PAY-3 · Round-number / impossible billing

**Definition.** Billed amounts or quantities are implausible on their face —
uniform round numbers inconsistent with metered services, or quantities
exceeding physical possibility (e.g., more service-hours than exist in the
period).

**Observable public-data signals.**
- Round-amount rate: share of a vendor's `payment.amount` values that are
  exact multiples of 100/1,000 compared against the population base rate for
  that payment category (population comparison is mandatory — Detection
  Principle 7).
- Digit-distribution outliers per vendor (e.g., first/last-digit frequencies
  far from the payment population's empirical distribution; note that many
  legitimate price ledgers do not follow theoretical digit laws — calibrate
  against observed base rates, not textbook curves).
- Impossibility checks where unit data exists: hours billed per period
  exceeding calendar hours, quantities exceeding contract ceilings
  (requires line-item quantity fields most portals lack — verify per source).

**Innocent explanations / FP modes.**
1. Fixed-price contracts and grants legitimately produce round amounts.
2. Retainers, milestone payments, and budget-capped payments are round by
   design.
3. Rounding introduced by the portal's own data processing.
4. Statistical outliers guaranteed by testing many vendors (multiple-
   comparison effect) — thresholds must be corrected for the number of
   vendors tested.

**Mitigation / human check.** Reviewer checks contract pricing type
(fixed-price vs. time-and-materials — competition/pricing-type codes exist
federally; verify), and treats digit-based statistics as triage ordering
only, never a standalone lead (consistent with Detection Principle 1's
stance on scoring).

**Detector coverage.** None existing. *Proposed:* `implausible_billing`
(impossibility subchecks only where unit fields exist; digit statistics as
a triage feature, severity capped).

**Data confidence: Low–Moderate.** Round-number statistics are computable
anywhere amounts exist but have weak evidential value; true impossibility
checks need line-item detail that is a structural gap in most public data.

---

### PAY-4 · Ghost vendors

**Definition.** Payments flow to an entity with no verifiable existence or
no plausible capacity to have delivered — a fabricated or hijacked payee.

**Observable public-data signals.**
- `Payment` rows whose `vendor_id` has **no** corresponding award
  (`payment.contract_award_id` null and no joinable `ContractAward`) — payee
  never visibly procured from.
- Vendor absent from corporate registry and from SAM/registration data at
  payment time (absence-of-record signals are weak: registry coverage gaps
  produce the same observation — treat as unknown-vs-absent explicitly).
- Vendor address failing validation or matching an agency employee-adjacent
  address — **caution:** matching against employee home addresses is off
  the table (privacy boundary); only official-capacity address overlaps
  (e.g., vendor address equals an agency facility) are in scope.
- Payments begin and end abruptly with no award, no registry footprint, and
  round amounts (composite with PAY-3).

**Innocent explanations / FP modes.**
1. Refunds, grants to individuals-as-classes, utility payments, inter-
   governmental transfers, and other non-procurement disbursements that
   legitimately lack awards.
2. Entity-resolution failure on our side: the vendor exists but under a name
   variant we failed to normalize.
3. Registry lag for newly formed legitimate businesses.

**Mitigation / human check.** Reviewer first rules out payment-type
categories that don't require awards (payment/object codes where the portal
provides them — verify per source), then attempts registry lookup manually
before treating non-existence as corroborated.

**Detector coverage.** None existing. *Proposed:* `unmatched_payee` —
payments-without-awards joined against registry presence, heavily gated on
payment-type classification quality.

**Data confidence: Low–Moderate.** The pattern is definable in checkbook
data, but the innocent base rate (non-procurement disbursements) is very
high; without payment-type codes this detector would drown reviewers.

---

## 4. Grant patterns

### GRANT-1 · Grant misuse indicators

**Definition.** Grant funds are spent outside the awarded purpose or by a
recipient whose profile is inconsistent with the program.

**Observable public-data signals.**
- Recipient-side anomalies computable from `GrantAward`: a recipient winning
  grants across unrelated assistance programs (federal assistance listing /
  CFDA numbers — high confidence these exist in USAspending assistance data;
  verify current field naming), sudden award-size jumps, or first-time
  recipients of unusually large awards.
- Cross-domain composite: grant recipient shares address/officers with
  vendors in the same agency's procurement pool (NET-1/NET-2).
- Recipient appears in `ExclusionRecord` (exclusions cover assistance
  programs too — verify scope semantics; VEND-2 logic applies directly).
- Audit-flag adjacency: recipients over federal single-audit spending
  thresholds with public audit findings (the Federal Audit Clearinghouse
  publishes single-audit data — moderate confidence on access mechanics;
  verify current hosting and API before registering the source).

**Innocent explanations / FP modes.**
1. Diversified nonprofits legitimately holding many unrelated grants.
2. Program expansions and emergency supplementals producing sudden size
   jumps for established recipients.
3. Fiscal-sponsor arrangements where one entity lawfully receives on behalf
   of many small organizations.

**Mitigation / human check.** How funds were *actually spent* is a
structural gap — public data shows awards, not expenditures. Reviewer relies
on published audit findings, program reports where public, and otherwise
marks leads `needs-data` (possibly FOIA planning, which is in scope).

**Detector coverage.** `debarred_vendor_match` extends naturally to
`GrantAward`. *Proposed:* `grant_recipient_profile` (weak, triage-only).

**Data confidence: Low for misuse itself (structural gap — expenditures are
not public); Moderate for recipient-profile and exclusion-overlap proxies.**
Detector specs must state plainly that they flag award-side anomalies, not
spending behavior.

---

### GRANT-2 · Subaward pass-through anomalies

**Definition.** Grant funds are passed through one or more intermediaries
that add margin but little function, or flow to subrecipients related to the
prime.

**Observable public-data signals.**
- Subaward ÷ prime ratios near 1.0 in federal subaward data (same dataset
  and caveats as VEND-3).
- Chains: subrecipient of grant A is prime of grant B with overlapping
  parties (requires subaward ingestion into `RelationshipEdge`).
- Relatedness: prime and subrecipient share `address.normalized` or
  `PersonOfficer` links.
- Many small subawards each just under the federal subaward reporting
  threshold (a bunching test; the threshold value must be verified for the
  period before use — it has changed over time).

**Innocent explanations / FP modes.**
1. Designed pass-through programs: states and umbrella nonprofits are
   *supposed* to re-grant most funds (block grants, fiscal sponsors) —
   ratio-near-1.0 is the intended shape, making the base rate of innocent
   matches very high.
2. Administrative-cost caps that legitimately force the prime's retained
   share to look thin.
3. Under-reporting: missing subaward records make partial chains look like
   anomalies.

**Mitigation / human check.** Reviewer identifies the program's design
(pass-through by statute?) before anything else; relatedness links, not
ratios, should drive escalation.

**Detector coverage.** None existing. *Proposed:* `subaward_passthrough`
shared with VEND-3, with a program-type allowlist to suppress designed
pass-throughs.

**Data confidence: Moderate federally, with severe under-reporting; Low
elsewhere.**

---

## 5. Conflict-of-interest patterns

Scope constraint (restating the boundary, not weakening it): COI analysis
uses **public disclosures and official-capacity records only** — public
financial-disclosure filings where published, corporate registry officer
lists, and procurement records naming officials in their official roles.
No tracking of private individuals, no enrichment beyond the public record
(`LEGAL_AND_ETHICAL_BOUNDARIES.md`).

### COI-1 · Official–vendor relationship recorded in public disclosures

**Definition.** A person appears both in an official capacity at a buying
agency (`PersonOfficer` with `agency_id`) and in a registered capacity at a
vendor receiving that agency's awards (`PersonOfficer` with `vendor_id`), or
a published financial-disclosure filing records an official's interest in a
vendor with awards from their agency.

**Observable public-data signals.**
- Same normalized `PersonOfficer.name` linked to both an `agency_id` and a
  `vendor_id` where that vendor has `ContractAward`/`GrantAward` rows from
  that agency — directly computable from existing models.
- Timing overlap: awards dated during the person's tenure in both roles
  (requires role start/end dates our `PersonOfficer` model currently lacks —
  schema extension needed; without dates, confidence must be capped).
- Disclosure-based edges: senior federal officials' public financial
  disclosures (OGE Form 278e is public for covered officials — high
  confidence the filing type exists; access mechanics and machine-readability
  must be verified; state/local disclosure regimes vary from robust portals
  to paper-only — inventory per jurisdiction).
- Post-employment ("revolving door") shape: an official's name appears at a
  vendor shortly after leaving the agency, and the vendor's awards from that
  agency rise — timing data caveat as above.

**Innocent explanations / FP modes.**
1. Name collision between distinct individuals — the dominant FP mode; we
   deliberately hold no discriminating personal data, so common names must
   score near zero.
2. Disclosed and recused interests: disclosure of an interest is the system
   *working*; the filing itself is not an anomaly.
3. Lawful post-employment moves outside any cooling-off restriction, or in
   roles not touching their former agency.
4. Stale registry data listing a person who has resigned.

**Mitigation / human check.** Reviewer verifies identity through primary
documents (does the registry filing and the agency record plausibly describe
the same person in official capacities?), checks whether the interest was
disclosed/recused where records are public, and confirms tenure dates.
Language rule is strictest here: output must read "public records list the
same name in both capacities — identity and propriety unverified," and the
case packet must carry the name-collision FP mode prominently.

**Detector coverage.** None existing. *Proposed:* `dual_capacity_overlap` —
`PersonOfficer` self-join across agency/vendor roles gated by award linkage,
with `name_commonality` as a dominant confidence input.

**Data confidence: Low–Moderate.** The join is computable today, but
name-only matching plus missing tenure dates makes standalone confidence
inherently low. Disclosure-filing ingestion is jurisdiction-by-jurisdiction
work; verify each source against `DATA_SOURCE_POLICY.md` admission criteria
before building.

---

## 6. Network patterns

### NET-1 · Shared addresses / officers / registered agents

**Definition.** Nominally independent vendors are linked through shared
physical addresses, overlapping officers, or a common controlling structure —
the substrate under PROC-1/2, VEND-1/3/4.

**Observable public-data signals.** As specced in
`detectors/shared_address_cluster.yml`: vendors grouped by
`address.normalized` (agent/coworking allowlist applied), clusters of ≥2
vendors with awards from the same `agency_id` within 24 months;
strengthened by `overlap_of_officers` via `PersonOfficer` and
`RelationshipEdge(relation="shared_address" | "officer_of")`.

**Innocent explanations / FP modes.** (from the spec, plus one)
1. Registered-agent and virtual-office addresses hosting unrelated firms —
   the single largest FP source; the allowlist is load-bearing and must be
   maintained as data, not code.
2. Incubators/coworking spaces.
3. Disclosed corporate families (parent/subsidiary).
4. Address-normalization collisions (suite-number loss merging distinct
   tenants).

**Mitigation / human check.** Per the spec: allowlist check, registry pull
for disclosed affiliation, officer-overlap confirmation in primary filings.
Suite-level normalization quality should be a confidence input.

**Detector coverage.** `shared_address_cluster` (existing).

**Data confidence: Moderate–High for the *link*; Low for what the link
means.** Addresses and officers are public; independence-vs-coordination is
not observable in data and always requires the human step.

---

### NET-2 · Rotating winners within a buyer's vendor pool

**Definition.** Within one buyer's recurring purchases, awards cycle among a
closed, interlinked vendor set — the network-level view of PROC-1, and the
composite pattern with the best public detectability among collusion shapes.

**Observable public-data signals.**
- Closed-set property: over N periods, ≥K awards in a (agency, category)
  stream go to a fixed set of vendors with no entrants
  (`award.vendor_id` set stability over `award.award_date` windows).
- Alternation: winner-sequence entropy or turn-taking statistics within the
  set (computable; must be benchmarked against thin-market nulls).
- Interlinkage: NET-1 edges among the set members (shared address, officers).
- Competition proxies: constant low `number_of_offers_received` across the
  stream (where federal; absent at most state/local portals).
- Split-purchase adjacency: PROC-3 signals inside the same
  (agency, vendor-set).

**Innocent explanations / FP modes.**
1. Thin regional markets — small towns often have exactly three plumbing
   contractors; rotation is what honesty also looks like there.
2. Deliberate award distribution policies (rotating quotes among small
   businesses is *encouraged* in some jurisdictions' purchasing manuals —
   verify the buyer's policy before flagging).
3. Multiple-award vehicles allocating task orders by design.
4. Seasonal/capacity effects producing alternation.

**Mitigation / human check.** Reviewer establishes market breadth (how many
plausible vendors exist), checks the buyer's published purchasing policy for
lawful rotation practices, and requires interlinkage (NET-1) between set
members before treating rotation as suspect. Rotation + independence-links
together are reviewable; rotation alone is not.

**Detector coverage.** Composite of `shared_address_cluster` +
`vendor_concentration` + `split_purchase`. *Proposed:* `winner_rotation`
(shared with PROC-1) consuming NET-1 edges as confidence inputs.

**Data confidence: Moderate.** Every ingredient is public
(winners, dates, amounts, addresses, officers); the ceiling is that
coordination itself is never in the data. This is the honest upper bound for
collusion detection on award-level public data.

---

## Coverage matrix

| Pattern | Existing detector | Proposed detector | Public detectability |
|---|---|---|---|
| PROC-1 bid rotation | partial: `vendor_concentration`, `shared_address_cluster` | `winner_rotation` | Structural gap; moderate proxies |
| PROC-2 complementary bidding | — | `cover_bid_spread` (source-gated) | Gap federally; low–mod with bid tabs |
| PROC-3 contract splitting | `split_purchase` | `threshold_bunching` | High |
| PROC-4 sole-source abuse | partial: `vendor_concentration` | `noncompete_share` | Moderate–high (federal) |
| PROC-5 spec-tailoring | partial: `vendor_concentration` | `competed_single_offer` | Moderate (outcome only) |
| PROC-6 change-order abuse | — | `modification_growth` (schema ext.) | Moderate–high (federal) |
| VEND-1 shell indicators | partial: `shared_address_cluster` | `young_vendor_large_award` | Moderate (weak composite) |
| VEND-2 excluded party | `debarred_vendor_match` | — | High |
| VEND-3 pass-through | — | `subaward_passthrough` (schema ext.) | Moderate (federal only) |
| VEND-4 rotating principals | — | `principal_succession` | Low–moderate |
| PAY-1 duplicate payments | `duplicate_payment` | — | Moderate (checkbook sources) |
| PAY-2 split invoices | — | `split_invoice` | Moderate (checkbook sources) |
| PAY-3 implausible billing | — | `implausible_billing` (triage-only) | Low–moderate |
| PAY-4 ghost vendors | — | `unmatched_payee` (gated) | Low–moderate |
| GRANT-1 grant misuse | partial: `debarred_vendor_match` on grants | `grant_recipient_profile` | Low (gap on spending) |
| GRANT-2 subaward anomalies | — | `subaward_passthrough` | Moderate (federal) |
| COI-1 dual capacity | — | `dual_capacity_overlap` | Low–moderate |
| NET-1 shared links | `shared_address_cluster` | — | Mod–high (link), low (meaning) |
| NET-2 rotating pool | composite of three existing | `winner_rotation` | Moderate |

## Implementation notes for detector authors

1. **Every new spec must reference its pattern ID** (add `taxonomy_ref` to
   the spec schema) and inherit at minimum the FP modes listed here.
2. **Schema extensions required before some detectors are honest:**
   contract modifications (PROC-6), subawards (VEND-3/GRANT-2), tenure dates
   on `PersonOfficer` (COI-1), payment/object type codes (PAY-4).
3. **Threshold and rule values are data, not constants.** PROC-3, PAY-2,
   VEND-3, and GRANT-2 all depend on jurisdiction- and period-specific
   thresholds; store them versioned with source citations.
4. **Field-name verification checklist** (do before any ingestion PR):
   exact USAspending field names for competition codes, offer counts,
   modification/ceiling values, assistance listing numbers, and subaward
   records; SAM.gov exclusion extract layout; per-state registry and
   checkbook schemas; disclosure-portal availability per jurisdiction.
   Concepts in this document are stated at high confidence; exact spellings
   and code lists deliberately are not.
5. **Structural-gap patterns (PROC-1/2, GRANT-1) must say so in the UI**:
   any signal from a proxy detector carries an explicit "public data cannot
   confirm this pattern; the signal reflects a weak proxy" statement in its
   hypothesis text.
