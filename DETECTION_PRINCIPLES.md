# Detection Principles

1. **Transparent rules first.** Every detector is a declarative YAML spec a
   reviewer can read. No black-box scoring in v1; any future ML assists
   triage ordering only and never creates signals by itself.
2. **Hypothesis, not verdict.** Each spec states the hypothesis it tests and
   the innocent explanations that produce the same pattern.
3. **Severity ≠ confidence.** Severity measures potential impact (dollars,
   scope); confidence measures how well the evidence fits the hypothesis.
   Both are computed from declared inputs, never hand-set.
4. **False positives are a design input.** Every spec lists known FP modes and
   the validation approach that would distinguish them.
5. **Evidence-linked.** A signal without resolvable evidence pointers is
   invalid and must not be persisted (enforced in `services/evidence.py`).
6. **Reproducible.** Same inputs + same spec version → same signals. Detector
   specs are versioned; signals record the spec version that produced them.
7. **Base-rate honest.** Dashboards show total population alongside flagged
   counts so reviewers see how rare (or common) a pattern is.
8. **Reviewer feedback loops back.** Dismissal reasons are structured data
   used to tune thresholds — not free text lost in a void.
