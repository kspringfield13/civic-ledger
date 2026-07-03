# Detector Catalog (Blueprint I)

Status: draft v0.1 · Source of truth: `detectors/*.yml` (this catalog
summarizes; if catalog and YAML disagree, the YAML wins and this file has a
bug). Contract enforced by `backend/tests/test_detector_contracts.py`.
Prereqs: `DETECTION_PRINCIPLES.md`, `EVIDENCE_STANDARD.md`,
`02-fraud-pattern-taxonomy.md` (taxonomy IDs referenced below),
`06-risk-scoring.md` (how severity/confidence become triage order).

Every detector emits **risk signals — hypotheses with linked evidence —
never findings**. Every spec declares at least two false-positive modes and
a validation approach; a spec without them fails CI.

## Catalog (10 detectors)

| Detector | Hypothesis (one line) | Required fields | Output | Severity basis | Confidence basis | Top FP risks | Validation method |
|---|---|---|---|---|---|---|---|
| `debarred_vendor_match` | Award/payment dated inside an exclusion record's active window, to a matching vendor, may be prohibited contracting with an excluded party | vendor.uei, vendor.normalized_name, exclusion.uei/excluded_name/active_from/active_to, award.award_date | vendor signal: exclusion_record_id, matched_award_ids, match_key | Award dollars; exclusion type | Match key (UEI-exact > name+location > name-only); name commonality; date-window margin | Name collision with unrelated entity; stale/rescinded exclusion snapshot | Reviewer re-checks the live authoritative exclusion record and identifiers before escalation |
| `duplicate_payment` | Near-identical payments (vendor, amount, invoice, close dates) may be one invoice paid twice | payment.vendor_id/amount/invoice_number/paid_date/agency_id | payment signal: matched_payment_ids, invoice_match_quality | Duplicate dollars; count in group | Invoice match quality (exact > normalized > amount-only); date proximity; same agency | Legitimate recurring charges; progress payments reusing an invoice prefix | Pull both source payments; check contract for recurrence; look for reversal/credit in-period |
| `shared_address_cluster` | ≥2 vendors at one normalized address winning from the same agency may not be independent | vendor.primary_address_id, address.normalized, award.vendor_id/agency_id/award_date | cluster signal: address_id, vendor_ids, agency_ids | Combined cluster dollars; cluster size | Address-normalization quality; agent/coworking allowlist coverage; officer overlap | Registered-agent/virtual-office addresses; incubators/coworking | Allowlist check; registry pull for disclosed affiliation; officer overlap in primary filings |
| `split_purchase` | ≥2 awards just under a threshold, close in time, whose sum exceeds it, may be an obligation split to avoid approval | award.agency_id/vendor_id/amount/award_date, config.thresholds | cluster signal: award_ids, threshold_referenced, combined_amount | Combined amount over threshold; number of splits | Proximity to threshold; time window; description similarity | Distinct needs pricing near a threshold; lawful BPA small orders; wrong threshold assumed | Verify the applicable threshold/period; read descriptions for distinct scope; check for a competed vehicle |
| `vendor_concentration` | Vendor share of an agency's category spend far above peer norms may indicate steering | award.agency_id/vendor_id/amount/award_date/description | vendor signal: agency_id, spend_share, peer_percentile | Vendor share of agency spend; total dollars | Peer baseline sample size; category classification quality; competition-indicator availability | Sole legitimate supplier in a thin market; mission that inherently concentrates spend | Compare named peer agencies; check public sole-source justifications; confirm category assignment |
| `price_outlier` | Award priced far above the peer distribution for comparable purchases may reflect overpayment | award.agency_id/vendor_id/amount/award_date/description | award signal: category_key, peer_award_ids, category_median, peer_percentile | Dollars over category median; award amount | Category classification quality; peer group sample size; description specificity | Bundled/multi-year award vs single-delivery peers; category misclassification; ceiling-vs-obligation recording | Read full description and solicitation; compare named peer awards; check ceiling vs obligation |
| `sole_source_repeat` | Repeated non-competed awards to one vendor, with escalating amounts or serial justifications, may indicate steering | award fields + award.extent_competed, award.competition_justification_code *(schema ext.)* | vendor signal: agency_id, award_ids, noncompeted_dollar_share, repeated_justification_code | Non-competed dollars; award count; escalation | Competition-code population rate; justification specificity; peer baseline size | Lawful sole-source categories; directed set-asides non-competed by design; missing codes misread | Locate the published J&A; verify code semantics against the official code list; peer comparison |
| `bid_rotation_pattern` | Closed, interlinked vendor set winning an (agency, category) stream in alternation is a weak proxy consistent with coordination — public data cannot confirm it | award fields + description, relationship_edge.relation, address.normalized | cluster signal: agency_id, vendor_ids, award_ids, category_key, interlink_edge_ids | Combined stream dollars; stream duration | Interlink edge count; market breadth; offer-count availability; category quality | Thin markets where alternation is honest; lawful rotation policies; IDIQ/BPA task allocation | Market-breadth check; buyer's published purchasing policy; multiple-award vehicle check; bid tabs where public. Rotation shape alone never escalates |
| `award_timing_anomaly` | Vendor capturing an outsized share of year-end rush awards, or awards finalized days after posting without emergency context, may indicate a pre-selected outcome | award fields, config.fiscal_year_end, solicitation.posted_date *(schema ext.)* | vendor signal: agency_id, award_ids, check_type, year_end_share_ratio, window_days | Anomalous award dollars; count | Fiscal-calendar verification; solicitation join quality; base-rate sample | Lawful year-end obligation of expiring funds (high base rate — triage-only); genuine emergencies; reposted solicitations | Verify fiscal calendar and expiring-fund context; read solicitation for emergency/amendment history; base-rate comparison |
| `new_vendor_rapid_award` | Vendor registered shortly before winning first-year award volume far above new-vendor norms may lack the operating history the awards imply (shell risk) | vendor.registration_date *(schema ext.)*, award.vendor_id/amount/award_date, vendor.primary_address_id, address.normalized | vendor signal: first_award_id, days_registration_to_first_award, first_year_award_dollars, first_year_percentile | First-year award dollars; largest single award | Registration-date source quality; address type; single-agency dependence; officer overlap | Legitimate startups/home businesses (dominant); lawful single-project SPVs; registry staleness | Registry pull (officers, history); set-aside/parent check; requires an independent co-occurring signal to escalate |

