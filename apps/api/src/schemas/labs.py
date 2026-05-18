"""Response schemas for the /api/v1/labs router.

Previously the three lab endpoints returned `response_model=dict` /
`response_model=list[dict]`, which meant OpenAPI docs and the TypeScript
frontend had no contract to validate against. These shapes formalize
what the handlers already return.
"""
from typing import Optional

from pydantic import BaseModel

from .document import LabRead


class LabSummary(LabRead):
    """A row in `GET /api/v1/labs` — lab core fields plus document count."""

    document_count: int


class LabDocumentItem(BaseModel):
    """Minimal document shape for the documents list nested under a lab."""

    id: int
    slug: str
    title: str
    doc_type: str


class LabDetail(LabRead):
    """`GET /api/v1/labs/{slug}` — lab core fields plus its documents."""

    documents: list[LabDocumentItem] = []


class LabCoveragePoint(BaseModel):
    """One row of the `GET /api/v1/labs/{slug}/coverage` heatmap.

    `score` is the max similarity any document on the lab has against the
    category embedding (0.0 if uncovered). `coverage_depth` is the embedder's
    qualitative band (`strong` / `moderate` / `weak` / `none`).
    """

    slug: str
    name: str
    score: float
    coverage_depth: str
