from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base

if TYPE_CHECKING:
    from .document import Document


class ModelFamily(Base):
    """A model lineage: e.g. 'Claude', 'GPT', 'Llama', 'Gemini'"""
    __tablename__ = "model_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    generations: Mapped[list["ModelGeneration"]] = relationship(
        "ModelGeneration", back_populates="family", order_by="ModelGeneration.release_date.desc()"
    )


class ModelGeneration(Base):
    """A specific model generation: e.g. 'Claude 3.5 Sonnet', 'GPT-4o'"""
    __tablename__ = "model_generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("model_families.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version_label: Mapped[Optional[str]] = mapped_column(String)
    release_date: Mapped[Optional[date]] = mapped_column(Date)
    parameter_count: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    family: Mapped["ModelFamily"] = relationship("ModelFamily", back_populates="generations")
    document: Mapped[Optional["Document"]] = relationship("Document")
    eval_results: Mapped[list["EvalResult"]] = relationship("EvalResult", back_populates="generation")
