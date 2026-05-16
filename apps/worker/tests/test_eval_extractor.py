"""Pin the behaviour of the content-section selector.

The Opus 4.7 incident (2026-05-15) was caused entirely by `_extract_eval_sections`
picking the wrong region of a 232-page card: keyword density landed on the
CBRN safety section, while the canonical capability table sat at char 368k —
past the 30 KB window. Anchor boosting + two-window split was the fix.

These tests freeze that behaviour so the next person tweaking the scorer
sees what regressing looks like before they merge.
"""
from __future__ import annotations


from extractor.eval_extractor import (
    _SECTION_HEADER_RE,
    _extract_eval_sections,
    _score_block,
)
from packages.pipeline_config import ANCHOR_BOOST, LONG_DOC_THRESHOLD


# ── _score_block ─────────────────────────────────────────────────────────────


def test_score_block_keyword_match_beats_narrative():
    """A block stuffed with benchmark keywords outscores a plain prose block."""
    bench_block = "MMLU accuracy 87.6%. SWE-bench Verified pass@1 reasoning."
    prose_block = "Introduction. This document describes the model release."
    assert _score_block(bench_block) > _score_block(prose_block)


def test_score_block_anchor_adds_at_least_anchor_boost():
    """A block containing a capability anchor jumps by ≥ ANCHOR_BOOST."""
    plain = "Lots of benchmark, evaluation, score keywords here."
    anchored = plain + "\n\nCapability evaluation summary follows."
    delta = _score_block(anchored) - _score_block(plain)
    assert delta >= ANCHOR_BOOST


def test_score_block_section_header_boost():
    """Numbered headers like '8.1 Capability evaluation summary' get the bonus.

    Two-window aside: this is what guarantees the capability table beats out
    a keyword-dense narrative block at scoring time."""
    plain = "Some prose about benchmarks and evaluation."
    headered = "8.1 Capability evaluation summary\n\n" + plain
    assert _SECTION_HEADER_RE.search(headered) is not None
    assert _score_block(headered) > _score_block(plain)


# ── _extract_eval_sections ───────────────────────────────────────────────────


def _make_doc(*blocks: str, padding_lines: int = 0) -> str:
    """Join blocks with optional filler lines between them."""
    filler = ("\n" + "filler line.\n" * padding_lines) if padding_lines else ""
    return filler.join(blocks)


def test_short_doc_returns_eval_dense_block():
    """A short doc (< LONG_DOC_THRESHOLD) selects via keyword density alone."""
    intro = "## Introduction\n\n" + ("background. " * 30)
    evals = (
        "MMLU accuracy 86.4%\n"
        "GPQA Diamond accuracy 78.1%\n"
        "SWE-bench Verified pass@1 65.2%\n"
        "HumanEval pass@1 90.0%\n"
    )
    doc = _make_doc(intro, "\n\n", evals, padding_lines=0)
    assert len(doc) < LONG_DOC_THRESHOLD

    out = _extract_eval_sections(doc, max_chars=10_000)
    assert "MMLU accuracy 86.4%" in out
    # Narrative-only block can also appear but the eval block must be there.


def test_long_doc_two_window_split_finds_back_half_content():
    """For docs > LONG_DOC_THRESHOLD the budget is split so a capability table
    at the END of the doc is picked up, even when the safety section in the
    front half is keyword-denser. This is the Opus 4.7 regression case."""
    # Front half: a dense safety narrative with many EVAL_KEYWORDS hits but
    # NO capability table. Size: large enough that front + back > LONG_DOC_THRESHOLD.
    safety_block = "\n".join(
        f"safety eval red team capability bias toxicity benchmark line {i}"
        for i in range(1400)
    )
    # Back half: the canonical capability table — fewer raw keywords than
    # the safety block, but contains the anchor.
    capability_block = (
        "8.1 Capability evaluation summary\n\n"
        "Claude Opus 4.7 achieves 87.6% on SWE-bench Verified.\n"
        "GPQA Diamond: 94.2%. MMLU-Pro: 91.5%.\n"
    ) + ("filler ".join(["table"] * 50)) + "\n"

    doc = safety_block + "\n\n" + capability_block
    assert len(doc) > LONG_DOC_THRESHOLD

    out = _extract_eval_sections(doc, max_chars=30_000)
    assert "Capability evaluation summary" in out, (
        "two-window split must surface back-half capability anchor"
    )


def test_anchor_wins_over_pure_keyword_density():
    """When a small anchored block competes with a slightly keyword-denser
    narrative block of the same size, the anchored one ranks higher."""
    narrative = "benchmark evaluation accuracy score performance " * 30
    anchored = "Capability evaluation summary. MMLU 87. " * 5
    assert _score_block(anchored) > _score_block(narrative)


def test_empty_content_returns_empty_string():
    """Defensive: extractor should not crash on an empty doc."""
    assert _extract_eval_sections("", max_chars=10_000) == ""
