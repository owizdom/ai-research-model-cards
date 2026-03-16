from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Float, String, Integer, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..session import Base

if TYPE_CHECKING:
    from .probe import ProbeResponse


class SlantScore(Base):
    __tablename__ = "slant_scores"
    __table_args__ = (
        Index("ix_slant_scores_model_probe", "model_slug", "probe_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("probe_responses.id", ondelete="CASCADE"), unique=True, index=True
    )
    model_slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    probe_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    liberal_anchor_sim: Mapped[Optional[float]] = mapped_column(Float)
    conservative_anchor_sim: Mapped[Optional[float]] = mapped_column(Float)
    neutral_anchor_sim: Mapped[Optional[float]] = mapped_column(Float)
    embedding_slant: Mapped[Optional[float]] = mapped_column(Float)

    moral_foundations_care: Mapped[Optional[float]] = mapped_column(Float)
    moral_foundations_fairness: Mapped[Optional[float]] = mapped_column(Float)
    moral_foundations_loyalty: Mapped[Optional[float]] = mapped_column(Float)
    moral_foundations_authority: Mapped[Optional[float]] = mapped_column(Float)
    moral_foundations_purity: Mapped[Optional[float]] = mapped_column(Float)

    political_valence: Mapped[Optional[float]] = mapped_column(Float)
    composite_slant: Mapped[Optional[float]] = mapped_column(Float)
    confidence: Mapped[Optional[float]] = mapped_column(Float)

    response: Mapped[Optional["ProbeResponse"]] = relationship("ProbeResponse", back_populates="slant_score")
