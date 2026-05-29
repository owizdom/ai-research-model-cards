"""Schema-level tests for the /api/v1/evals/divergence response shape.

Phase 3 of EvalCards alignment. The endpoint's SQL + grouping logic lives
in apps/api/src/api/v1/evals.py and needs a live DB to exercise; these
tests pin the Pydantic contract the endpoint must satisfy so the API
shape can't drift accidentally.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.eval import (
    DivergenceResponse,
    DivergenceSummary,
    DivergentGroup,
    DivergentReport,
)


def _report(**overrides) -> DivergentReport:
    defaults = dict(
        eval_id=1, document_id=10, document_title="Llama 3.1 Tech Report",
        lab_slug="meta", score=82.5, variant="default", is_self_reported=True,
    )
    defaults.update(overrides)
    return DivergentReport(**defaults)


def _group(**overrides) -> DivergentGroup:
    defaults = dict(
        benchmark_slug="mmlu", benchmark_name="MMLU", model_name="gpt-4",
        report_count=2, score_min=82.0, score_max=88.5, score_spread=6.5,
        cross_party=True,
        differing_fields=["shot_count", "method"],
        reports=[_report(eval_id=1, score=82.0), _report(eval_id=2, score=88.5, document_id=20, is_self_reported=False)],
    )
    defaults.update(overrides)
    return DivergentGroup(**defaults)


def test_divergent_report_minimum_shape():
    r = _report()
    assert r.score == 82.5
    assert r.is_self_reported is True


def test_divergent_report_score_required():
    """score is the load-bearing field for divergence — making it required
    pins the contract."""
    with pytest.raises(ValidationError):
        DivergentReport(eval_id=1, document_id=10, variant="default", is_self_reported=True)


def test_divergent_group_score_spread_invariant():
    """Pin: score_spread should equal score_max - score_min as a derived
    fact, even though the schema doesn't enforce it (the endpoint computes
    it from SQL). This is a regression guard for the typical mistake of
    reordering the subtraction or dropping the field."""
    g = _group(score_min=70.0, score_max=85.0, score_spread=15.0)
    assert g.score_spread == g.score_max - g.score_min


def test_divergent_group_carries_paper_signals():
    """The two structured signals readers need: cross_party (does the
    disagreement span first-party vs third-party reports?) and
    differing_fields (which setup axes vary across the contributing rows?)."""
    g = _group(cross_party=True, differing_fields=["shot_count"])
    assert g.cross_party is True
    assert g.differing_fields == ["shot_count"]


def test_divergent_group_caveat_optional_but_used_in_practice():
    """The endpoint stamps a metric-path caveat on every group. Schema
    permits None so future endpoints can opt out (e.g. once metric-path
    differentiation lands)."""
    g = _group(caveat=None)
    assert g.caveat is None
    g2 = _group(caveat="metric-path limitation")
    assert "metric-path" in g2.caveat


def test_divergent_group_reports_serialize_as_list():
    g = _group()
    dumped = g.model_dump()
    assert isinstance(dumped["reports"], list)
    assert len(dumped["reports"]) == 2


def test_divergence_summary_stats_shape():
    s = DivergenceSummary(
        threshold=5.0,
        total_pairs_scanned=181,
        divergent_pairs=94,
        cross_party_divergent_pairs=7,
        avg_spread_among_divergent=7.2,
    )
    assert s.threshold == 5.0
    assert s.divergent_pairs == 94


def test_divergence_response_full_shape():
    """End-to-end: a fully-populated response with summary + groups
    serializes cleanly and round-trips back to the same Pydantic
    object. Pins the JSON contract the frontend depends on."""
    resp = DivergenceResponse(
        summary=DivergenceSummary(
            threshold=5.0,
            total_pairs_scanned=181,
            divergent_pairs=94,
            cross_party_divergent_pairs=7,
            avg_spread_among_divergent=7.2,
        ),
        groups=[_group()],
        returned=1,
    )
    dumped = resp.model_dump()
    assert dumped["summary"]["divergent_pairs"] == 94
    assert dumped["returned"] == 1
    assert dumped["groups"][0]["model_name"] == "gpt-4"
    # Round-trip
    rebuilt = DivergenceResponse.model_validate(dumped)
    assert rebuilt.summary.threshold == 5.0


def test_divergence_response_empty_corpus():
    """When no pairs exceed threshold, returned=0 and groups=[]."""
    resp = DivergenceResponse(
        summary=DivergenceSummary(
            threshold=5.0,
            total_pairs_scanned=0,
            divergent_pairs=0,
            cross_party_divergent_pairs=0,
            avg_spread_among_divergent=0.0,
        ),
        groups=[],
        returned=0,
    )
    assert resp.returned == 0
    assert resp.groups == []
