"""Case review queue. Placeholder until Phase 3 workflow lands."""

from fastapi import APIRouter

from ..schemas.case import CaseLeadOut

router = APIRouter(prefix="/cases", tags=["cases"])

_PLACEHOLDER = [
    CaseLeadOut(
        id=1,
        title="Review: fictional exclusion match for Sample Paving Co",
        summary="Bundled from 1 risk signal. Sample data only.",
        status="new",
    ),
]


@router.get("", response_model=list[CaseLeadOut])
def list_cases() -> list[CaseLeadOut]:
    return _PLACEHOLDER
