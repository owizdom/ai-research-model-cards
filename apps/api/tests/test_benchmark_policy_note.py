"""Pydantic-shape tests for BenchmarkPolicyNote + the BenchmarkRead extension.

Mirrors test_labs_schemas.py: schema-level, no DB or TestClient. Pins the
EvalCards-paper-aligned shape so a future "just store it as a dict" refactor
breaks the suite loudly instead of silently regressing /docs.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.eval import BenchmarkPolicyNote, BenchmarkRead


def _bench_core() -> dict:
    return {
        "id": 1,
        "slug": "mmlu",
        "name": "MMLU",
        "category": "knowledge",
        "higher_is_better": True,
    }


def _policy_note() -> dict:
    return {
        "measures": "57 multiple-choice exams spanning STEM, humanities, etc.",
        "caveat": "Saturated above 88%; documented contamination.",
        "intended_for": "Aggregate-knowledge comparisons between LLMs.",
        "how_to_read": "Higher is better.",
        "topic_tags": ["stem", "humanities"],
        "sources": {"paper": "https://arxiv.org/abs/2009.03300"},
    }


def test_policy_note_accepts_paper_shape():
    pn = BenchmarkPolicyNote(**_policy_note())
    assert pn.measures.startswith("57 ")
    assert pn.topic_tags == ["stem", "humanities"]
    assert pn.sources["paper"].startswith("https://")


def test_policy_note_all_fields_optional():
    """A benchmark with no fields filled in is still a valid policy note —
    the four narrative fields are individually optional. The UI handles
    rendering only what's populated."""
    pn = BenchmarkPolicyNote()
    assert pn.measures is None
    assert pn.caveat is None
    assert pn.topic_tags == []
    assert pn.sources == {}


def test_benchmark_read_with_policy_note():
    """BenchmarkRead carries the nested PolicyNote when present."""
    br = BenchmarkRead(**_bench_core(), policy_note=_policy_note())
    assert br.policy_note is not None
    assert br.policy_note.measures.startswith("57 ")


def test_benchmark_read_without_policy_note():
    """The common case — most benchmarks won't have notes yet. Field is None,
    not missing; clients should rely on null-coalescing in the UI."""
    br = BenchmarkRead(**_bench_core())
    assert br.policy_note is None


def test_benchmark_read_exposes_newly_added_fields():
    """Regression-pin the API-surface extension: source_url, aliases,
    score_min/max were on the SQLAlchemy model but weren't exposed via
    the BenchmarkRead schema before Phase 1."""
    br = BenchmarkRead(
        **_bench_core(),
        source_url="https://arxiv.org/abs/2009.03300",
        aliases=["MMLU (5-shot)"],
        score_min=0.0,
        score_max=100.0,
    )
    assert br.source_url == "https://arxiv.org/abs/2009.03300"
    assert br.aliases == ["MMLU (5-shot)"]
    assert br.score_min == 0.0
    assert br.score_max == 100.0


def test_policy_note_topic_tags_must_be_strings():
    """Light type guard — paper Figure 3 tags are lowercase short strings."""
    with pytest.raises(ValidationError):
        BenchmarkPolicyNote(topic_tags=[123, "stem"])


def test_policy_note_sources_must_be_string_to_string():
    """Sources is a flat {label: url} map — no nested structure."""
    with pytest.raises(ValidationError):
        BenchmarkPolicyNote(sources={"paper": ["a", "b"]})
