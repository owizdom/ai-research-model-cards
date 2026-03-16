from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, Boolean, ForeignKey, Text, ARRAY, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from ..session import Base

if TYPE_CHECKING:
    from .document import DocumentVersion


class TaxonomyCategory(Base):
    __tablename__ = "taxonomy_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("taxonomy_categories.id"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768))

    parent: Mapped[Optional["TaxonomyCategory"]] = relationship(
        "TaxonomyCategory", remote_side="TaxonomyCategory.id", back_populates="children"
    )
    children: Mapped[list["TaxonomyCategory"]] = relationship(
        "TaxonomyCategory", back_populates="parent", foreign_keys=[parent_id]
    )
    mappings: Mapped[list["DocumentTaxonomyMapping"]] = relationship(
        "DocumentTaxonomyMapping", back_populates="category"
    )


class DocumentTaxonomyMapping(Base):
    __tablename__ = "document_taxonomy_mappings"
    __table_args__ = (
        Index("ix_dtm_category_covered", "taxonomy_category_id", "is_covered"),
    )

    document_version_id: Mapped[int] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), primary_key=True
    )
    taxonomy_category_id: Mapped[int] = mapped_column(
        ForeignKey("taxonomy_categories.id", ondelete="CASCADE"), primary_key=True
    )
    similarity_score: Mapped[Optional[float]] = mapped_column(Float)
    is_covered: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)
    coverage_depth: Mapped[Optional[str]] = mapped_column(String)

    document_version: Mapped["DocumentVersion"] = relationship("DocumentVersion", back_populates="taxonomy_mappings")
    category: Mapped["TaxonomyCategory"] = relationship("TaxonomyCategory", back_populates="mappings")
