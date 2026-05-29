"""Parse free-form `variant` strings into the structured EvalResult columns.

The extractor historically stashed setup info (shot count, prompting method,
language, training state) inside the legacy `variant` string when it
couldn't or didn't break those out into the dedicated columns. Once the
columns existed they were never backfilled — most rows have a populated
variant string and NULL shot_count / method / language / training_state.

This is purely a parser. It's used by:
  - scripts/backfill_variant_fields.py — one-shot backfill against prod
  - apps/worker/src/extractor/eval_extractor.py — eventually, called
    post-extraction so every new row carries structured fields

Design principles:
  1. Conservative — match only on patterns we've actually seen in prod
     data and that aren't ambiguous. When in doubt, no-op.
  2. Composable — `5-shot CoT, French` populates three fields at once.
  3. Bounded — we don't try to NLP-infer training state from model names
     or sampling settings from temperature mentions. Only obvious tokens.

Returns a dict containing only the keys that were confidently parsed.
Callers should use this to fill NULL columns, not overwrite existing data.
"""
from __future__ import annotations

import re
from typing import Optional


# ── shot_count ───────────────────────────────────────────────────────────────
# Matches "N-shot", "N shot", "Nshot" where N is a digit string.
_SHOT_INT_RE = re.compile(r"\b(\d+)[\s-]?shots?\b", re.IGNORECASE)
# Matches "k-shots=N", "k_shots=N", "k=N-shot" — observed Anthropic format.
_SHOT_EQ_RE = re.compile(r"\bk[\s_-]?shots?\s*=\s*(\d+)\b", re.IGNORECASE)
# "zero-shot" / "zero shot"
_SHOT_ZERO_RE = re.compile(r"\bzero[\s-]shots?\b", re.IGNORECASE)


def _parse_shot_count(variant: str) -> Optional[int]:
    if _SHOT_ZERO_RE.search(variant):
        return 0
    m = _SHOT_EQ_RE.search(variant)
    if m:
        return int(m.group(1))
    m = _SHOT_INT_RE.search(variant)
    if m:
        return int(m.group(1))
    return None


# ── method (sampling/prompting strategy) ─────────────────────────────────────
# Order matters: longer / more specific patterns first.
_METHOD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bchain[\s-]of[\s-]thought\b", re.IGNORECASE), "CoT"),
    (re.compile(r"\bCoT\b"), "CoT"),
    (re.compile(r"\bself[\s-]consistency\b", re.IGNORECASE), "self-consistency"),
    (re.compile(r"\bmajority[\s-]voting\b", re.IGNORECASE), "majority-voting"),
    (re.compile(r"\bmaj@\d+\b", re.IGNORECASE), "majority-voting"),
    (re.compile(r"\bextended[\s-]thinking\b", re.IGNORECASE), "extended-thinking"),
    (re.compile(r"\btree[\s-]of[\s-]thoughts\b", re.IGNORECASE), "tree-of-thoughts"),
    (re.compile(r"\bToT\b"), "tree-of-thoughts"),
    (re.compile(r"\bRAG\b"), "RAG"),
    (re.compile(r"\bwith\s+tools?\b", re.IGNORECASE), "with-tools"),
    (re.compile(r"\b(?:no|without)\s+tools?\b", re.IGNORECASE), "no-tools"),
]


def _parse_method(variant: str) -> Optional[str]:
    for pattern, value in _METHOD_PATTERNS:
        if pattern.search(variant):
            return value
    return None


# ── language ─────────────────────────────────────────────────────────────────
# Capitalized forms only — avoids matching English language words used in prose
# (e.g. variant containing "the english test"). The extractor produces tokens
# in a stable form so this is safe.
_LANGUAGE_TOKENS: dict[str, str] = {
    "English": "English",
    "French": "French",
    "German": "German",
    "Spanish": "Spanish",
    "Japanese": "Japanese",
    "Mandarin": "Mandarin",
    "Multilingual": "Multilingual",
    "Average": "Average",  # cross-language aggregate; common in MGSM-style cards
}


def _parse_language(variant: str) -> Optional[str]:
    for token, value in _LANGUAGE_TOKENS.items():
        if re.search(rf"\b{re.escape(token)}\b", variant):
            return value
    return None


# ── training_state ───────────────────────────────────────────────────────────
_TRAINING_STATE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpre[\s-]?trained\b", re.IGNORECASE), "pretrained"),
    (re.compile(r"\binstruction[\s-]tuned\b", re.IGNORECASE), "instruction-tuned"),
    (re.compile(r"\bRLHF\b", re.IGNORECASE), "RLHF"),
    (re.compile(r"\bSFT\b"), "SFT"),
    # "base" only as a standalone word — too many false positives otherwise
    # (model names containing "base", "base case", etc.).
    (re.compile(r"\bbase\b", re.IGNORECASE), "base"),
]


def _parse_training_state(variant: str) -> Optional[str]:
    for pattern, value in _TRAINING_STATE_PATTERNS:
        if pattern.search(variant):
            return value
    return None


# ── public entry point ───────────────────────────────────────────────────────
def parse_variant(variant: Optional[str]) -> dict:
    """Parse a variant string. Returns a dict with only confidently-parsed keys.

    >>> parse_variant("5-shot CoT")
    {'shot_count': 5, 'method': 'CoT'}
    >>> parse_variant("Magnification, pre-mitigation")
    {}
    >>> parse_variant("extended-thinking, rlhf")
    {'method': 'extended-thinking', 'training_state': 'RLHF'}
    """
    if not variant or variant.lower() in {"default", ""}:
        return {}

    out: dict = {}
    shot = _parse_shot_count(variant)
    if shot is not None:
        out["shot_count"] = shot
    method = _parse_method(variant)
    if method is not None:
        out["method"] = method
    lang = _parse_language(variant)
    if lang is not None:
        out["language"] = lang
    ts = _parse_training_state(variant)
    if ts is not None:
        out["training_state"] = ts
    return out
