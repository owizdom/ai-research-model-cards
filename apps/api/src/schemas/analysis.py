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
