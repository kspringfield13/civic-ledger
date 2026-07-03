"""Contract test: every detector YAML spec must declare the full contract,
so no detector can ship without stating its hypothesis, FP risks, and
validation approach (DETECTION_PRINCIPLES.md #2, #4)."""

from app.services.detectors import REQUIRED_SPEC_FIELDS, load_specs

EXPECTED_DETECTORS = {
    "duplicate_payment",
    "split_purchase",
    "vendor_concentration",
    "debarred_vendor_match",
    "shared_address_cluster",
}


def test_all_starter_detectors_present():
    ids = {spec["id"] for spec in load_specs()}
    assert EXPECTED_DETECTORS.issubset(ids)


def test_every_spec_has_required_fields():
    specs = load_specs()
    assert specs, "no detector specs found"
    for spec in specs:
        missing = [f for f in REQUIRED_SPEC_FIELDS if f not in spec or spec[f] in (None, "", [])]
        assert not missing, f"{spec.get('id', '?')} missing fields: {missing}"


def test_false_positive_risks_are_substantive():
    for spec in load_specs():
        assert len(spec["false_positive_risks"]) >= 2, (
            f"{spec['id']}: declare at least two known false-positive modes"
        )
