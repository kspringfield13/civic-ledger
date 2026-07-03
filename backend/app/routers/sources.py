"""Registered data sources. Placeholder in-memory data until Phase 1 persistence."""

from fastapi import APIRouter

from ..schemas.source import DataSourceOut

router = APIRouter(prefix="/sources", tags=["sources"])

_PLACEHOLDER = [
    DataSourceOut(
        id=1,
        name="SAM.gov Exclusions (planned)",
        tier=1,
        url="https://sam.gov/data-services",
        access_basis="public",
    ),
    DataSourceOut(
        id=2,
        name="USAspending Awards (planned)",
        tier=1,
        url="https://api.usaspending.gov",
        access_basis="public",
    ),
]


@router.get("", response_model=list[DataSourceOut])
def list_sources() -> list[DataSourceOut]:
    return _PLACEHOLDER
