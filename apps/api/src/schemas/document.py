from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class LabRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    slug: str
    name: str
    website: Optional[str] = None
    color_hex: Optional[str] = None


class TaxonomyCategoryRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    slug: str
    name: str
    description: Optional[str] = None


class TaxonomyMappingRead(BaseModel):
    model_config = {"from_attributes": True}
    category: TaxonomyCategoryRead
    similarity_score: Optional[float] = None
    is_covered: Optional[bool] = None
    coverage_depth: Optional[str] = None


class DocumentVersionSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    version_date: date
    word_count: Optional[int] = None
    wayback_url: Optional[str] = None
    fetched_at: datetime


class DocumentVersionDetail(DocumentVersionSummary):
    content_md: str
    taxonomy_mappings: list[TaxonomyMappingRead] = []


class DocumentSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    slug: str
    title: str
    doc_type: str
    source_url: Optional[str] = None
    updated_at: datetime
    lab: Optional[LabRead] = None


class DocumentDetail(DocumentSummary):
    versions: list[DocumentVersionSummary] = []


class WordCountTimelinePoint(BaseModel):
    lab_slug: str
    lab_name: str
    document_slug: str
    document_title: str
    version_date: str
    word_count: int


class DiffResult(BaseModel):
    version_a_id: int
    version_b_id: int
    unified_diff: str
    lines_added: int
    lines_removed: int
    words_added: int
    words_removed: int
    change_percent: float
