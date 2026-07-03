# Detector spec template

Create `detectors/<id>.yml` with ALL fields below (contract-tested):

```yaml
id: <snake_case_id>
version: "0.1"
purpose: <one sentence: what pattern this surfaces>
hypothesis: <what, if true, would explain the pattern — stated as hypothesis>
required_fields: [<model.field references>]
logic: <plain-language rule a reviewer can verify by hand>
severity_inputs: [<impact drivers: dollars, scope>]
confidence_inputs: [<evidence-fit drivers: match quality, data quality>]
false_positive_risks: [<at least two innocent explanations>]
validation_approach: <how a reviewer distinguishes the FP modes from the hypothesis>
output_fields: [<subject_type, ids, scores, evidence_refs>]
```

Rules: severity ≠ confidence; never encode conclusory language; a detector
with fewer than two declared false-positive modes fails CI.
