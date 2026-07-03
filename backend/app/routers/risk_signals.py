"""Risk signals — hypotheses for review, never findings."""

from fastapi import APIRouter

from ..schemas.risk import RiskSignalOut

router = APIRouter(prefix="/risk-signals", tags=["risk-signals"])

_PLACEHOLDER = [
    RiskSignalOut(
        id=1,
        detector_id="debarred_vendor_match",
        detector_version="0.1",
        subject_type="vendor",
        subject_id=2,
        hypothesis="Vendor name/UEI matches an active exclusion record (FICTIONAL sample).",
        severity=0.7,
        confidence=0.55,
    ),
]


@router.get("", response_model=list[RiskSignalOut])
def list_risk_signals() -> list[RiskSignalOut]:
    return _PLACEHOLDER
