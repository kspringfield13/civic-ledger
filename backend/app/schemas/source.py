from datetime import datetime

from pydantic import BaseModel


class DataSourceOut(BaseModel):
    id: int
    name: str
    tier: int
    url: str | None = None
    access_basis: str = "public"
    approved_at: datetime | None = None
