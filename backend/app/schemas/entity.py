from pydantic import BaseModel


class AgencyOut(BaseModel):
    id: int
    name: str
    canonical_code: str | None = None


class VendorOut(BaseModel):
    id: int
    name: str
    normalized_name: str | None = None
    uei: str | None = None
