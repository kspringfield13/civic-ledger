# Blueprint 12 — Red-Team Findings

Adversarial review of the nine blueprint drafts and the 10 detector specs.
Authored by the command model after the dedicated QA agent run was cut short;
findings draw on direct review of every blueprint doc, the detector YAMLs,
the current backend code, and the drafting agents' own risk disclosures.
Severity: **HIGH** = could wrongly implicate someone or silently corrupt
evidence; **MED** = degrades trust, coverage, or reviewability; **LOW** =
friction or drift risk.

The framing question throughout: *how does this system hurt an innocent
vendor, mislead a reviewer, or flatter itself — and what test would catch it?*

---

## 1. Ways the system could wrongly implicate innocent parties

### RT-1 (HIGH) — Name-only matches against exclusion records for individuals
`debarred_vendor_match` matches vendors by UEI or name+postal-code. But the
SAM exclusions file also lists **individuals**, most without UEIs, so the
tempting extension to person-name matching has no strong identifier rung at
all (Blueprint 04 caps name-only at blocking, confidence 0.40). **Failure
scenario:** a sole proprietorship named for a common surname matches an
excluded individual two states away; the signal survives because postal-code
agreement is coincidental in a dense metro.
**Fix:** hard rule — exclusion matches for individual-type exclusion records
require an identifier or documented registry linkage, never name+location
alone; add a fixture pair ("JOHN SMITH CONSULTING" vs excluded "John Smith")
to `data/sample/` that MUST NOT produce a signal, enforced in CI.

### RT-2 (HIGH) — Merge errors propagate faster than the dispute workflow heals
Blueprint 09 §7 freezes disputed entities and recomputes, but recompute is
acknowledged as unimplemented, and Blueprint 04 admits exported packets
cannot be recalled. **Failure scenario:** a bad rung-3 merge (state registry
number collision across states) attaches an exclusion signal to the wrong
vendor; a packet is exported before anyone disputes; the correction notice
depends entirely on the operator remembering §7.5.
**Fix:** until recompute exists, block exports for any lead whose evidence
chain crosses a merge younger than N days (cooling-off), and make the
export generator print the merge basis and date into the packet — both are
cheap and mechanical.

### RT-3 (MED) — Registered-agent allowlist is load-bearing and empty
Three documents (02, 04, and the `shared_address_cluster` spec) lean on a
curated registered-agent/virtual-office address allowlist that does not
exist yet. Until it is populated, the single largest documented FP source
for network signals has no guardrail. **Fix:** M2 must ship a starter
allowlist file (even 50 entries) plus the rule that an unallowlisted address
shared by >5 vendors is auto-flagged for allowlist review *instead of*
generating cluster edges.

### RT-4 (MED) — `signal_view` audit trail is itself a dossier
Blueprint 09 correctly logs signal views, but the log then records which
named entities a human repeatedly examined — a browsing history that would
be the most sensitive artifact in a breach or a FOIA-style demand against
the operator. The doc notes this; nothing mitigates it. **Fix:** give the
audit log its own access rule (admin-only reads), and store subject ids,
not denormalized names, in view events.

## 2. Political and selection bias vectors

### RT-5 (MED) — The corpus determines who can ever be flagged
V1 ingests federal procurement + exclusions only (D1). Every scrutinized
entity is therefore a federal contractor; state grantees, municipal vendors,
and everyone outside USAspending are structurally invisible. That is a
defensible scoping decision — but dashboards showing "top risk signals"
will read as "these kinds of companies are risky" when they mean "this is
the only data we have." **Fix:** the Blueprint 08 base-rate components must
state corpus coverage ("signals drawn from federal awards FY22–25 only") on
every aggregate surface, not just population denominators.

### RT-6 (MED) — Pilot-state choice is a bias decision disguised as a
convenience decision. Blueprint 01 picks one state checkbook pilot on
engineering criteria (schema quality). Whichever state is chosen, its
vendors become the only ones exposed to payment-level detectors
(duplicate_payment, split_invoice). **Fix:** record the pilot-state
rationale in the source registry entry as an explicit operator decision,
and suppress cross-state comparisons in UI until ≥3 states exist.

### RT-7 (LOW) — Precision metric rewards timidity
S1 (queue precision ≥30%) improves by flagging only the safest patterns.
A system optimized on S1 alone converges on exclusion matches and nothing
else. The mission brief acknowledges S1 can't measure recall; nothing yet
pushes back. **Fix:** track a paired "coverage" indicator — count of
distinct detector families producing reviewed leads per quarter — so
narrowing shows up as a visible regression.

## 3. Overfitting to noisy public records

### RT-8 (HIGH) — Exact-amount duplicate grouping vs float money columns
The data-architecture agent found the models type money as Python `float`
against `Numeric(14,2)`. `duplicate_payment` groups by exact
(vendor, amount). Float drift (e.g., 1052.20 stored as 1052.1999…) silently
breaks exact-match grouping differently across SQLite and Postgres —
false negatives on one dialect, phantom mismatches on the other.
**Fix:** TODO already filed in Blueprint 05; elevate it to M1 (before any
ingestion), use `Decimal`/integer-cents end to end, and add a dual-dialect
CI test that a known duplicate pair groups identically on both databases.

