"""Evidence enforcement (see EVIDENCE_STANDARD.md).

Rule: a RiskSignal may only be persisted with >=1 EvidenceItem whose
source document resolves. This module is the single gate for that rule.
"""


class MissingEvidenceError(ValueError):
    """Raised when a risk signal is submitted without resolvable evidence."""


def require_evidence(evidence_items: list) -> None:
    if not evidence_items:
        raise MissingEvidenceError(
            "Risk signal rejected: no evidence items. See EVIDENCE_STANDARD.md."
        )
