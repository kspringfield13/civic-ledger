# Case packet template

Generated when a human reviewer escalates a lead. Language rules from
EVIDENCE_STANDARD.md apply: signals and patterns, never accusations.

## 1. Lead summary
- Lead ID / title / date opened / reviewer
- One-paragraph neutral description of the pattern observed

## 2. Hypothesis under review
- From detector spec(s), verbatim, with detector id + version

## 3. Evidence
For each item: source name (tier), locator (URL/doc ID), SHA-256, retrieval
timestamp, and the exact fields/values relied on (quoted).

## 4. Innocent explanations considered
- The spec's false-positive modes and what was checked for each

## 5. Assessment
- Severity and confidence with the inputs that produced them
- Explicit uncertainty statement: what is NOT known

## 6. Reviewer disposition
- confirm-worthy / dismissed (reason code) / needs-more-data (what data)
- Recommended next lawful step (e.g. FOIA request draft, IG referral draft)
  — executed by humans outside this system
