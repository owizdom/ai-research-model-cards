"""Smoke tests for the /api/v1/labs response schemas.

The /api/v1/labs router historically used response_model=dict, which meant
nothing validated the shape we returned. These tests pin the contract: any
future field rename or accidental drop breaks the suite.

We do not exercise the route handlers (those need a DB) — we exercise the
schemas they emit, with payloads matching what the handlers actually build.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.labs import LabCoveragePoint, LabDetail, LabDocumentItem, LabSummary


def _lab_core() -> dict:
    return {
        "id": 1,
        "slug": "anthropic",
        "name": "Anthropic",
        "website": "https://www.anthropic.com",
        "color_hex": "#D4791A",
    }


def test_lab_summary_accepts_handler_shape():
    """list_labs() returns lab core fields + document_count."""
    s = LabSummary(**_lab_core(), document_count=20)
    assert s.document_count == 20
    assert s.slug == "anthropic"


def test_lab_summary_requires_document_count():
    """Dropping document_count is the bug we'd most likely regress."""
    with pytest.raises(ValidationError):
        LabSummary(**_lab_core())


def test_lab_detail_with_documents():
    """get_lab() returns lab core + a documents list of LabDocumentItem."""
    d = LabDetail(
        **_lab_core(),
        documents=[
            LabDocumentItem(id=12, slug="anthropic_opus47_card",
                            title="Claude Opus 4.7 System Card", doc_type="model_card"),
        ],
    )
    assert len(d.documents) == 1
    assert d.documents[0].doc_type == "model_card"


def test_lab_detail_documents_defaults_to_empty_list():
    """A lab with no docs (rare but possible at fresh seed) shouldn't 500."""
    d = LabDetail(**_lab_core())
    assert d.documents == []


def test_lab_coverage_point_accepts_score_and_depth():
    """get_lab_coverage() returns one row per top-level taxonomy category."""
    p = LabCoveragePoint(
        slug="dual_use",
        name="Dual Use",
        score=0.4732,
        coverage_depth="moderate",
    )
    assert p.score == pytest.approx(0.4732)
    assert p.coverage_depth == "moderate"


def test_lab_coverage_point_uncovered_uses_none_string():
    """The handler emits 'none' (not null) when a category has no mapping."""
    p = LabCoveragePoint(slug="x", name="X", score=0.0, coverage_depth="none")
    assert p.coverage_depth == "none"
