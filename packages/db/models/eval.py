from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String, Float, Integer, Boolean, ForeignKey, Text,
    DateTime, JSON, func, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base

if TYPE_CHECKING:
    from .model_family import ModelGeneration
    from .document import DocumentVersion


class BenchmarkDefinition(Base):
    """Registry of known benchmarks: MMLU, HumanEval, GSM8K, etc."""
    __tablename__ = "benchmark_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    metric_name: Mapped[Optional[str]] = mapped_column(String)
    metric_unit: Mapped[Optional[str]] = mapped_column(String)
    higher_is_better: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String)
    aliases: Mapped[Optional[dict]] = mapped_column(JSON)
    score_min: Mapped[Optional[float]] = mapped_column(Float)
    score_max: Mapped[Optional[float]] = mapped_column(Float)
    parent_slug: Mapped[Optional[str]] = mapped_column(String, index=True)
    industry_domain: Mapped[Optional[str]] = mapped_column(String, index=True)


class EvalResult(Base):
    """A single benchmark score extracted from a model card."""
    __tablename__ = "eval_results"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id", "generation_id", "benchmark_id", "variant", "model_name",
            name="uq_eval_result",
        ),
        Index("ix_eval_results_benchmark", "benchmark_id"),
        Index("ix_eval_results_generation", "generation_id"),
        Index("ix_eval_results_version", "document_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False,
    )
    generation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("model_generations.id", ondelete="SET NULL"),
    )
    benchmark_id: Mapped[int] = mapped_column(
        ForeignKey("benchmark_definitions.id", ondelete="CASCADE"), nullable=False,
    )
    score: Mapped[Optional[float]] = mapped_column(Float)
    variant: Mapped[str] = mapped_column(String, default="default", nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String)
    state: Mapped[Optional[str]] = mapped_column(String, index=True)
    shot_count: Mapped[Optional[int]] = mapped_column(Integer)
    method: Mapped[Optional[str]] = mapped_column(String)
    language: Mapped[Optional[str]] = mapped_column(String)
    training_state: Mapped[Optional[str]] = mapped_column(String)
    extraction_protocol_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    score_details: Mapped[Optional[dict]] = mapped_column(JSON)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float)
    is_self_reported: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String, default="model_card", nullable=False)
    external_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("external_eval_sources.id", ondelete="SET NULL"),
    )
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document_version: Mapped["DocumentVersion"] = relationship("DocumentVersion")
    generation: Mapped[Optional["ModelGeneration"]] = relationship("ModelGeneration", back_populates="eval_results")
    benchmark: Mapped["BenchmarkDefinition"] = relationship("BenchmarkDefinition")


class ExtractionRun(Base):
    """Track extraction runs for auditability."""
    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    model_used: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    evals_extracted: Mapped[Optional[int]] = mapped_column(Integer)
    raw_output: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
