"""Regression tests for ``_parse_extraction_json`` in ``eval_extractor``.

Locks in tolerance for the real-world shapes the Claude CLI emits, including
the bug we fixed where the CLI opens a ```json fence but never closes it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from extractor.parse import parse_extraction_json as _parse_extraction_json


FIXTURES = Path(__file__).parent / "fixtures"


def test_plain_json_object_parses():
    raw = '{"results": [{"benchmark_name": "MMLU", "score": 86.8}]}'
    out = _parse_extraction_json(raw)
    assert isinstance(out, dict)
    assert out["results"][0]["benchmark_name"] == "MMLU"
    assert out["results"][0]["score"] == 86.8


def test_closed_json_fence_parses():
    raw = (
        "```json\n"
        '{"results": [{"benchmark_name": "HumanEval", "score": 92.0}]}\n'
        "```"
    )
    out = _parse_extraction_json(raw)
    assert isinstance(out, dict)
    assert out["results"][0]["benchmark_name"] == "HumanEval"


def test_unclosed_json_fence_parses():
    """THE BUG: Claude CLI sometimes emits an opening ```json with no close."""
    raw = (
        "```json\n"
        '{"results": [{"benchmark_name": "GSM8K", "score": 95.0}]}'
    )
    out = _parse_extraction_json(raw)
    assert isinstance(out, dict)
    assert out["results"][0]["benchmark_name"] == "GSM8K"
    assert out["results"][0]["score"] == 95.0


def test_prose_plus_fenced_json_parses():
    raw = (
        "Sure, here are the extracted results:\n\n"
        "```json\n"
        '{"results": [{"benchmark_name": "GPQA", "score": 59.4}]}\n'
        "```\n"
        "Let me know if you need anything else."
    )
    out = _parse_extraction_json(raw)
    assert isinstance(out, dict)
    assert out["results"][0]["benchmark_name"] == "GPQA"


def test_prose_plus_bare_json_parses_via_fallback():
    raw = (
        "Here are the results you asked for: "
        '{"results": [{"benchmark_name": "SWE-Bench", "score": 49.0}]} '
        "Hope that helps!"
    )
    out = _parse_extraction_json(raw)
    assert isinstance(out, dict)
    assert out["results"][0]["benchmark_name"] == "SWE-Bench"


def test_top_level_json_array_parses_as_list():
    raw = '[{"benchmark_name": "MATH", "score": 71.1}]'
    out = _parse_extraction_json(raw)
    assert isinstance(out, list)
    assert out[0]["benchmark_name"] == "MATH"


def test_empty_string_returns_empty_results():
    assert _parse_extraction_json("") == {"results": []}


def test_garbage_text_returns_empty_results():
    raw = "I could not find any benchmarks in this document, sorry."
    assert _parse_extraction_json(raw) == {"results": []}


def test_real_llama3_unclosed_fence_parses_to_225_items():
    """Smoking gun: the real 42 KB Llama-3.1 raw_output that triggered the
    bug. Must parse cleanly and yield exactly 225 benchmark items."""
    fixture = FIXTURES / "llama3_unclosed_fence.txt"
    raw = fixture.read_text()
    out = _parse_extraction_json(raw)

    assert isinstance(out, dict), "must recover a dict, not fall through to []"
    assert "results" in out, "parsed dict must have 'results' key"
    assert len(out["results"]) == 225, (
        f"expected 225 items, got {len(out['results'])} — "
        "if this changed, either the fixture drifted or the parser regressed"
    )
    first = out["results"][0]
    assert "benchmark_name" in first
    assert "score" in first


_NOISE_SAMPLES = [
    "", "   ", "not json at all",
    "```", "```json", "```json\n", "```json\n{", "```json\n{}",
    "```json\n{}\n```", "```\n{}\n```",
    "{", "}", "[", "]", "{}", "[]",
    '{"results":[]}',
    '{"results": [{"benchmark_name":"x","score":1}]}',
    'prefix {"results":[]} suffix',
    '```json\n{"results":[{"a":1}]}',
    '```json\n{"results":[{"a":1}]}\n```',
    "```\n[1,2,3]\n```",
    "```json\n[1,2,3]",
    "garbage\n```json\n{}\n```\nmore garbage",
    '{"results": [' + ",".join(['{"benchmark_name":"b","score":0}'] * 50) + "]}",
    "```json\n" + '{"results": [' + ",".join(['{"benchmark_name":"b","score":0}'] * 50) + "]}",
    "NULL", "true", "42", '"just a string"',
    '{"nested": {"deeper": {"even": {"deeper": [1,2,3]}}}}',
    '```json\n{"a":1, "b":2}\n```\n```json\n{"c":3}\n```',
]


@pytest.mark.parametrize("raw", _NOISE_SAMPLES)
def test_parser_never_crashes_on_weird_input(raw):
    """Core invariant: the parser must return dict|list for ANY string input."""
    out = _parse_extraction_json(raw)
    assert isinstance(out, (dict, list))


try:
    from hypothesis import given, settings, strategies as st
except ImportError:
    pass
else:
    @settings(max_examples=100, deadline=None)
    @given(
        prefix=st.text(max_size=50),
        obj=st.recursive(
            st.one_of(
                st.none(),
                st.booleans(),
                st.integers(min_value=-1000, max_value=1000),
                st.floats(allow_nan=False, allow_infinity=False, width=32),
                st.text(max_size=20),
            ),
            lambda children: st.one_of(
                st.lists(children, max_size=5),
                st.dictionaries(st.text(max_size=10), children, max_size=5),
            ),
            max_leaves=10,
        ),
        suffix=st.text(max_size=50),
        fence=st.sampled_from(["", "```", "```json\n", "```json"]),
        closing=st.sampled_from(["", "\n```", "```"]),
    )
    def test_hypothesis_parser_never_crashes(prefix, obj, suffix, fence, closing):
        body = json.dumps(obj)
        raw = f"{prefix}{fence}{body}{closing}{suffix}"
        out = _parse_extraction_json(raw)
        assert isinstance(out, (dict, list))
