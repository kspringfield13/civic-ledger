"""Spend-side records: awards, payments, exclusions."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ContractAward(Base):
    __tablename__ = "contract_awards"
    id: Mapped[int] = mapped_column(primary_key=True)
    award_id: Mapped[str] = mapped_column(String(100), index=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    description: Mapped[str | None] = mapped_column(String(1000))
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    award_date: Mapped[date] = mapped_column(Date)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))


class GrantAward(Base):
    __tablename__ = "grant_awards"
    id: Mapped[int] = mapped_column(primary_key=True)
    award_id: Mapped[str] = mapped_column(String(100), index=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    award_date: Mapped[date] = mapped_column(Date)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_ref: Mapped[str] = mapped_column(String(100), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"))
    contract_award_id: Mapped[int | None] = mapped_column(ForeignKey("contract_awards.id"))
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    paid_date: Mapped[date] = mapped_column(Date)
    invoice_number: Mapped[str | None] = mapped_column(String(100), index=True)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))


class ExclusionRecord(Base):
    """Debarment/suspension record from an official exclusions list."""

    __tablename__ = "exclusion_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    excluded_name: Mapped[str] = mapped_column(String(300), index=True)
    uei: Mapped[str | None] = mapped_column(String(12), index=True)
    exclusion_type: Mapped[str | None] = mapped_column(String(100))
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))
