"""Resolved entities. Individuals appear only in official/registered capacities."""

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    canonical_code: Mapped[str | None] = mapped_column(String(50))


class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(300), index=True)
    uei: Mapped[str | None] = mapped_column(String(12), index=True)
    primary_address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"))


class PersonOfficer(Base):
    """A person in an official/registered capacity only (officer, agent, CO)."""

    __tablename__ = "person_officers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(100))
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"))
    agency_id: Mapped[int | None] = mapped_column(ForeignKey("agencies.id"))


class Address(Base):
    __tablename__ = "addresses"
    id: Mapped[int] = mapped_column(primary_key=True)
    raw: Mapped[str] = mapped_column(String(500))
    normalized: Mapped[str | None] = mapped_column(String(500), index=True)
    city: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))


class RelationshipEdge(Base):
    """Typed edge between entities (shared_address, officer_of, awarded_by)."""

    __tablename__ = "relationship_edges"
    id: Mapped[int] = mapped_column(primary_key=True)
    src_type: Mapped[str] = mapped_column(String(50))
    src_id: Mapped[int]
    dst_type: Mapped[str] = mapped_column(String(50))
    dst_id: Mapped[int]
    relation: Mapped[str] = mapped_column(String(100), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"))
