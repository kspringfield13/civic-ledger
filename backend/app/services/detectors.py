"""Detector engine (Phase 2).

Loads YAML specs from detectors/, validates them against the contract
(see tests/test_detector_contracts.py), and will execute their logic
generically. Signals produced here MUST pass through evidence.attach()
before persistence — a signal without evidence is invalid.
"""

from pathlib import Path

import yaml

DETECTOR_DIR = Path(__file__).resolve().parents[3] / "detectors"

REQUIRED_SPEC_FIELDS = [
    "id",
    "version",
    "purpose",
    "hypothesis",
    "required_fields",
    "logic",
    "severity_inputs",
    "confidence_inputs",
    "false_positive_risks",
    "validation_approach",
    "output_fields",
]


def load_specs(directory: Path = DETECTOR_DIR) -> list[dict]:
    specs = []
    for path in sorted(directory.glob("*.yml")):
        with open(path) as f:
            specs.append(yaml.safe_load(f))
    return specs
