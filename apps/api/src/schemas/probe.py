from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProbeRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    probe_key: str
    prompt: str
    category: str
    subcategory: Optional[str] = None
    expected_behavior: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool


class SlantScoreRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    composite_slant: Optional[float] = None
    embedding_slant: Optional[float] = None
    political_valence: Optional[float] = None
    moral_foundations_care: Optional[float] = None
    moral_foundations_fairness: Optional[float] = None
    moral_foundations_loyalty: Optional[float] = None
    moral_foundations_authority: Optional[float] = None
    moral_foundations_purity: Optional[float] = None
    confidence: Optional[float] = None
    scored_at: datetime


class ProbeResponseRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    probe_id: Optional[int] = None
    model_slug: str
    model_id: str
    prompt_text: str
    response_text: Optional[str] = None
    error: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    recorded_at: datetime
    probe: Optional[ProbeRead] = None
    slant_score: Optional[SlantScoreRead] = None


class ProbeRunSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    triggered_by: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    probe_count: Optional[int] = None
    model_count: Optional[int] = None
    status: str


class ProbeRunDetail(ProbeRunSummary):
    responses: list[ProbeResponseRead] = []


class RunProbesRequest(BaseModel):
    probe_ids: Optional[list[int]] = None
    model_slugs: Optional[list[str]] = None
