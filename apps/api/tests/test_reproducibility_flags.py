"""Tests for the per-EvalResult ReproducibilityFlags computed field.

Phase 2 of the EvalCards alignment. The signal counts how many of
{shot_count, method, language, training_state} were actually reported,
treating extractor fallback strings ("none", "unknown") as not-reported.
Sister-pinned to Phase 1's BenchmarkPolicyNote tests.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from schemas.eval import (
    BenchmarkRead, EvalResultRead, ReproducibilityFlags,
    EvalsByDocumentResponse, ExtractionTriggerResponse,
)


def _benchmark() -> BenchmarkRead:
    return BenchmarkRead(id=1, slug="mmlu", name="MMLU", category="knowledge", higher_is_better=True)


def _eval(**overrides) -> EvalResultRead:
    defaults = dict(
        id=1,
        benchmark=_benchmark(),
        variant="default",
        is_self_reported=True,
        source_type="model_card",
        extracted_at=datetime(2026, 5, 29, 12, 0, 0),
    )
    defaults.update(overrides)
    return EvalResultRead(**defaults)


def test_fully_reproducible_row_scores_one():
    e = _eval(shot_count=5, method="CoT", language="English", training_state="RLHF")
    r = e.reproducibility
    assert r.populated_count == 4
    assert r.score == 1.0
    assert r.missing_fields == []
    assert r.has_shot_count and r.has_method and r.has_language and r.has_training_state


def test_bare_row_scores_zero():
    """The common case: a score with no methodology disclosed. Should clearly
    signal that all four reproducibility axes are absent."""
    e = _eval()
    r = e.reproducibility
    assert r.populated_count == 0
    assert r.score == 0.0
    assert set(r.missing_fields) == {"shot_count", "method", "language", "training_state"}


def test_extractor_fallback_strings_treated_as_not_reported():
    """method='none' and training_state='unknown' are extractor placeholders,
    not real disclosures. They should count as missing for reproducibility
    purposes — surfacing the gap rather than hiding it behind a string."""
    e = _eval(shot_count=5, method="none", training_state="unknown")
    r = e.reproducibility
    assert r.populated_count == 1  # only shot_count
    assert r.score == 0.25
    assert "method" in r.missing_fields
    assert "training_state" in r.missing_fields
    assert "shot_count" not in r.missing_fields
    assert r.has_method is False
    assert r.has_training_state is False


def test_partial_disclosure_scores_proportionally():
    """A row with 2 of 4 fields filled scores exactly 0.5."""
    e = _eval(shot_count=0, method="CoT")
    r = e.reproducibility
    assert r.populated_count == 2
    assert r.score == 0.5
    assert set(r.missing_fields) == {"language", "training_state"}


def test_zero_shot_is_a_real_disclosure():
    """shot_count=0 (zero-shot) is a legitimate disclosure, not a missing value."""
    e = _eval(shot_count=0)
    assert e.reproducibility.has_shot_count is True


def test_reproducibility_appears_in_model_dump():
    """The computed field must serialize — that's how the frontend receives it.
    A plain @property would not show up in .model_dump()."""
    e = _eval(shot_count=5)
    dumped = e.model_dump()
    assert "reproducibility" in dumped
    assert dumped["reproducibility"]["score"] == 0.25
    assert dumped["reproducibility"]["total_count"] == 4


def test_reproducibility_flags_is_constructible_directly():
    """Sanity: the schema isn't only buildable via the computed field path."""
    r = ReproducibilityFlags(
        has_shot_count=True, has_method=False, has_language=True, has_training_state=False,
        missing_fields=["method", "training_state"], populated_count=2, score=0.5,
    )
    assert r.total_count == 4  # default


def test_evals_by_document_response_carries_reproducibility():
    """The container response must expose nested EvalResultRead, which in
    turn must expose reproducibility — this is what the OpenAPI components
    block needs in order to document ReproducibilityFlags at all."""
    e = _eval(shot_count=5, method="CoT")
    resp = EvalsByDocumentResponse(
        document_id=24,
        title="Llama 3.1 Technical Paper",
        lab_name="Meta AI",
        version_id=42,
        evals=[e],
    )
    dumped = resp.model_dump()
    assert dumped["document_id"] == 24
    assert dumped["evals"][0]["reproducibility"]["populated_count"] == 2
    assert "method" not in dumped["evals"][0]["reproducibility"]["missing_fields"]


def test_evals_by_document_response_defaults_are_safe():
    """When the doc isn't found we early-return with only document_id set —
    the schema must tolerate that (None title, empty evals list)."""
    resp = EvalsByDocumentResponse(document_id=999)
    assert resp.title is None
    assert resp.lab_name is None
    assert resp.version_id is None
    assert resp.evals == []


def test_extraction_trigger_response_shape():
    resp = ExtractionTriggerResponse(version_id=42, status="queued")
    assert resp.version_id == 42
    assert resp.status == "queued"
