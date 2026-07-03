"""Provenance layer: where every record came from (see DATA_SOURCE_POLICY.md)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class DataSource(Base):
    """A registered, policy-approved source (e.g. SAM.gov exclusions)."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    tier: Mapped[int]  # 1 authoritative, 2 supporting, 3 contextual
    url: Mapped[str | None] = mapped_column(String(500))
    license: Mapped[str | None] = mapped_column(String(200))
    access_basis: Mapped[str] = mapped_column(String(100), default="public")
    terms_notes: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)


class SourceDocument(Base):
    """One retrieved artifact; hashed at ingestion for chain of custody."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    locator: Mapped[str] = mapped_column(String(1000))
    sha256: Mapped[str | None] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    retrieval_method: Mapped[str] = mapped_column(String(100), default="api")
