"""Resolved entities. Placeholder data drawn from the fictional sample set."""

from fastapi import APIRouter

from ..schemas.entity import VendorOut

router = APIRouter(prefix="/entities", tags=["entities"])

_PLACEHOLDER = [
    VendorOut(
        id=1,
        name="Example Widgets LLC (FICTIONAL)",
        normalized_name="example widgets llc",
        uei="FAKEUEI00001",
    ),
    VendorOut(
        id=2,
        name="Sample Paving Co (FICTIONAL)",
        normalized_name="sample paving co",
        uei="FAKEUEI00002",
    ),
]


@router.get("", response_model=list[VendorOut])
def list_entities() -> list[VendorOut]:
    return _PLACEHOLDER