### RT-9 (MED) — UEI semantics are asserted, not verified
Rung-1 auto-merge (confidence 0.98) assumes UEI ≡ legal entity. Blueprint 04
itself flags that if UEI is per-registration (as DUNS was per-location),
rung-1 conflates branches with parents. Everything downstream inherits
this. **Fix:** the M2.7 field-verification spike must answer this question
specifically, in writing, before rung-1 auto-merge is enabled; until then
rung-1 merges are review-queue items like rung 4.

### RT-10 (MED) — Snapshot staleness reads as currency
The exclusions "current set = latest successful snapshot" rule means a
silently failing daily ingest leaves week-old data presented as current,
and `debarred_vendor_match` FP mode #2 (lapsed/rescinded exclusions)
becomes live. **Fix:** surface snapshot age on every exclusion-derived
signal (the UI already requires retrieval timestamps — add an explicit
staleness warning above an operator-set threshold) and alert when the
pipeline misses two consecutive scheduled runs.

## 4. Sophisticated behavior the current detectors will miss

Honesty requirement: these are not fixable gaps; they are limits that must
stay visible so nobody oversells coverage.

- **Clean collusion.** Colluders with distinct addresses, officers, and
  registries defeat NET-1 entirely; bid rotation without shared identifiers
  produces only the weak `bid_rotation_pattern` proxy, which correctly
  cannot escalate without an interlink edge. The taxonomy says this
  (structural gap); the executive brief and any demo material must repeat it.
- **Threshold-aware pricing.** Vendors pricing 15% high stay inside
  `price_outlier`'s 3× median gate forever. Peer-relative drift detection
  needs line-item data that is a structural gap federally.
- **Subaward invisibility.** FSRS under-reporting means pass-through abuse
  hides by *not filing*; the specs treat missing subawards as unknown, but
  "unknown" must never be displayed as "no pass-through risk found."
- **Fresh shells with clean paper.** `new_vendor_rapid_award` catches lazy
  shells; an incorporator who ages entities two years and varies addresses
  defeats it. Registration-age gates select for unsophisticated actors —
  acceptable if stated, misleading if not.

## 5. Cross-document contradictions and gaps

| # | Sev | Contradiction | Resolution |
|---|-----|---------------|------------|
| RT-11 | MED | Mission brief D-series treats the 5 original detectors as the v1 universe; the detection agent shipped 5 more, 3 blocked on schema extensions | Catalog (07) already marks implementation status; the brief's assumption is stale — v1 *runnable* set is the original 5 minus data-gated ones. Note in 13-agent-findings; no doc edit needed if the backlog (M3) stays authoritative |
| RT-12 | MED | `duplicate_payment` is a ROADMAP Phase-2 flagship but its realistic data (invoice-level) arrives only with the state-checkbook pilot ranked difficulty-high | Backlog already resolves this: M3 closes on fictional fixtures; real signals await the pilot. Keep the caveat in any status reporting |
| RT-13 | MED | Taxonomy wants `taxonomy_ref` required in the spec contract; detection made it optional to avoid breaking 5 existing specs | Correct call; file the backfill as an explicit M3 task so the contract can tighten rather than drift |
| RT-14 | LOW | CI pins Python 3.12; local venv runs 3.11; pyproject allows ≥3.11 | Harmless until a 3.12-only feature slips in; M6's dual-dialect CI job should also pin-and-test the floor version |
| RT-15 | LOW | `main.py` CORS allows GET only; Phase-3 review actions add POSTs | Already flagged in the build plan — widen CORS in the same commit as the first POST route |
| RT-16 | MED | CaseLead↔RiskSignal has no join table in current code (evidence chain broken at the human layer); three agents independently flagged it | Blueprint 05's `case_lead_signals` + service rule "no lead without signals" is the fix; it must land in M1's migration, not later |

## 6. Missing validation — concrete additions

1. **Adversarial fixture pack** in `data/sample/` (all fictional, labeled):
   the RT-1 name-collision pair; a legitimate BPA with 12 small same-vendor
   awards (must NOT trigger `split_purchase`); a registered-agent address
   hosting 30 unrelated vendors (must NOT cluster); a rescinded exclusion
   with an award inside the original window (must trigger at reduced
   confidence citing snapshot age); twin vendors differing only by legal
   suffix (must NOT auto-merge).
2. **Determinism test** (already S4): run each detector twice, diff signals
   byte-for-byte, both dialects.
3. **Language lint** (brief item 10): extend beyond UI strings to detector
   YAML `hypothesis` fields and packet templates; wordlist as versioned
   config per Blueprint 08.
4. **Dismissal-loop test:** simulate 20 dismissals with reason
   `fp_known_mode:*` and assert the tuning report surfaces the top FP mode —
   proving Principle 8's loop is real, not aspirational.
5. **Merge-reversal drill:** scripted merge → signal → unmerge → assert
   downstream signals flagged `resolution_reverted` and the lead reopens.
   Run in CI once the merge log exists (M2).

## 7. Verdict

No boundary violations found in any draft: no doc proposes non-public data,
person-first analysis, automated referral, or accusation language; the
strictest agents (network-intel demoting name+address merges, product-UX
banning entity leaderboards) tightened the mission rather than loosening it.
The two failure modes most likely to actually happen are unglamorous:
**RT-8 (float money)** and **RT-3 (empty allowlist)** — both are cheap to
fix now and expensive after real data lands. Highest-severity open items:
RT-1, RT-2, RT-8. All three have concrete M1–M3 fixes above and none block
starting the backlog.
