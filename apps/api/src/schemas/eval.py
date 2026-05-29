from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class BenchmarkPolicyNote(BaseModel):
    """Plain-language Policy Note attached to a benchmark.

    Mirrors Figure 3 of the EvalCards paper (NeurIPS 2026): the four
    narrative fields a non-technical reader needs to interpret a score,
    plus topic tags and outbound source links. All fields optional; the
    UI degrades to "no policy note available" when absent.
    """
    measures: Optional[str] = None
    caveat: Optional[str] = None
    intended_for: Optional[str] = None
    how_to_read: Optional[str] = None
    topic_tags: list[str] = []
    sources: dict[str, str] = {}


class BenchmarkRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    slug: str
    name: str
    category: str
    description: Optional[str] = None
    metric_name: Optional[str] = None
    metric_unit: Optional[str] = None
    higher_is_better: bool
    source_url: Optional[str] = None
    aliases: Optional[list[str]] = None
    score_min: Optional[float] = None
    score_max: Optional[float] = None
    policy_note: Optional[BenchmarkPolicyNote] = None


class GenerationBrief(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    slug: str
    name: str
    version_label: Optional[str] = None


class EvalResultRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    benchmark: BenchmarkRead
    generation: Optional[GenerationBrief] = None
    score: Optional[float] = None
    variant: str
    model_name: Optional[str] = None
    state: Optional[str] = None
    shot_count: Optional[int] = None
    method: Optional[str] = None
    language: Optional[str] = None
    training_state: Optional[str] = None
    extraction_protocol_version: int = 1
    score_details: Optional[dict] = None
    extraction_confidence: Optional[float] = None
    is_self_reported: bool
    source_type: str
    extracted_at: datetime


class FamilyRead(BaseModel):
    id: int
    slug: str
    name: str
    lab_slug: str
    generation_count: int


class GenerationRead(BaseModel):
    id: int
    slug: str
    name: str
    version_label: Optional[str] = None
    release_date: Optional[date] = None
    parameter_count: Optional[str] = None
    eval_count: int
    document_id: Optional[int] = None


class FamilyDetail(FamilyRead):
    generations: list[GenerationRead]


class ComparisonResult(BaseModel):
    family_slug: str
    family_name: str
    benchmarks: list[str]
    generations: list[str]
    matrix: dict[str, dict[str, Optional[float]]]


class TimelinePoint(BaseModel):
    period: str
    lab_slug: str
    eval_count: int
    document_count: int


class PerCardEvalPoint(BaseModel):
    document_id: int
    document_title: str
    lab_slug: str
    version_date: str
    eval_count: int


class CategoryTimelinePoint(BaseModel):
    document_slug: str
    document_title: str
    lab_slug: str
    lab_name: str
    benchmark_category: str
    eval_count: int


class FragmentationBucket(BaseModel):
    n_labs: int
    count: int
    slugs: list[str]
    names: dict[str, str]


class FragmentationView(BaseModel):
    total: int
    one_lab_count: int
    pct_unique: int
    histogram: list[FragmentationBucket]


class LabUniqueness(BaseModel):
    lab_slug: str
    lab_name: str
    total_reported: int
    only_them_count: int
    only_them: list[dict]


class FragmentationResponse(BaseModel):
    labs: list[str]
    raw: FragmentationView
    families: FragmentationView
    by_lab: list[LabUniqueness]


class ExtractionRunRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    document_version_id: int
    model_used: str
    status: str
    evals_extracted: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