All signals additionally output `severity`, `confidence`, and
`evidence_refs` per `EVIDENCE_STANDARD.md`; the columns above show the
detector-specific payload.

## Taxonomy mapping and implementation status

| Detector | Taxonomy ref | Status | Blocking dependencies |
|---|---|---|---|
| `debarred_vendor_match` | VEND-2 | Spec complete; Phase-2 build target | None — Tier-1 data both sides |
| `duplicate_payment` | PAY-1 | Spec complete; Phase-2 build target | Checkbook-style (invoice-level) sources only; federal data is award-level |
| `shared_address_cluster` | NET-1 | Spec complete | Agent/coworking allowlist (maintained as data) |
| `split_purchase` | PROC-3 | Spec complete | Versioned, cited threshold config per jurisdiction |
| `vendor_concentration` | PROC-4/5 (partial) | Spec complete | Category classification quality (v0 naive keywords) |
| `price_outlier` | PROC-5, PAY-3 (nearest) | Spec new (v0.1) | Category classification; ≥30-award peer groups |
| `sole_source_repeat` | PROC-4 | Spec new (v0.1) | **Schema ext.:** competition fields on `ContractAward`; verify FPDS/USAspending field names + code lists |
| `bid_rotation_pattern` | PROC-1, NET-2 | Spec new (v0.1); structural-gap proxy | NET-1 edges populated; UI must carry the weak-proxy statement verbatim |
| `award_timing_anomaly` | PROC-5 (short-window facet); fiscal facet proposed as new taxonomy entry | Spec new (v0.1); check A triage-only | **Schema ext.:** solicitation posting dates + join verification; cited fiscal calendars |
| `new_vendor_rapid_award` | VEND-1 | Spec new (v0.1); confidence-capped standalone | **Schema ext.:** `Vendor.registration_date`; per-jurisdiction registry availability (Tier 2) |

## Cross-cutting rules for all ten

1. **Severity ≠ confidence** in every spec: severity inputs are impact
   drivers (dollars, scope, duration); confidence inputs are evidence-fit
   drivers (match quality, data quality, corroboration). The scorer in
   `06-risk-scoring.md` consumes them separately.
2. **Hypothesis language only.** Spec `hypothesis` fields state what the
   pattern *may* represent and name innocent explanations; no spec, signal,
   or UI text may use conclusory language (`EVIDENCE_STANDARD.md`).
3. **Hand-verifiable logic.** Each `logic` field is a plain-language rule a
   reviewer can re-execute manually on the evidence-linked records — the
   acceptance test for every implementation.
4. **Structural-gap honesty.** `bid_rotation_pattern` (and any future proxy
   detector) states in its hypothesis that public data cannot confirm the
   underlying pattern; that statement travels with the signal into the UI
   (taxonomy implementation note 5).
5. **Missing data is unknown, not incriminating.** Absent competition codes,
   registry records, or subawards reduce confidence; they never raise it
   (`sole_source_repeat`, `new_vendor_rapid_award` encode this explicitly).
6. **Field-name verification before ingestion.** Field references in the
   new specs are conceptual against our models; exact upstream spellings
   (USAspending competition codes, SAM extract layout, registry schemas)
   must be verified per the taxonomy's checklist before any ingestion PR.
