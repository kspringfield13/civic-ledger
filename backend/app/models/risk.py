"""Risk signals: hypotheses with evidence, severity, and confidence — not findings."""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    detector_id: Mapped[str] = mapped_column(String(100), index=True)
    detector_version: Mapped[str] = mapped_column(String(20))
    subject_type: Mapped[str] = mapped_column(String(50))
    subject_id: Mapped[int]
    hypothesis: Mapped[str] = mapped_column(Text)
    severity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
