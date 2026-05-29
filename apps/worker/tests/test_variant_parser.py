"""Tests for the variant string parser.

Cases derived directly from a prod survey of the top-40 most-frequent
non-default variant strings — testing what the parser actually sees,
not invented edge cases.
"""
from __future__ import annotations

import pytest

from src.extractor.variant_parser import parse_variant


# ── shot_count ───────────────────────────────────────────────────────────────

def test_zero_shot():
    assert parse_variant("0-shot") == {"shot_count": 0}


def test_zero_shot_word():
    assert parse_variant("zero-shot") == {"shot_count": 0}


def test_n_shot_basic():
    assert parse_variant("5-shot") == {"shot_count": 5}
    assert parse_variant("1-shot") == {"shot_count": 1}
    assert parse_variant("16-shot") == {"shot_count": 16}


def test_k_shots_equals_form():
    """Anthropic-format: k-shots=10"""
    assert parse_variant("k-shots=10") == {"shot_count": 10}


# ── shot_count + method combos (most common compound form in prod) ───────────

def test_shot_plus_cot_comma():
    assert parse_variant("0-shot, CoT") == {"shot_count": 0, "method": "CoT"}


def test_shot_plus_cot_space():
    assert parse_variant("0-shot CoT") == {"shot_count": 0, "method": "CoT"}
    assert parse_variant("5-shot CoT") == {"shot_count": 5, "method": "CoT"}


def test_shot_plus_pretrained():
    """16-shot, pre-trained — common in Llama tech reports."""
    assert parse_variant("16-shot, pre-trained") == {
        "shot_count": 16,
        "training_state": "pretrained",
    }


# ── method tokens ────────────────────────────────────────────────────────────

def test_cot_uppercase():
    assert parse_variant("CoT") == {"method": "CoT"}


def test_chain_of_thought_spelled_out():
    assert parse_variant("chain of thought") == {"method": "CoT"}
    assert parse_variant("chain-of-thought") == {"method": "CoT"}


def test_extended_thinking_variants():
    assert parse_variant("extended thinking") == {"method": "extended-thinking"}
    assert parse_variant("extended-thinking") == {"method": "extended-thinking"}


def test_extended_thinking_plus_rlhf():
    """Observed 16 times in prod."""
    assert parse_variant("extended-thinking, rlhf") == {
        "method": "extended-thinking",
        "training_state": "RLHF",
    }


def test_tools_modes():
    assert parse_variant("with tools") == {"method": "with-tools"}
    assert parse_variant("no tools") == {"method": "no-tools"}
    assert parse_variant("without tools") == {"method": "no-tools"}


def test_majority_voting():
    assert parse_variant("majority voting") == {"method": "majority-voting"}
    assert parse_variant("maj@8") == {"method": "majority-voting"}


# ── language ─────────────────────────────────────────────────────────────────

def test_language_alone():
    assert parse_variant("English") == {"language": "English"}
    assert parse_variant("French") == {"language": "French"}


def test_language_average_cross_lang_aggregate():
    """MGSM-style cards report 'Average' across languages."""
    assert parse_variant("Average") == {"language": "Average"}


def test_lowercase_language_not_matched():
    """Lowercase 'english' in prose-y variant should NOT match — too
    ambiguous (could be 'english test', 'english version', etc.)."""
    assert parse_variant("english") == {}


# ── training_state ───────────────────────────────────────────────────────────

def test_pretrained_variants():
    assert parse_variant("pre-trained") == {"training_state": "pretrained"}
    assert parse_variant("pretrained") == {"training_state": "pretrained"}


def test_instruction_tuned():
    assert parse_variant("instruction-tuned") == {"training_state": "instruction-tuned"}


def test_rlhf_case_insensitive():
    assert parse_variant("RLHF") == {"training_state": "RLHF"}
    assert parse_variant("rlhf") == {"training_state": "RLHF"}


# ── critical NEGATIVES: don't pollute fields with bad guesses ────────────────

def test_metric_string_not_method():
    """pass@1 is a metric name, NOT a method. The extractor stashes it in
    variant sometimes — we must not misclassify it as a setup field."""
    assert parse_variant("pass@1") == {}


def test_subset_name_no_match():
    """'Magnification, pre-mitigation' is a sub-task name (EvalCards split)
    plus mitigation state. None of our four fields applies. Stay silent."""
    assert parse_variant("Magnification, pre-mitigation") == {}
    assert parse_variant("Acquisition, post-mitigation") == {}


def test_ambiguous_words_no_match():
    """Single-word variants we can't confidently map."""
    assert parse_variant("ambiguous") == {}
    assert parse_variant("disambiguated") == {}
    assert parse_variant("hard") == {}
    assert parse_variant("overall") == {}
    assert parse_variant("not_unsafe") == {}
    assert parse_variant("not_overrefuse") == {}


def test_comparison_variants_no_match():
    """Comparative descriptors aren't setup fields."""
    assert parse_variant("vs Gemini 2.5 Flash") == {}
    assert parse_variant("relative to Gemini 1.5 Pro 002") == {}
    assert parse_variant("win rate vs Claude 3.5 Sonnet") == {}


def test_subset_year_no_match():
    assert parse_variant("USAMO 2026") == {}


def test_default_and_empty():
    assert parse_variant("default") == {}
    assert parse_variant("") == {}
    assert parse_variant(None) == {}


def test_standard_thinking_not_extended():
    """'standard thinking' is observed but doesn't unambiguously map to
    extended-thinking. Stay silent."""
    assert parse_variant("standard thinking") == {}


# ── compound real-world examples ─────────────────────────────────────────────

def test_compound_realistic():
    """Multi-axis variant should populate all matching axes."""
    result = parse_variant("5-shot, CoT, English, RLHF")
    assert result == {
        "shot_count": 5,
        "method": "CoT",
        "language": "English",
        "training_state": "RLHF",
    }


def test_8shot_cot_observed():
    """Observed in prod, 9 times."""
    assert parse_variant("8-shot, CoT") == {"shot_count": 8, "method": "CoT"}
