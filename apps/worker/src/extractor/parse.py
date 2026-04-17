"""Tolerant JSON parser for LLM-emitted extraction output.

Separated from eval_extractor.py so the pure logic can be unit-tested
without pulling in litellm and the Claude CLI subprocess deps.
"""
from __future__ import annotations

import json
import re


def _try_load(s: str) -> dict | list | None:
    """json.loads but only accept container types; primitives aren't useful."""
    try:
        v = json.loads(s)
    except json.JSONDecodeError:
        return None
    return v if isinstance(v, (dict, list)) else None


def parse_extraction_json(raw: str) -> dict | list:
    """Tolerant JSON extractor for LLM output.

    Handles: plain JSON, fenced ```json blocks (closed OR unclosed — the CLI
    has been observed to emit an opening ```json without a closing ```), and
    prose wrappers by falling back to the outermost {...} or [...] span.

    Always returns a container (dict or list). Non-container JSON (e.g.
    bare literals like ``true``, ``42``) collapses to ``{"results": []}``
    because downstream code expects a results structure.
    """
    if not raw:
        return {"results": []}

    got = _try_load(raw)
    if got is not None:
        return got

    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        got = _try_load(m.group(1))
        if got is not None:
            return got

    stripped = raw.strip()
    fence = re.match(r"^```(?:json)?\s*\n?", stripped)
    if fence:
        stripped = stripped[fence.end():].rstrip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].rstrip()
        got = _try_load(stripped)
        if got is not None:
            return got

    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = raw.find(open_ch)
        end = raw.rfind(close_ch)
        if start >= 0 and end > start:
            got = _try_load(raw[start:end + 1])
            if got is not None:
                return got

    return {"results": []}
