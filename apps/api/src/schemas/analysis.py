from pydantic import BaseModel


class IntersectionSet(BaseModel):
    labs: list[str]
    categories: list[str]
    count: int


class IntersectionResult(BaseModel):
    matrix: dict[str, dict[str, float]]
    covered_by_all: list[str]
    covered_by_none: list[str]
    unique_to: dict[str, list[str]]
    intersection_sets: list[IntersectionSet]
    lab_slugs: list[str]
    category_names: dict[str, str]


class TemporalPoint(BaseModel):
    period_start: str
    period_end: str
    covered_by_all_count: int
    total_categories: int
    convergence_score: float


class DriftResult(BaseModel):
    model_slug: str
    probe_id: int
    n_samples: int
    mean_slant: float
    std_slant: float
    trend: str
    p_value: float
    tau: float
    is_significant: bool
    direction: str
    time_series: list[dict]


class AsymmetryResult(BaseModel):
    model_slug: str
    probe_a_key: str
    probe_b_key: str
    trump_slant: float
    biden_slant: float
    asymmetry_score: float
    interpretation: str


class SlantSummary(BaseModel):
    model_scores: list[dict]
    probe_scores: list[dict]
