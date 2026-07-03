# Risk Scoring Framework (Blueprint G)

Status: draft v0.1 · Feeds: `backend/app/services/` scoring implementation,
`08-product-ux.md` queue design
Prereqs: extends `DETECTION_PRINCIPLES.md` (especially #1 transparent rules,
#3 severity ≠ confidence, #7 base-rate honest, #8 feedback loops),
`EVIDENCE_STANDARD.md`, and the lead lifecycle in
`09-governance-and-safety-controls.md`. It never overrides them.

## What a score is — and is not

**A triage score is an ordering of human attention, nothing more.** It answers
one question: *given limited reviewer time, which lead should be opened
next?* It does not answer "how likely is fraud?" and it must never be
presented, exported, or described as if it did.

> **No output of this framework is a fraud determination.** Scores order
> human review; only humans, following the lifecycle in
> `09-governance-and-safety-controls.md`, dispose of a lead — and even a
> disposed lead is a *reviewed risk signal*, never a finding of wrongdoing.

Consequences of that framing, baked into the design below:

- The score has **no probabilistic interpretation**. A lead scoring 0.8 is
  not "80% likely" anything; it is *ahead of* a lead scoring 0.5 in the queue.
- Every factor is **computed from declared inputs and reproducible by hand**
  (Detection Principle 1 and 6). No learned weights in v1; any future ML
  reorders triage only and never creates or suppresses signals.
- The UI shows the **factor breakdown next to every score**, plus the
  population base rate for each detector involved (Principle 7).

## The seven factors — kept separate

Each factor is computed, stored, and displayed independently. They are only
combined at the last step, and the combination rule is published here.

| # | Factor | What it measures | What it must NOT measure |
|---|--------|------------------|--------------------------|
| 1 | Raw signal count | How many open signals attach to the subject/lead | Importance. Count alone never drives the score (see below) |
| 2 | Severity | Potential impact if the hypothesis were true: dollars at issue, scope (entities/awards affected), duration of the pattern | How sure we are. Severity is computed even when confidence is low |
| 3 | Confidence | Evidence fit: match quality (e.g. UEI-exact vs name-only), data quality (field population rates, normalization quality), corroboration count *within* the signal's own evidence | Impact. A perfectly evidenced $400 duplicate stays low-severity |
| 4 | Corroboration | Independent signals from *different detector families* and/or *different data sources* converging on the same subject | Repetition. Ten signals from one detector on one dataset are one line of evidence, not ten |
| 5 | Recency decay | How stale the underlying records are | Relevance of old high-impact patterns — decay reduces, never zeroes |
| 6 | Dollar exposure | Total dollars across the lead's evidence-linked awards/payments | A second severity multiplier. Dollars already feed severity; exposure is displayed and used only as a tiebreaker (see double-counting rule) |
| 7 | Human review status | Where the lead sits in the `09-governance` lifecycle | Merit. Status gates queue membership; it never inflates a score |

### 1. Raw signal count (displayed, never multiplied)

`signal_count` is shown on every lead card. It is **not** a term in the
score. Rationale: a noisy detector can emit dozens of correlated signals
from one underlying artifact (e.g., one bad address normalization producing
30 `shared_address_cluster` pairs). Rewarding count would let the noisiest
detector rule the queue and would punish precisely the detectors we tuned
best. Count matters only via factor 4 — and there, only *independent*
signals count.

### 2. Severity ∈ [0, 1]

Computed per signal from the `severity_inputs` declared in its detector spec
(`detectors/*.yml`), normalized through **published, versioned bands** —
config data with citations, not code constants. v1 default bands:

| Dollar impact of the signal | Severity contribution |
|---|---|
| < $10k | 0.1 |
| $10k – $100k | 0.3 |
| $100k – $1M | 0.5 |
| $1M – $10M | 0.7 |
| > $10M | 0.9 |

Scope and duration inputs (cluster size, count of transactions, stream
duration) add up to +0.1 total, capped so severity ≤ 1.0. Bands are
per-jurisdiction config: $1M means something different in a small town's
checkbook than in federal data. **The band table version used is recorded on
each signal** (Principle 6).

### 3. Confidence ∈ [0, 1]

Computed per signal from its spec's `confidence_inputs`. Each spec's inputs
map to published levels; e.g. `debarred_vendor_match`:

| match_key | base confidence |
|---|---|
| `uei_exact` | 0.9 |
| `name_plus_location` | 0.5 |
| `name_only` | 0.2 |

modified by `name_commonality` (common name: ×0.5) and data-quality inputs.
Detectors the taxonomy marks *structural gap* or *triage-only*
(`bid_rotation_pattern`, `award_timing_anomaly` check A,
`new_vendor_rapid_award` standalone) carry **confidence caps** written into
their specs — no arithmetic may exceed the cap.

### 4. Corroboration multiplier C ∈ [1.0, 2.0]

Count `k` = number of **independent lines** on the same subject, where a line
is a distinct (detector family, data source) pair whose signal has
per-signal priority ≥ 0.2 (see below). Then:

```
C = min(1 + 0.25 × (k − 1), 2.0)
```

One line → C = 1.0 (no boost). Two independent lines → 1.25. Five or more →
capped at 2.0. Detector *families* group specs that share an evidence basis
(e.g., `split_purchase` and a future `split_invoice` are one family), so the
same artifact can't corroborate itself.

### 5. Recency decay d(t) ∈ (0, 1]

```
d(t) = 0.5 ^ (age_months / 24)
```

with `age_months` measured from the most recent evidence-linked record in
the signal, and a **floor of 0.25**: 24-month half-life, but a large old
pattern never decays to invisibility — statutes of limitation and audit
lookbacks make old patterns reviewable. Half-life and floor are versioned
config per deployment.

### 6. Dollar exposure (tiebreaker only)

`exposure` = sum of amounts across the lead's evidence-linked awards and
payments, displayed as a banded figure. **Double-counting rule:** dollars
already enter severity (factor 2), so exposure is *never multiplied into the
score*. It breaks ties: within a score band (rounded to 0.05), higher
exposure sorts first.

### 7. Human review status (hard gates)

Statuses from `09-governance-and-safety-controls.md`:

| Lead status | Queue effect |
|---|---|
| `new`, `triaged` | In the active queue, scored as below |
| `in_review` | Held out of the unassigned queue (visible on assignee's board) |
| `needs_more_data` | Parked queue; auto-returns to `triaged` when matching SourceDocuments arrive |
| `escalated` | Out of the triage queue (in the case-packet workflow) |
| `dismissed` | Excluded; its signals' dismissal reason_codes feed threshold tuning (Principle 8) |
| Superseded-evidence reopen | Back to `triaged` with a system note, rescored on current data |

A dismissed signal contributes **zero** to any future lead score unless an
admin reopens it with written rationale.

## Combination rule (the whole formula)

Per open signal *i* on the lead:

```
p_i = severity_i × confidence_i × d(t_i)          # per-signal priority
```

Lead triage score:

```
score = min( [ p_max + 0.25 × Σ(other p_i, top 4 only) ] × C , 1.0 )
```

- `p_max` — the single strongest signal dominates: one excellent signal
  should outrank a pile of weak ones.
- `0.25 × Σ(other p_i)`, limited to the next 4 strongest — additional
  signals help with diminishing returns; the cap stops count-stuffing.
- `× C` — the corroboration multiplier from factor 4.
- Ties broken by dollar exposure, then by oldest-unreviewed-first.

Every term is visible in the lead's "why this score" panel, with links to
each signal's evidence items. A reviewer with a calculator can reproduce the
number — that is the acceptance test for any implementation.

## Worked examples

### Example 1 — one strong signal beats six weak ones

**Lead A**: one `debarred_vendor_match` signal. Award $2.4M during an active
exclusion window, UEI-exact match, distinctive name, records 3 months old.

- severity = 0.7 (band $1M–$10M) + 0.0 scope = **0.7**
- confidence = 0.9 (`uei_exact`), no commonality penalty = **0.9**
- d = 0.5^(3/24) = **0.917**
- p = 0.7 × 0.9 × 0.917 = **0.578**
- One line → C = 1.0 → **score = 0.578**, exposure $2.4M

**Lead B**: six `award_timing_anomaly` check-A signals on one vendor,
$40k each, fiscal calendar unverified, records 3 months old.

- severity per signal = 0.3; confidence = 0.25 (capped triage-only, calendar
  unverified); d = 0.917
- p_i = 0.3 × 0.25 × 0.917 = **0.069** each
- All six are one line (same detector family, same source) → C = 1.0
- score = 0.069 + 0.25 × (4 × 0.069) = 0.069 + 0.069 = **0.138**

Lead A (score 0.578, signal_count 1) far outranks Lead B (0.138,
signal_count 6). The queue shows both counts so the reviewer sees why.

### Example 2 — independent corroboration lifts a moderate lead

**Lead C**: vendor with two signals from different families and sources:

1. `shared_address_cluster` (registry + spending data): severity 0.5
   (cluster dollars $300k), confidence 0.6 (good normalization, address not
   on agent allowlist), 6 months old → d = 0.841 →
   p = 0.5 × 0.6 × 0.841 = **0.252**
2. `new_vendor_rapid_award` (registry source): severity 0.5, confidence
   0.3 (standalone cap), 6 months old → p = 0.5 × 0.3 × 0.841 = **0.126**

Both lines ≥ 0.2? Only line 1 is; line 2 (0.126) is below the 0.2
independence threshold, so k = 1, **C = 1.0**:

- score = 0.252 + 0.25 × 0.126 = **0.284**

Now a third, independent signal arrives: `sole_source_repeat` on the same
vendor (competition-code source), p = 0.31. k = 2 lines ≥ 0.2 → C = 1.25:

- score = (0.31 + 0.25 × (0.252 + 0.126)) × 1.25 = (0.31 + 0.0945) × 1.25
  = **0.506**

Corroboration nearly doubled the lead's position — because *independent*
evidence converged, not because signals piled up.

### Example 3 — recency decay with a floor

Same as Lead A but the records are 6 years old (72 months):

- d = max(0.5^(72/24), 0.25) = max(0.125, 0.25) = **0.25**
- p = 0.7 × 0.9 × 0.25 = **0.158** → score = 0.158

The lead drops far down the queue but never vanishes; if the reviewer's
mandate includes historical audits, a queue filter can sort by undecayed
p (also stored).

### Example 4 — review status gates

Lead C from Example 2 is opened, and the reviewer dismisses the
`shared_address_cluster` signal with reason_code
`registered_agent_address`. That signal now contributes 0, the allowlist
gets a candidate entry (Principle 8), and the lead rescores:

- remaining: `sole_source_repeat` p = 0.31, `new_vendor_rapid_award`
  p = 0.126; k = 1 → C = 1.0
- score = 0.31 + 0.25 × 0.126 = **0.342** (down from 0.506)

The audit trail (`ReviewAction`) records who dismissed what and why; the
rescore is automatic and logged.

## Anti-gaming and honesty requirements

1. **No hand-set scores.** Severity and confidence come only from declared
   spec inputs (Principle 3); overrides require an admin `ReviewAction` with
   rationale and appear in the breakdown as an override, visually distinct.
2. **Caps are contracts.** A detector spec's confidence cap binds the
   scorer; CI should fail if a stored signal exceeds its spec's cap.
3. **Base rates beside scores.** Every queue view shows, per detector,
   flagged count / population scanned (Principle 7).
4. **Versioned everything.** Band tables, half-life, floor, corroboration
   cap, and the formula itself carry a `scoring_version`; every stored score
   records it, so a score can be reproduced later exactly (Principle 6).
5. **Feedback loop.** Dismissal reason_codes are aggregated per detector;
   a detector whose signals are dismissed > X% for the same reason gets a
   threshold-review task, not a silent weight change.

## Explicit restatement

Scores produced under this framework are **triage ordinals for human
attention**. They are not risk probabilities, not findings, and not fraud
determinations, and no export, API response, or UI surface may label them
otherwise. The language standard in `EVIDENCE_STANDARD.md` applies to every
surface where a score appears.
