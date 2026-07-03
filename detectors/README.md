# Detector specs

Declarative YAML specifications for rule-based detectors. Each spec is the
single source of truth for a detector's hypothesis, logic, scoring inputs,
known false-positive modes, and validation approach.

Contract (enforced by `backend/tests/test_detector_contracts.py`): every spec
must define `id, version, purpose, hypothesis, required_fields, logic,
severity_inputs, confidence_inputs, false_positive_risks, validation_approach,
output_fields`.

Detectors produce **risk signals** for human review — never determinations.
Signals persist only with linked evidence (see `EVIDENCE_STANDARD.md`).
