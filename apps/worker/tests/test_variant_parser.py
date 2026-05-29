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

def test_pass_at_n_is_metric_not_method():
    """pass@1 → metric_path, not method. (Phase 5a expands the parser to
    capture metric_paths it ignored in Phase 4.)"""
    assert parse_variant("pass@1") == {"metric_path": "pass_at_1"}


def test_truly_ambiguous_still_silent():
    """The remaining ambiguous strings should still produce nothing — they're
    eval-mode tokens or safety classifications we can't generalize."""
    assert parse_variant("not_unsafe") == {}
    assert parse_variant("not_overrefuse") == {}
    assert parse_variant("prompt engineered") == {}
    assert parse_variant("single-turn") == {}
    assert parse_variant("side-by-side") == {}
    assert parse_variant("relative to Gemini 1.5 Pro 002") == {}
    assert parse_variant("vs Gemini 2.5 Flash") == {}


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


# ── split (Phase 5a) ─────────────────────────────────────────────────────────

def test_split_biorisk_subtasks():
    """OpenAI's biological-risk benchmark sub-tasks. The single biggest cluster
    of unparseable variants in our corpus before Phase 5a."""
    assert parse_variant("Magnification, pre-mitigation") == {
        "split": "magnification",
        "method": "pre-mitigation",
    }
    assert parse_variant("Acquisition, post-mitigation") == {
        "split": "acquisition",
        "method": "post-mitigation",
    }
    assert parse_variant("Ideation, pre-mitigation") == {
        "split": "ideation",
        "method": "pre-mitigation",
    }


def test_split_bbq_modes():
    assert parse_variant("ambiguous") == {"split": "ambiguous"}
    assert parse_variant("disambiguated") == {"split": "disambiguated"}


def test_split_swe_bench_verified():
    """SWE-bench Verified is the curated 500-task subset — a different split
    from full SWE-bench. Critical for resolving the 28-point divergence."""
    assert parse_variant("Verified") == {"split": "verified"}


def test_split_gpqa_diamond():
    assert parse_variant("Diamond") == {"split": "diamond"}


def test_split_difficulty_descriptors():
    assert parse_variant("hard") == {"split": "hard"}
    assert parse_variant("overall") == {"split": "overall"}


def test_split_year_anchored_subset():
    """USAMO 2026 — year acts as the split label, not the year of report."""
    assert parse_variant("USAMO 2026") == {"split": "2026"}
    assert parse_variant("AIME 2024") == {"split": "2024"}


# ── metric_path (Phase 5a) ───────────────────────────────────────────────────

def test_metric_pass_at_n():
    assert parse_variant("pass@1") == {"metric_path": "pass_at_1"}
    assert parse_variant("pass@10") == {"metric_path": "pass_at_10"}


def test_metric_cot_correct():
    """MMLU-Pro and similar — distinguishes raw accuracy from CoT scoring."""
    assert parse_variant("CoT correct") == {"metric_path": "cot_correct"}
    assert parse_variant("CoT-correct") == {"metric_path": "cot_correct"}


def test_metric_win_rate():
    assert parse_variant("win rate vs Claude 3.5 Sonnet") == {"metric_path": "win_rate"}
    assert parse_variant("win-rate") == {"metric_path": "win_rate"}


def test_metric_f1():
    assert parse_variant("F1") == {"metric_path": "f1"}


def test_metric_resolve_rate():
    """SWE-bench native metric."""
    assert parse_variant("resolve rate") == {"metric_path": "resolve_rate"}


# ── mitigation states route to method ────────────────────────────────────────

def test_without_mitigations_goes_to_method():
    assert parse_variant("without mitigations") == {"method": "without-mitigations"}
    assert parse_variant("without safeguards") == {"method": "without-safeguards"}


def test_pre_mitigation_alone():
    """pre-mitigation by itself maps to method (not a split — splits are
    sub-tasks, mitigation state is a methodology choice)."""
    assert parse_variant("pre-mitigation") == {"method": "pre-mitigation"}


# ── compound real-world cases (Phase 5a) ─────────────────────────────────────

def test_compound_split_plus_metric():
    """A realistic full-path variant: hard MATH subset under pass@1 scoring."""
    assert parse_variant("hard, pass@1") == {"split": "hard", "metric_path": "pass_at_1"}


def test_compound_full_hierarchy():
    """Composite: shot count + method + split + metric all in one string."""
    result = parse_variant("0-shot, CoT, Verified, pass@1")
    assert result == {
        "shot_count": 0,
        "method": "CoT",
        "split": "verified",
        "metric_path": "pass_at_1",
    }


def test_no_match_still_silent():
    """Phase 4's silent-on-ambiguous behavior must still hold."""
    assert parse_variant("relative to Gemini 1.5 Pro 002") == {}
    assert parse_variant("not_unsafe") == {}
