"""Human review layer: leads, actions, and the evidence chain."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class CaseLead(Base):
    """A bundle of related risk signals queued for a human reviewer."""

    __tablename__ = "case_leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="new")
    assignee: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewAction(Base):
    """Audit trail: who did what to a lead, when, and why (structured reason)."""

    __tablename__ = "review_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_lead_id: Mapped[int] = mapped_column(ForeignKey("case_leads.id"))
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    reason_code: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvidenceItem(Base):
    """Links a risk signal to the exact source material it relies on."""

    __tablename__ = "evidence_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    risk_signal_id: Mapped[int] = mapped_column(ForeignKey("risk_signals.id"))
    source_document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"))
    fields_relied_on: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
