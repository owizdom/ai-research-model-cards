from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, computed_field


# Fields the EvalCards paper (Section 4.2) treats as the minimal-reproducibility
# sub-schema. Our equivalent: what was evaluated rather than how it was sampled
# (the paper checks temperature/max_tokens; we check shot_count/method/language/
# training_state). Same intent — surface what's missing as content.
_REPRODUCIBILITY_FIELDS: tuple[str, ...] = (
    "shot_count", "method", "language", "training_state",
)
# Treat these as "not really reported" even when the column is non-null —
# the extractor emits them as fallback strings rather than actual disclosures.
_NULL_EQUIVALENT_VALUES: dict[str, set] = {
    "method": {"none"},
    "training_state": {"unknown"},
}


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


class ReproducibilityFlags(BaseModel):
    """Per-result reproducibility signal (EvalCards paper Section 4.2).

    Counts how many of the four method/setup fields are actually reported.
    A row with `score = 1.0` is fully reproducible on these axes; a row at
    `0.0` is a bare score with no methodology disclosed.
    """
    has_shot_count: bool
    has_method: bool
    has_language: bool
    has_training_state: bool
    missing_fields: list[str]
    populated_count: int
    total_count: int = 4
    score: float


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

    @computed_field
    @property
    def reproducibility(self) -> ReproducibilityFlags:
        """Derived per-row reproducibility signal. Computed on serialization."""
        present = {}
        for field in _REPRODUCIBILITY_FIELDS:
            value = getattr(self, field)
            null_equiv = _NULL_EQUIVALENT_VALUES.get(field, set())
            present[field] = value is not None and value not in null_equiv
        missing = [k for k, ok in present.items() if not ok]
        populated = sum(present.values())
        return ReproducibilityFlags(
            has_shot_count=present["shot_count"],
            has_method=present["method"],
            has_language=present["language"],
            has_training_state=present["training_state"],
            missing_fields=missing,
            populated_count=populated,
            total_count=len(_REPRODUCIBILITY_FIELDS),
            score=populated / len(_REPRODUCIBILITY_FIELDS),
        )


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


class EvalsByDocumentResponse(BaseModel):
    """Response shape for GET /api/v1/evals/results/by-document/{id}.

    Pinning this schema makes the OpenAPI docs accurately advertise the
    nested EvalResultRead + ReproducibilityFlags shape, which previously
    rendered as an untyped object because the route returned a raw dict.
    """
    document_id: int
    title: Optional[str] = None
    lab_name: Optional[str] = None
    version_id: Optional[int] = None
    evals: list[EvalResultRead] = []


class ExtractionTriggerResponse(BaseModel):
    """Response shape for POST /api/v1/evals/extract/{version_id}.

    The endpoint enqueues a Redis job and returns 202. The not-found path
    now raises HTTPException(404) rather than returning an error dict —
    cleaner contract, single response shape.
    """
    version_id: int
    status: str


# ─── Divergence detection (EvalCards Section 4.2 comparability signal) ───────

class DivergentReport(BaseModel):
    """One contributing row inside a divergent (benchmark, model) group."""
    eval_id: int
    document_id: int
    document_title: Optional[str] = None
    lab_slug: Optional[str] = None
    score: float
    variant: str
    shot_count: Optional[int] = None
    method: Optional[str] = None
    language: Optional[str] = None
    training_state: Optional[str] = None
    is_self_reported: bool


class DivergentGroup(BaseModel):
    """A (benchmark, model_name) pair whose reports disagree above the
    configured threshold. Lists every contributing report plus the
    structured signals readers need to judge whether the disagreement
    reflects a real measurement difference or just a setup difference."""
    benchmark_slug: str
    benchmark_name: str
    model_name: str
    report_count: int
    score_min: float
    score_max: float
    score_spread: float
    cross_party: bool
    differing_fields: list[str]
    reports: list[DivergentReport]
    caveat: Optional[str] = None


class DivergenceSummary(BaseModel):
    """Aggregate stats for the corpus at the configured threshold."""
    threshold: float
    total_pairs_scanned: int
    divergent_pairs: int
    cross_party_divergent_pairs: int
    avg_spread_among_divergent: float


class DivergenceResponse(BaseModel):
    """Response for GET /api/v1/evals/divergence.

    Implements the EvalCards paper's comparability signal at the granularity
    of (benchmark_slug, model_name) tuples. Without metric-path
    differentiation (paper Section 3.2), some groups will be flagged that
    actually reflect different scoring rules rather than measurement
    disagreement — DivergentGroup.caveat surfaces that limitation in-band.
    """
    summary: DivergenceSummary
    groups: list[DivergentGroup]
    returned: int
