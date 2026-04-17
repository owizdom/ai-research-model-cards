from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Date, Integer, Text, ForeignKey, UniqueConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from ..session import Base

if TYPE_CHECKING:
    from .lab import Lab
    from .taxonomy import DocumentTaxonomyMapping


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[Optional[int]] = mapped_column(ForeignKey("labs.id", ondelete="SET NULL"), index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    doc_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # doc_scope classifies the document's role so "0 benchmarks" on a
    # policy doc isn't a surprise. Values: capability_paper, safety_paper,
    # technical_paper, model_card, system_card, policy_doc, license,
    # usage_policy, constitution. Backfilled from doc_type + title heuristics
    # on migration 0006; new sources can set explicitly via registry.
    doc_scope: Mapped[Optional[str]] = mapped_column(String, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String)
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lab: Mapped[Optional["Lab"]] = relationship("Lab", back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document",
        order_by="DocumentVersion.version_date.desc()", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "content_hash", name="uq_document_version_hash"),
        Index("ix_document_versions_document_date", "document_id", "version_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_date: Mapped[date] = mapped_column(Date, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    wayback_url: Mapped[Optional[str]] = mapped_column(String)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768))

    document: Mapped["Document"] = relationship("Document", back_populates="versions")
    taxonomy_mappings: Mapped[list["DocumentTaxonomyMapping"]] = relationship(
        "DocumentTaxonomyMapping", back_populates="document_version", cascade="all, delete-orphan"
    )
