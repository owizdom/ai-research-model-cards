from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from ..session import Base


class ExternalEvalSource(Base):
    """Registry of 3rd-party eval sources: LMSYS Arena, Open LLM Leaderboard, etc."""
    __tablename__ = "external_eval_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    fetch_method: Mapped[str] = mapped_column(String, nullable=False)  # "api", "scrape", "csv"
    fetch_config: Mapped[Optional[dict]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
