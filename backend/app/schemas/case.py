from datetime import datetime

from pydantic import BaseModel


class CaseLeadOut(BaseModel):
    id: int
    title: str
    summary: str | None = None
    status: str = "new"
    assignee: str | None = None
    created_at: datetime | None = None


class ReviewActionIn(BaseModel):
    actor: str
    action: str  # assign|dismiss|escalate|note|request_data
    reason_code: str | None = None
    note: str | None = None
