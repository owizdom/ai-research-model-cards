from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from ..session import Base

if TYPE_CHECKING:
    from .slant import SlantScore


class ProbeDefinition(Base):
    __tablename__ = "probe_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    probe_key: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String)
    expected_behavior: Mapped[Optional[str]] = mapped_column(String)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    responses: Mapped[list["ProbeResponse"]] = relationship("ProbeResponse", back_populates="probe")


class ProbeRun(Base):
    __tablename__ = "probe_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    triggered_by: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    probe_count: Mapped[Optional[int]] = mapped_column(Integer)
    model_count: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False, index=True)

    responses: Mapped[list["ProbeResponse"]] = relationship(
        "ProbeResponse", back_populates="run", cascade="all, delete-orphan"
    )


class ProbeResponse(Base):
    __tablename__ = "probe_responses"
    __table_args__ = (
        Index("ix_probe_responses_model_probe", "model_slug", "probe_id"),
        Index("ix_probe_responses_recorded_at", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("probe_runs.id", ondelete="SET NULL"), index=True)
    probe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("probe_definitions.id", ondelete="SET NULL"), index=True)
    model_slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768))

    run: Mapped[Optional["ProbeRun"]] = relationship("ProbeRun", back_populates="responses")
    probe: Mapped[Optional["ProbeDefinition"]] = relationship("ProbeDefinition", back_populates="responses")
    slant_score: Mapped[Optional["SlantScore"]] = relationship(
        "SlantScore", back_populates="response", uselist=False
    )
