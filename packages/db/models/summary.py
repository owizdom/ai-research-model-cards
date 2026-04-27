from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, JSON, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base


class DocumentSummary(Base):
    """Claude-written chaptered summary of a document version."""
    __tablename__ = "document_summaries"
    __table_args__ = (
        Index("ix_document_summaries_version", "document_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    source_hash: Mapped[str] = mapped_column(String(12), nullable=False)
    model_used: Mapped[str] = mapped_column(String, nullable=False)
    chapters: Mapped[list] = mapped_column(JSON, nullable=False)
    total_words: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    error: Mapped[Optional[str]] = mapped_column(Text)
