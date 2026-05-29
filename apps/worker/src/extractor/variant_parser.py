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
    # Don't match CoT when followed by "correct" — that's a metric_path, not a
    # prompting method. e.g. "CoT correct" or "CoT-correct" on MMLU-Pro.
    (re.compile(r"\bCoT\b(?![\s-]?correct)"), "CoT"),
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


# ── split (EvalCards Section 3.2 — sub-task / subcategory within a benchmark) ─
# Splits are benchmark-specific. We recognize tokens that the extractor has
# actually emitted into variant strings across the corpus. Anything else stays
# null — splits we don't know about should reach the schema through the
# extractor prompt (Phase 5b) rather than being guessed at by this parser.
_SPLIT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OpenAI biorisk benchmark sub-tasks (long_form_biological_risk_questions)
    (re.compile(r"\bMagnification\b"), "magnification"),
    (re.compile(r"\bAcquisition\b"), "acquisition"),
    (re.compile(r"\bIdeation\b"), "ideation"),
    (re.compile(r"\bFormulation\b"), "formulation"),
    (re.compile(r"\bRelease\b"), "release"),
    # BBQ-family eval modes
    (re.compile(r"\bambiguous\b", re.IGNORECASE), "ambiguous"),
    (re.compile(r"\bdisambiguated\b", re.IGNORECASE), "disambiguated"),
    # SWE-bench curated subset
    (re.compile(r"\bverified\b", re.IGNORECASE), "verified"),
    # GPQA curated subset
    (re.compile(r"\bDiamond\b"), "diamond"),
    # Generic difficulty splits
    (re.compile(r"\bhard\b", re.IGNORECASE), "hard"),
    (re.compile(r"\boverall\b", re.IGNORECASE), "overall"),
    # Year-anchored subsets (USAMO 2026, AIME 2024 etc.) — when the year follows
    # an Olympiad/competition name, treat year as the split.
    (re.compile(r"\b(?:USAMO|AIME|AMC|HMMT|Putnam)\s+(\d{4})\b"), r"\g<1>"),
]


def _parse_split(variant: str) -> Optional[str]:
    for pattern, value in _SPLIT_PATTERNS:
        m = pattern.search(variant)
        if m:
            # Allow backreferences (e.g. captured year).
            return m.expand(value) if "\\" in value else value
    return None


# ── metric_path (EvalCards Section 3.2 — scoring rule) ───────────────────────
_METRIC_PATH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpass@(\d+)\b", re.IGNORECASE), r"pass_at_\g<1>"),
    (re.compile(r"\bCoT[\s-]?correct\b", re.IGNORECASE), "cot_correct"),
    (re.compile(r"\bwin[\s-]rate\b", re.IGNORECASE), "win_rate"),
    (re.compile(r"\bF1\b"), "f1"),
    (re.compile(r"\bexact[\s-]match\b", re.IGNORECASE), "exact_match"),
    (re.compile(r"\bresolve[\s-]rate\b", re.IGNORECASE), "resolve_rate"),
    (re.compile(r"\belo\b", re.IGNORECASE), "elo"),
]


def _parse_metric_path(variant: str) -> Optional[str]:
    for pattern, value in _METRIC_PATH_PATTERNS:
        m = pattern.search(variant)
        if m:
            return m.expand(value) if "\\" in value else value
    return None


# ── mitigation states (paper-not-modeled axis; routed to method column) ──────
# pre/post-mitigation and the "without mitigations / without safeguards" tokens
# are methodology choices about how the model was evaluated, not splits or
# metrics. They go to `method` so they integrate with the existing pill UI.
_MITIGATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpre[\s-]mitigation\b", re.IGNORECASE), "pre-mitigation"),
    (re.compile(r"\bpost[\s-]mitigation\b", re.IGNORECASE), "post-mitigation"),
    (re.compile(r"\bwithout\s+mitigations?\b", re.IGNORECASE), "without-mitigations"),
    (re.compile(r"\bwithout\s+safeguards?\b", re.IGNORECASE), "without-safeguards"),
]


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
    # Method: first the explicit sampling/prompting tokens, then fall back to
    # mitigation state (these are method-like; they describe HOW the eval ran).
    method = _parse_method(variant)
    if method is None:
        for pattern, value in _MITIGATION_PATTERNS:
            if pattern.search(variant):
                method = value
                break
    if method is not None:
        out["method"] = method
    lang = _parse_language(variant)
    if lang is not None:
        out["language"] = lang
    ts = _parse_training_state(variant)
    if ts is not None:
        out["training_state"] = ts
    split = _parse_split(variant)
    if split is not None:
        out["split"] = split
    metric_path = _parse_metric_path(variant)
    if metric_path is not None:
        out["metric_path"] = metric_path
    return out
