from datetime import datetime

from pydantic import BaseModel, Field


class RiskSignalOut(BaseModel):
    id: int
    detector_id: str
    detector_version: str
    subject_type: str
    subject_id: int
    hypothesis: str
    severity: float = Field(ge=0, le=1, description="Potential impact, 0-1")
    confidence: float = Field(ge=0, le=1, description="Evidence fit, 0-1. Not a finding.")
    status: str = "open"
    created_at: datetime | None = None
    disclaimer: str = "Risk signal for human review — not a determination of fraud."
