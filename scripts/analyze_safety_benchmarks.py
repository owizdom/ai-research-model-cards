#!/usr/bin/env python3
"""
Analysis: Safety Benchmark Landscape Across AI Model Cards
==========================================================
Which safety benchmarks exist, who uses them, when, and can we
compare models on safety?  Synthesizes findings into a recommendation
for standardized safety benchmark disclosure.

Usage:
    python scripts/analyze_safety_benchmarks.py [--db-url URL]

Outputs (in output/analysis/safety/):
    - safety_coverage_matrix.csv       Model x safety benchmark presence/scores
    - temporal_safety.csv              Timeline of safety benchmark adoption
    - safety_benchmark_catalog.csv     Catalog of all safety-relevant benchmarks
    - cohort_comparison.csv            Temporal cohort comparability analysis
    - safety_coverage_heatmap.png      Heatmap of model x benchmark
    - temporal_adoption.png            Timeline chart
    - cohort_comparability.png         Cohort Jaccard similarity chart
"""
import argparse
import os
import re
import sys
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from tabulate import tabulate

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DB_URL = os.getenv(
    "RAILWAY_DB_URL",
    "postgresql://postgres:EhJrykdvTfzmimVtioekfVUYppGRowxm@hopper.proxy.rlwy.net:37555/railway",
)
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "analysis" / "safety"
EXTERNAL_VALIDATION_DIR = Path(__file__).parent.parent / "external_validation"

CANONICAL_SAFETY_BENCHMARKS = {
    "truthfulqa", "bbq", "toxigen", "xstest", "realtoxicityprompts",
}

SAFETY_KEYWORDS = [
    "safety", "safe", "red.?team", "adversarial", "harmful", "harm",
    "toxicity", "toxic", "bias", "fairness", "hate", "abuse", "violence",
    "csam", "child.?safety", "self.?harm", "suicide", "weapons", "cbrn",
    "malicious", "jailbreak", "refusal", "guardrail", "misuse",
    "dangerous", "cybersecurity", "cyber",
]
_SAFETY_RE = re.compile("|".join(SAFETY_KEYWORDS), re.IGNORECASE)

# Benchmark -> taxonomy category mapping (extended from says_vs_measures)
BENCHMARK_TO_TAXONOMY = {
    "truthfulqa":          "misinformation",
    "bbq":                 "bias_fairness",
    "toxigen":             "harmful_content",
    "xstest":              "safety_guidelines",
    "realtoxicityprompts": "harmful_content",
}

TAXONOMY_CATEGORIES = [
    ("safety_guidelines",    "Safety Guidelines & Red Lines",       "Safe",                              "Art.9, Annex IV"),
    ("alignment_values",     "Alignment & Core Values",             "Valid & Reliable",                  "Art.9"),
    ("bias_fairness",        "Bias & Fairness",                     "Fair - Bias Managed",               "Art.10, Recital 47"),
    ("privacy_data",         "Privacy & Data Handling",             "Privacy Enhanced",                  "Art.10, Art.53(1)(d)"),
    ("transparency",         "Transparency & Explainability",       "Accountable & Transparent",         "Art.13, Art.50"),
    ("harmful_content",      "Harmful Content Prevention",          "Safe",                              "Art.5, Art.9"),
    ("dual_use",             "Dual-Use & Weapons",                  "Safe, Secure & Resilient",          "Recital 33"),
    ("political_neutrality", "Political Neutrality & Elections",    "Fair - Bias Managed",               "Art.5(1)(a)"),
    ("human_oversight",      "Human Oversight & Control",           "Accountable & Transparent",         "Art.14, Annex IV"),
    ("agentic_behavior",     "Agentic Behavior & Autonomy",        "Safe, Accountable & Transparent",   "Art.14"),
    ("creative_fiction",     "Creative Content & Fiction",          "~",                                 "Art.50"),
    ("legal_compliance",     "Legal Compliance & Copyright",        "~",                                 "Art.53(1)(c)"),
    ("misinformation",       "Misinformation & Factual Accuracy",  "Valid and Reliable",                "Art.9, Recital 47"),
    ("child_safety",         "Child Safety",                        "Safe",                              "Art.5"),
    ("mental_health",        "Mental Health & Vulnerable Users",    "Safe, Fair",                        "Art.5(1)(a)"),
]

GEN_CHRONO_ORDER = {
    # Claude
    "claude-2": 1, "claude-3": 2, "claude-3.5": 3, "claude-3.5-haiku": 4,
    "claude-3.7": 5, "claude-4": 6, "claude-sonnet-4.5": 7, "claude-opus-4.5": 8,
    "claude-haiku-4.5": 9, "claude-opus-4.1": 10, "claude-sonnet-4.6": 11,
    "claude-opus-4.6": 12, "claude-mythos": 13,
    # GPT
    "gpt-4": 1, "gpt-4o": 2, "gpt-4.5": 3, "o1": 4, "o3-mini": 5,
    "o3": 6, "gpt-5": 7, "operator": 8, "gpt-5.1": 9, "gpt-5.2": 10,
    "gpt-5.3": 11,
    # Gemini
    "gemini-1.0": 1, "gemini-1.5": 2, "gemini-2.0": 3, "gemini-2.5": 4,
    "gemini-2.5-pro": 5, "gemini-2.5-dt": 6, "gemini-3.0": 7,
    "gemini-3.0-pro": 8, "gemini-3.1-pro": 9,
    # Llama
    "llama-2": 1, "llama-3": 2, "llama-3.1": 3, "llama-3.1-card": 4,
    "llama-3.2": 5, "llama-3.3": 6, "llama-4": 7,
    # Grok
    "grok-4": 1, "grok-4-fast": 2, "grok-4.1": 3,
    # Mistral
    "mistral-7b": 1, "mixtral-8x7b": 2, "codestral": 3,
    "mistral-large-2": 4, "mistral-small-3": 5,
}

LAB_COLORS = {
    "anthropic": "#D4791A",
    "openai": "#10A37F",
    "google": "#4285F4",
    "meta": "#0866FF",
    "xai": "#1DA1F2",
    "mistral": "#FF7000",
    "cohere": "#39594D",
    "amazon": "#FF9900",
    "ai21": "#6C3CE1",
}

COHORT_WINDOW_MONTHS = 6

# ---------------------------------------------------------------------------
# Saturation & Benchmark Lifecycle
# ---------------------------------------------------------------------------
# A benchmark is "saturated" when the best observed score is within this
# margin of the theoretical max (score_max).  For 0-100 benchmarks,
# SATURATION_THRESHOLD = 95 means scores >= 95 are considered saturated.
SATURATION_THRESHOLD_PCT = 0.95  # fraction of score_max

# Known benchmark succession chains.  When an older benchmark is dropped
# and its successor is adopted, that's a legitimate retirement.
# Format: old_slug -> new_slug (the harder / updated version)
BENCHMARK_SUCCESSORS = {
    "mmlu":             "mmlu_pro",
    "gsm8k":            "math",
    "math":             "aime",
    "humaneval":        "swe_bench",
    "hellaswag":        "big_bench_hard",
    "arc_challenge":    "gpqa",
    "swe_bench":        "swe_bench_verified",
    "gpqa":             "gpqa_diamond",
    "winogrande":       "big_bench_hard",
    "triviaqa":         "mmlu",
    "natural_questions": "mmlu",
    "boolq":            "big_bench_hard",
    "toxigen":          "wildchat_toxic",
    "truthfulqa":       "truthfulqa",     # no successor yet — sentinel
    "bbq":              "bbq",            # no successor yet — sentinel
    # Version chains (same benchmark, newer version)
    "livecodebench_v5":                "livecodebench_v6",
    "livecodebench_10_1_2024_2_1_2025": "livecodebench_1_1_2025_5_1_2025",
    "mrcr_1m":                         "mrcr_v2",
    "swe_lancer_ic_swe":               "swe_lancer_swe_manager",
    "aime":                            "aime_2024",
    "troubleshootingbench_human_expert_baseline": "troubleshootingbench_expert_threshold",
}

# Lifecycle status labels
LIFECYCLE_ACTIVE      = "ACTIVE"        # still reported by recent models
LIFECYCLE_SATURATED   = "SATURATED"     # dropped after near-ceiling score
LIFECYCLE_SUPERSEDED  = "SUPERSEDED"    # dropped, successor adopted
LIFECYCLE_CONTAMINATED = "CONTAMINATED" # known data leakage into training sets
LIFECYCLE_FLAWED      = "FLAWED"        # known methodological issues (label errors, ambiguity)
LIFECYCLE_FORMAT_AGED = "FORMAT_AGED"   # task format no longer relevant (e.g., MCQ shortcuts)
LIFECYCLE_SUSPICIOUS  = "SUSPICIOUS"    # dropped without identifiable legitimate reason
LIFECYCLE_EMERGING    = "EMERGING"      # only appears in recent models
LIFECYCLE_ONETIME     = "ONE-TIME"      # appeared in exactly 1 model
LIFECYCLE_INTERNAL    = "INTERNAL"      # proprietary/internal research eval, not meant for cross-gen tracking
LIFECYCLE_CAP_SHIFT   = "CAP_SHIFT"    # capability-specific benchmark dropped when lab shifted focus
LIFECYCLE_METRIC_CHG  = "METRIC_CHANGE" # score rescaling or metric redefinition (>50% score swing)
LIFECYCLE_COST        = "COST_PROHIBITIVE"  # expensive to run (human eval, large-scale agent benchmarks)

# Benchmarks with documented data contamination issues.
# Sources: GSM1K paper (arXiv:2405.00332), HumanEval leakage study (arXiv:2406.04244),
# MMLU rephrasing attacks (arXiv:2311.04850), OpenAI SWE-bench statement (2025).
KNOWN_CONTAMINATED = {
    "gsm8k",             # GSM1K study: up to 13% accuracy inflation from leakage
    "humaneval",         # 8-18% overlap with pre-training sets (RedPajama, StarCoder)
    "mmlu",              # Rephrasing attacks; MMLU data widely in web crawls
    "math",              # LLM decontaminator found 1.58% rephrased samples
    "swe_bench_verified", # OpenAI: frontier models can reproduce ground-truth patches
    "swe_bench",         # Same underlying data as Verified; GitHub PRs in training
    "arc_challenge",     # Included in many fine-tuning datasets
}

# Benchmarks with documented methodological flaws (incorrect labels, ambiguous Qs).
# Sources: MMLU error analysis (arXiv:2406.04127), HellaSwag construct validity
# (arXiv:2504.07825), SWE-bench Verified audit (OpenAI, 59.4% flawed tests),
# HumanEval ground-truth errors (arXiv:2305.01210).
KNOWN_FLAWED = {
    "mmlu",              # ~6.5% of questions contain errors; 57% of Virology wrong
    "hellaswag",         # Construct validity: ungrammatical, typos, misleading prompts
    "swe_bench_verified", # 59.4% of problems have material test design issues
    "humaneval",         # >10% of ground-truth solutions incorrectly implemented
    "truthfulqa",        # Static "common misconceptions" become outdated over time
    "winogrande",        # Annotation artifacts allow shortcutting
}

# Benchmarks whose task format is considered outdated (MCQ shortcuts, isolated tasks).
# Sources: MCQ position bias studies (arXiv:2406.07545), HumanEval scope critique.
KNOWN_FORMAT_AGED = {
    "mmlu",              # MCQ format: 25% accuracy drop when converted to open-ended
    "hellaswag",         # MCQ sentence completion: solvable via surface patterns
    "arc_challenge",     # MCQ: grade-school science, process-of-elimination exploitable
    "winogrande",        # Binary choice: not representative of real usage
    "boolq",             # Binary yes/no: trivially simple format
    "humaneval",         # Isolated function generation ≠ real software development
    "triviaqa",          # Factoid recall, not reasoning
    "natural_questions", # Factoid recall from Google Search
}

# Benchmarks known to have been "gamed" / exploited.
# Sources: LMArena controversy (TechCrunch 2025), Berkeley exploit study.
KNOWN_GAMED = {
    "chatbot_arena_elo",  # LMArena: labs privately test variants, reveal only best
    "swe_bench",          # Berkeley: automated agents exploit benchmark without reasoning
    "webarena",           # Berkeley: exploit-based near-perfect scores
    "arc_agi",            # OpenAI reportedly spent $100K+ compute to score high
}

# Internal / proprietary research evals — lab-specific, never meant for cross-gen tracking.
# Matched by exact slug OR prefix patterns.
KNOWN_INTERNAL_SLUGS = {
    "lab_bench_cloning_scenarios", "lab_bench_seqqa",
    "long_form_virology_task_1_overall", "long_form_virology_task_2",
    "protocol_design", "protocolqa", "sequence_design",
    "soft_bias_internal",
    "mcp_atlas",                        # MCP protocol eval — Anthropic internal
    "openai_prs",                       # OpenAI internal PR eval
    "openai_interview_multiple_choice", # OpenAI internal hiring benchmark
    "openai_research_coding_interview", # OpenAI internal hiring benchmark
    "model_mistake_rate_unmitigated",   # OpenAI Operator internal safety metric
    "reasoning_monitor",                # OpenAI internal monitoring eval
    "topical_classifier",               # OpenAI internal classifier eval
    "standard_disallowed_content_evaluation",  # OpenAI internal safety
}
KNOWN_INTERNAL_PREFIXES = (
    "lab_bench_", "long_form_virology", "model_autonomy_",
    "prompt_injection_", "claude_code_", "benign_request_",
    "violative_request_", "single_turn_", "child_safety_",
    "suicide_and_self_harm_", "political_bias_", "disordered_eating_",
    "image_input_evaluations_",
)

# Capability-specific benchmarks — only relevant to certain model types.
# When a lab de-emphasizes a capability, these benchmarks naturally drop.
CAPABILITY_BENCHMARKS = {
    "vision": {
        "chartqa", "figqa", "docvqa", "mmmu", "mathvista", "ai2d",
        "vibe_eval_reka", "video_mme", "charxiv_missing_image",
        "image_editing_character_genai_bench", "image_editing_creative_genai_bench",
        "image_editing_infographics_genai_bench", "image_editing_object_environment_genai_bench",
        "image_editing_product_recontextualization_genai_bench",
        "image_editing_stylization_genai_bench",
        "text_to_image_alignment_genai_bench",
        "overall_preference_lmarena_image_editing",
        "overall_preference_lmarena_text_to_image",
    },
    "multilingual": {
        "mgsm", "mmmlu", "wmt23_all_languages", "wmt23_high_resource",
        "wmt23_into_english", "wmt23_mid_resource", "wmt23_out_of_english",
        "low_resource_translation_flores_ntrex", "wikilingua", "xlsum",
        "tydiqa_goldp", "uhura_eval_hausa", "arc_easy_hausa",
        "multilingual_safety",
    },
    "long_context": {
        "infinitebench_en_mc", "infinitebench_en_qa", "ruler",
        "needle_in_haystack", "nih_multi_needle",
        "mrcr_1m", "mrcr_v2", "quality",
        "key_value_retrieval_synthetic",
    },
    "agentic": {
        "webarena", "osworld", "swe_bench", "swe_bench_verified",
        "swe_lancer_ic_swe", "swe_lancer_swe_manager",
        "agentdojo", "agentharm", "terminal_bench_2_0",
        "browsing_broken_tools",
    },
}
# Flatten for quick lookup: slug -> set of capabilities
_BENCH_TO_CAPS: dict[str, set[str]] = {}
for cap, slugs in CAPABILITY_BENCHMARKS.items():
    for s in slugs:
        _BENCH_TO_CAPS.setdefault(s, set()).add(cap)

# Benchmarks known to be expensive to evaluate (human-in-the-loop, large agent runs).
# Labs may drop these for cost reasons, not quality reasons.
KNOWN_COST_PROHIBITIVE = {
    "metr",                 # Multi-day agent tasks, expensive compute
    "arc_agi_2_verified",   # Expensive compute ($100K+)
    "mle_bench",            # Full ML pipeline runs
    "paperbench",           # Full paper reproduction
    "re_bench",             # Research engineering tasks
    "humanity_s_last_exam", # Expert-curated, expensive to produce/score
    "human_preference_chatgpt_api_prompts",  # Human eval
    "human_evaluation_vs_gemma_2_27b",       # Human eval
    "human_evaluation_vs_gpt_4o_mini",       # Human eval
    "human_evaluation_vs_llama_3_3_70b",     # Human eval
    "human_evaluation_vs_qwen_2_5_32b",      # Human eval
    "person_identification",                 # Human eval
    "speaker_identification",                # Human eval
}

# Metric rescaling threshold: if score drops >50% between adjacent generations
# without the benchmark being known-saturated, likely a metric redefinition.
METRIC_CHANGE_DROP_THRESHOLD = 0.50  # 50% relative drop


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chrono_sort_key(gen_slug_series: pd.Series) -> pd.Series:
    return gen_slug_series.map(GEN_CHRONO_ORDER).fillna(999)


def assign_cohort(release_date) -> str:
    if pd.isna(release_date):
        return "Unknown"
    d = pd.to_datetime(release_date)
    half = "H1" if d.month <= 6 else "H2"
    return f"{d.year}-{half}"


def compute_jaccard(set_a: set, set_b: set) -> float:
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_engine(db_url: str):
    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine


def query_all_evals(engine) -> pd.DataFrame:
    sql = text("""
        SELECT
            mf.slug   AS family_slug,
            mf.name   AS family_name,
            mg.slug   AS gen_slug,
            mg.name   AS gen_name,
            mg.release_date,
            bd.slug   AS benchmark_slug,
            bd.name   AS benchmark_name,
            bd.category AS benchmark_category,
            bd.description AS benchmark_description,
            bd.metric_name,
            bd.higher_is_better,
            er.score,
            er.state,
            er.variant,
            er.model_name
        FROM model_families mf
        JOIN model_generations mg ON mg.family_id = mf.id
        JOIN eval_results er ON er.generation_id = mg.id
        JOIN benchmark_definitions bd ON bd.id = er.benchmark_id
        ORDER BY mf.slug, mg.release_date, bd.slug
    """)
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


def query_all_benchmarks(engine) -> pd.DataFrame:
    sql = text("""
        SELECT slug, name, category, description,
               metric_name, higher_is_better, score_min, score_max, source_url
        FROM benchmark_definitions
        ORDER BY category, slug
    """)
    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


def query_all_generations(engine) -> pd.DataFrame:
    sql = text("""
        SELECT
            mf.slug  AS family_slug,
            mf.name  AS family_name,
            mg.slug  AS gen_slug,
            mg.name  AS gen_name,
            mg.release_date
        FROM model_families mf
        JOIN model_generations mg ON mg.family_id = mf.id
        ORDER BY mf.slug, mg.slug
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    df["_sort_key"] = df["gen_slug"].map(GEN_CHRONO_ORDER).fillna(999)
    df = df.sort_values(["family_slug", "_sort_key"]).drop(columns=["_sort_key"])
    return df


# ---------------------------------------------------------------------------
# Safety Benchmark Discovery
# ---------------------------------------------------------------------------

def identify_safety_benchmarks(all_evals_df: pd.DataFrame,
                               all_benchmarks_df: pd.DataFrame) -> set:
    """Find all safety-relevant benchmarks via category + keyword matching."""
    safety_slugs = set()

    # 1. category == 'safety'
    safety_slugs.update(
        all_benchmarks_df[all_benchmarks_df["category"] == "safety"]["slug"].tolist()
    )

    # 2. Canonical set
    safety_slugs.update(CANONICAL_SAFETY_BENCHMARKS)

    # 3. Keyword match on benchmark definitions
    for _, row in all_benchmarks_df.iterrows():
        text_to_check = f"{row['name']} {row.get('description', '')}"
        if _SAFETY_RE.search(text_to_check):
            safety_slugs.add(row["slug"])

    # 4. Keyword match on dynamically-created benchmarks in eval results
    for slug in all_evals_df["benchmark_slug"].unique():
        name = all_evals_df[all_evals_df["benchmark_slug"] == slug]["benchmark_name"].iloc[0]
        desc = all_evals_df[all_evals_df["benchmark_slug"] == slug]["benchmark_description"].iloc[0]
        text_to_check = f"{slug} {name} {desc if pd.notna(desc) else ''}"
        if _SAFETY_RE.search(text_to_check):
            safety_slugs.add(slug)

    return safety_slugs


# ---------------------------------------------------------------------------
# Analysis 1: Safety Benchmark Coverage Matrix
# ---------------------------------------------------------------------------

def build_safety_coverage_matrix(safety_evals_df: pd.DataFrame,
                                 gens_df: pd.DataFrame,
                                 safety_benchmarks: set) -> pd.DataFrame:
    """Model generations (rows) x safety benchmarks (cols) with scores."""
    if safety_evals_df.empty:
        return pd.DataFrame()

    # Deduplicate: best score per (family, gen, benchmark)
    deduped = (
        safety_evals_df.sort_values("score", ascending=False, na_position="last")
        .drop_duplicates(subset=["family_slug", "gen_slug", "benchmark_slug"], keep="first")
    )

    # Build long-form matrix
    rows = []
    benchmarks_seen = sorted(deduped["benchmark_slug"].unique())

    for _, gen in gens_df.iterrows():
        gen_evals = deduped[
            (deduped["family_slug"] == gen["family_slug"])
            & (deduped["gen_slug"] == gen["gen_slug"])
        ]
        for bench in benchmarks_seen:
            match = gen_evals[gen_evals["benchmark_slug"] == bench]
            if len(match) > 0:
                r = match.iloc[0]
                score = r["score"]
                state = r["state"]
                if state == "scored" and pd.notna(score):
                    cell = f"{score:.1f}"
                else:
                    cell = "M"
            else:
                score = None
                state = None
                cell = "."

            rows.append({
                "family_slug": gen["family_slug"],
                "gen_slug": gen["gen_slug"],
                "gen_name": gen["gen_name"],
                "release_date": gen["release_date"],
                "benchmark_slug": bench,
                "benchmark_name": (
                    deduped[deduped["benchmark_slug"] == bench]["benchmark_name"].iloc[0]
                    if bench in deduped["benchmark_slug"].values else bench
                ),
                "score": score,
                "state": state,
                "cell_value": cell,
            })

    return pd.DataFrame(rows)


def print_safety_coverage(matrix_df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("  ANALYSIS 1: SAFETY BENCHMARK COVERAGE MATRIX")
    print("  Which models report which safety benchmarks?")
    print("=" * 80)

    if matrix_df.empty:
        print("\n  No safety eval data found.")
        return

    benchmarks = sorted(matrix_df["benchmark_slug"].unique())

    for family in sorted(matrix_df["family_slug"].unique()):
        fam_df = matrix_df[matrix_df["family_slug"] == family]
        gens = (
            fam_df[["gen_slug", "gen_name", "release_date"]]
            .drop_duplicates()
            .assign(_sk=lambda d: chrono_sort_key(d["gen_slug"]))
            .sort_values("_sk").drop(columns=["_sk"])
        )
        # Only show benchmarks this family has used at least once
        fam_benchmarks = fam_df[fam_df["cell_value"] != "."]["benchmark_slug"].unique()
        if len(fam_benchmarks) == 0:
            continue

        fam_benchmarks = sorted(fam_benchmarks)
        print(f"\n\n--- {family.upper()} ({len(gens)} generations, "
              f"{len(fam_benchmarks)} safety benchmarks ever reported) ---")

        table_rows = []
        for bench in fam_benchmarks:
            row = {"Benchmark": bench}
            for _, gen in gens.iterrows():
                cell = fam_df[
                    (fam_df["gen_slug"] == gen["gen_slug"])
                    & (fam_df["benchmark_slug"] == bench)
                ]
                row[gen["gen_slug"]] = cell.iloc[0]["cell_value"] if len(cell) > 0 else "."
            table_rows.append(row)

        # Summary row: count per generation
        summary = {"Benchmark": "TOTAL"}
        for _, gen in gens.iterrows():
            gen_cells = fam_df[
                (fam_df["gen_slug"] == gen["gen_slug"])
                & (fam_df["cell_value"] != ".")
            ]
            summary[gen["gen_slug"]] = str(len(gen_cells))
        table_rows.append(summary)

        print(tabulate(table_rows, headers="keys", tablefmt="simple"))

    # Overall summary
    print("\n\n  SUMMARY: Safety benchmarks per model")
    summary_rows = []
    for family in sorted(matrix_df["family_slug"].unique()):
        fam_df = matrix_df[matrix_df["family_slug"] == family]
        for gen in fam_df["gen_slug"].unique():
            gen_df = fam_df[(fam_df["gen_slug"] == gen) & (fam_df["cell_value"] != ".")]
            if len(gen_df) > 0:
                summary_rows.append({
                    "Family": family,
                    "Generation": gen,
                    "Safety Benchmarks": len(gen_df),
                    "Scored": len(gen_df[gen_df["state"] == "scored"]),
                    "Mentioned": len(gen_df[gen_df["state"].isin(["mentioned", "cited"])]),
                })
    if summary_rows:
        print(tabulate(summary_rows, headers="keys", tablefmt="simple"))


def plot_safety_coverage_heatmap(matrix_df: pd.DataFrame, output_dir: Path):
    if matrix_df.empty:
        print("  Skipping safety coverage heatmap - no data.")
        return

    benchmarks = sorted(matrix_df["benchmark_slug"].unique())
    # Build ordered list of gen_slugs grouped by family
    gen_labels = []
    gen_families = []
    for family in sorted(matrix_df["family_slug"].unique()):
        fam_df = matrix_df[matrix_df["family_slug"] == family]
        gens = (
            fam_df[["gen_slug"]].drop_duplicates()
            .assign(_sk=lambda d: chrono_sort_key(d["gen_slug"]))
            .sort_values("_sk").drop(columns=["_sk"])
        )
        for _, g in gens.iterrows():
            gen_labels.append(g["gen_slug"])
            gen_families.append(family)

    # Build matrix: 0=absent, 1=mentioned, 2=scored
    data = np.zeros((len(gen_labels), len(benchmarks)))
    for gi, gen in enumerate(gen_labels):
        for bi, bench in enumerate(benchmarks):
            cell = matrix_df[
                (matrix_df["gen_slug"] == gen)
                & (matrix_df["benchmark_slug"] == bench)
            ]
            if len(cell) > 0:
                cv = cell.iloc[0]["cell_value"]
                if cv == "M":
                    data[gi, bi] = 1
                elif cv != ".":
                    data[gi, bi] = 2

    fig, ax = plt.subplots(figsize=(max(10, len(benchmarks) * 0.8),
                                     max(8, len(gen_labels) * 0.35)))
    cmap = matplotlib.colors.ListedColormap(["#f0f0f0", "#f39c12", "#2ecc71"])
    ax.imshow(data, cmap=cmap, vmin=0, vmax=2, aspect="auto")

    ax.set_xticks(range(len(benchmarks)))
    ax.set_xticklabels(benchmarks, rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(gen_labels)))
    ax.set_yticklabels(gen_labels, fontsize=7)

    # Score annotations
    for gi, gen in enumerate(gen_labels):
        for bi, bench in enumerate(benchmarks):
            cell = matrix_df[
                (matrix_df["gen_slug"] == gen)
                & (matrix_df["benchmark_slug"] == bench)
            ]
            if len(cell) > 0:
                cv = cell.iloc[0]["cell_value"]
                if cv not in (".", "M"):
                    ax.text(bi, gi, cv, ha="center", va="center",
                            fontsize=5, color="white", fontweight="bold")

    # Family color bars on left
    prev_family = None
    for gi, fam in enumerate(gen_families):
        color = LAB_COLORS.get(fam, "#888888")
        ax.add_patch(plt.Rectangle((-1.5, gi - 0.5), 0.8, 1,
                                   color=color, clip_on=False))
        if fam != prev_family:
            if prev_family is not None:
                ax.axhline(y=gi - 0.5, color="white", linewidth=2)
            prev_family = fam

    legend_patches = [
        mpatches.Patch(color="#2ecc71", label="Scored"),
        mpatches.Patch(color="#f39c12", label="Mentioned"),
        mpatches.Patch(color="#f0f0f0", label="Not reported"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=3,
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.02))

    ax.set_title("Safety Benchmark Coverage Across AI Models",
                 fontsize=13, fontweight="bold", pad=15)
    plt.tight_layout()
    path = output_dir / "safety_coverage_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Analysis 2: Temporal Analysis
# ---------------------------------------------------------------------------

def build_temporal_safety(safety_evals_df: pd.DataFrame,
                          gens_df: pd.DataFrame,
                          safety_benchmarks: set) -> pd.DataFrame:
    if safety_evals_df.empty:
        return pd.DataFrame()

    # Get safety benchmarks per generation
    gen_benchmarks = (
        safety_evals_df
        .drop_duplicates(subset=["family_slug", "gen_slug", "benchmark_slug"])
        .groupby(["family_slug", "gen_slug"])
        .agg(
            n_safety_benchmarks=("benchmark_slug", "nunique"),
            safety_benchmark_list=("benchmark_slug", lambda x: ", ".join(sorted(x))),
        )
        .reset_index()
    )

    # Merge with generation metadata
    result = gens_df.merge(gen_benchmarks, on=["family_slug", "gen_slug"], how="left")
    result["n_safety_benchmarks"] = result["n_safety_benchmarks"].fillna(0).astype(int)
    result["safety_benchmark_list"] = result["safety_benchmark_list"].fillna("")
    result["cohort"] = result["release_date"].apply(assign_cohort)

    return result


def print_temporal_summary(temporal_df: pd.DataFrame):
    print("\n\n" + "=" * 80)
    print("  ANALYSIS 2: TEMPORAL SAFETY BENCHMARK ADOPTION")
    print("  When did models start reporting safety benchmarks?")
    print("=" * 80)

    if temporal_df.empty:
        print("\n  No temporal data.")
        return

    # Table sorted by release date
    display = temporal_df[temporal_df["n_safety_benchmarks"] > 0].copy()
    display = display.sort_values("release_date", na_position="last")

    table_rows = []
    for _, row in display.iterrows():
        rd = row["release_date"]
        table_rows.append({
            "Family": row["family_slug"],
            "Generation": row["gen_slug"],
            "Release Date": str(rd)[:10] if pd.notna(rd) else "Unknown",
            "Cohort": row["cohort"],
            "# Safety Benchmarks": row["n_safety_benchmarks"],
            "Benchmarks": row["safety_benchmark_list"][:60],
        })
    print()
    print(tabulate(table_rows, headers="keys", tablefmt="simple"))

    # Trend: average per cohort
    cohort_stats = (
        temporal_df[temporal_df["cohort"] != "Unknown"]
        .groupby("cohort")
        .agg(
            n_models=("gen_slug", "nunique"),
            avg_safety_benchmarks=("n_safety_benchmarks", "mean"),
            models_with_safety=("n_safety_benchmarks", lambda x: (x > 0).sum()),
        )
        .reset_index()
        .sort_values("cohort")
    )

    print("\n\n  TREND: Average safety benchmarks per model by cohort")
    for _, row in cohort_stats.iterrows():
        bar_len = int(row["avg_safety_benchmarks"] * 3)
        bar = "#" * bar_len
        print(f"    {row['cohort']}:  {row['avg_safety_benchmarks']:5.1f} avg  "
              f"({row['models_with_safety']:.0f}/{row['n_models']} models)  {bar}")

    # Overall: models with vs without safety benchmarks
    with_safety = len(temporal_df[temporal_df["n_safety_benchmarks"] > 0])
    total = len(temporal_df)
    print(f"\n  Models reporting ANY safety benchmark: {with_safety}/{total} "
          f"({with_safety/total*100:.0f}%)")


def plot_temporal_adoption(temporal_df: pd.DataFrame, output_dir: Path):
    if temporal_df.empty:
        print("  Skipping temporal chart - no data.")
        return

    dated = temporal_df[temporal_df["release_date"].notna()].copy()
    dated["release_date"] = pd.to_datetime(dated["release_date"])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[1, 1])

    # Top: scatter of safety benchmark count per model over time
    for family in sorted(dated["family_slug"].unique()):
        fam = dated[dated["family_slug"] == family]
        color = LAB_COLORS.get(family, "#888888")
        ax1.scatter(fam["release_date"], fam["n_safety_benchmarks"],
                    c=color, s=60, label=family, edgecolors="white", zorder=3)
        # Label points
        for _, row in fam.iterrows():
            if row["n_safety_benchmarks"] > 0:
                ax1.annotate(row["gen_slug"], (row["release_date"], row["n_safety_benchmarks"]),
                             fontsize=6, rotation=20, ha="left", va="bottom")

    # Trend line
    if len(dated) > 2:
        dated_sorted = dated.sort_values("release_date")
        x_num = matplotlib.dates.date2num(dated_sorted["release_date"])
        y = dated_sorted["n_safety_benchmarks"].values
        if len(x_num) > 1 and np.std(x_num) > 0:
            z = np.polyfit(x_num, y, 1)
            p = np.poly1d(z)
            ax1.plot(dated_sorted["release_date"], p(x_num),
                     "--", color="gray", alpha=0.5, label="Trend")

    ax1.set_ylabel("# Safety Benchmarks Reported", fontsize=11)
    ax1.set_title("Safety Benchmark Reporting Over Time", fontsize=13, fontweight="bold")
    ax1.legend(fontsize=8, loc="upper left", ncol=3)
    ax1.grid(axis="y", alpha=0.3)

    # Bottom: stacked area - cumulative adoption of canonical safety benchmarks
    canonical_in_data = sorted(
        CANONICAL_SAFETY_BENCHMARKS & set(temporal_df["safety_benchmark_list"].str.cat(sep=", ").split(", "))
    )

    if canonical_in_data and len(dated) > 0:
        date_range = pd.date_range(
            dated["release_date"].min(),
            dated["release_date"].max(),
            freq="ME",
        )
        if len(date_range) > 1:
            cumulative = pd.DataFrame({"date": date_range})
            for bench in canonical_in_data:
                models_with = dated[dated["safety_benchmark_list"].str.contains(bench, na=False)]
                cumulative[bench] = [
                    len(models_with[models_with["release_date"] <= d])
                    for d in date_range
                ]

            colors_safety = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db"]
            ax2.stackplot(cumulative["date"],
                          *[cumulative[b] for b in canonical_in_data],
                          labels=canonical_in_data,
                          colors=colors_safety[:len(canonical_in_data)],
                          alpha=0.7)
            ax2.legend(fontsize=8, loc="upper left")

    ax2.set_xlabel("Release Date", fontsize=11)
    ax2.set_ylabel("Cumulative Models Reporting", fontsize=11)
    ax2.set_title("Cumulative Adoption of Canonical Safety Benchmarks",
                  fontsize=13, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = output_dir / "temporal_adoption.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Analysis 3: Safety Benchmark Catalog
# ---------------------------------------------------------------------------

def build_safety_catalog(safety_evals_df: pd.DataFrame,
                         all_benchmarks_df: pd.DataFrame,
                         safety_benchmarks: set) -> pd.DataFrame:
    rows = []
    # Check which external validation files exist
    ext_val_files = []
    if EXTERNAL_VALIDATION_DIR.exists():
        ext_val_files = [f.stem.lower() for f in EXTERNAL_VALIDATION_DIR.glob("*.md")]

    for slug in sorted(safety_benchmarks):
        # Get benchmark definition
        bench_def = all_benchmarks_df[all_benchmarks_df["slug"] == slug]
        if len(bench_def) > 0:
            b = bench_def.iloc[0]
            name = b["name"]
            description = b.get("description", "")
            category = b["category"]
            metric = b.get("metric_name", "")
        else:
            # Dynamically created benchmark, get info from evals
            evals = safety_evals_df[safety_evals_df["benchmark_slug"] == slug]
            if len(evals) == 0:
                continue
            name = evals.iloc[0]["benchmark_name"]
            description = evals.iloc[0].get("benchmark_description", "")
            category = evals.iloc[0].get("benchmark_category", "")
            metric = evals.iloc[0].get("metric_name", "")

        # Stats from eval results
        bench_evals = safety_evals_df[safety_evals_df["benchmark_slug"] == slug]
        labs_using = sorted(bench_evals["family_slug"].unique())
        n_labs = len(labs_using)
        n_models = bench_evals["gen_slug"].nunique()

        scored = bench_evals[bench_evals["state"] == "scored"]
        score_min_obs = scored["score"].min() if len(scored) > 0 else None
        score_max_obs = scored["score"].max() if len(scored) > 0 else None
        score_mean = scored["score"].mean() if len(scored) > 0 else None

        # External validation?
        has_ext_val = any(slug.replace("_", "") in f or slug in f for f in ext_val_files)

        # Taxonomy mapping
        taxonomy_cat = BENCHMARK_TO_TAXONOMY.get(slug, "")
        # Try keyword-based taxonomy assignment for unmapped benchmarks
        if not taxonomy_cat and description:
            desc_lower = str(description).lower()
            if any(w in desc_lower for w in ["bias", "fairness", "discriminat"]):
                taxonomy_cat = "bias_fairness"
            elif any(w in desc_lower for w in ["toxic", "hate", "harmful", "violence"]):
                taxonomy_cat = "harmful_content"
            elif any(w in desc_lower for w in ["truthful", "misinformation", "factual"]):
                taxonomy_cat = "misinformation"
            elif any(w in desc_lower for w in ["safety", "refusal", "red team", "guardrail"]):
                taxonomy_cat = "safety_guidelines"
            elif any(w in desc_lower for w in ["cyber", "weapon", "cbrn"]):
                taxonomy_cat = "dual_use"
            elif any(w in desc_lower for w in ["child", "csam", "minor"]):
                taxonomy_cat = "child_safety"
            elif any(w in desc_lower for w in ["privacy", "data handling"]):
                taxonomy_cat = "privacy_data"

        rows.append({
            "slug": slug,
            "name": name,
            "description": str(description)[:200] if description else "",
            "category": category,
            "taxonomy_category": taxonomy_cat,
            "metric": metric,
            "labs_using": ", ".join(labs_using),
            "n_labs": n_labs,
            "n_models": n_models,
            "score_min_observed": score_min_obs,
            "score_max_observed": score_max_obs,
            "score_mean": score_mean,
            "has_external_validation": has_ext_val,
            "is_canonical": slug in CANONICAL_SAFETY_BENCHMARKS,
            "is_proprietary": n_labs == 1,
        })

    return pd.DataFrame(rows).sort_values(["n_labs", "n_models"], ascending=False)


def print_safety_catalog(catalog_df: pd.DataFrame):
    print("\n\n" + "=" * 80)
    print("  ANALYSIS 3: SAFETY BENCHMARK CATALOG")
    print("  What does each safety benchmark measure?")
    print("=" * 80)

    if catalog_df.empty:
        print("\n  No safety benchmarks found.")
        return

    # Widely adopted
    wide = catalog_df[catalog_df["n_labs"] >= 2]
    if len(wide) > 0:
        print("\n  WIDELY ADOPTED (2+ labs):")
        table = wide[["slug", "name", "taxonomy_category", "n_labs", "n_models",
                       "score_mean", "is_canonical"]].copy()
        table.columns = ["Slug", "Name", "Taxonomy Category", "Labs", "Models",
                         "Mean Score", "Canonical"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    # Lab-specific
    proprietary = catalog_df[catalog_df["is_proprietary"]]
    if len(proprietary) > 0:
        print(f"\n  LAB-SPECIFIC ({len(proprietary)} benchmarks used by only 1 lab):")
        table = proprietary[["slug", "name", "labs_using", "n_models",
                              "taxonomy_category"]].head(20).copy()
        table.columns = ["Slug", "Name", "Lab", "Models", "Taxonomy"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple"))

    # Taxonomy coverage gap
    print("\n\n  TAXONOMY COVERAGE GAP ANALYSIS")
    print("  " + "-" * 70)
    measured_cats = set(catalog_df[catalog_df["taxonomy_category"] != ""]["taxonomy_category"])
    for slug, name, nist, eu in TAXONOMY_CATEGORIES:
        benchmarks_for_cat = catalog_df[catalog_df["taxonomy_category"] == slug]
        if len(benchmarks_for_cat) > 0:
            bench_list = ", ".join(benchmarks_for_cat["slug"].tolist())
            status = "COVERED"
        elif slug in measured_cats:
            bench_list = ""
            status = "COVERED"
        else:
            bench_list = ""
            status = "NO BENCHMARK"
        marker = "  [X]" if status == "COVERED" else "  [ ]"
        print(f"  {marker} {name}")
        print(f"       NIST: {nist}  |  EU AI Act: {eu}")
        if bench_list:
            print(f"       Benchmarks: {bench_list}")

    n_covered = len(measured_cats)
    n_total = len(TAXONOMY_CATEGORIES)
    print(f"\n  Coverage: {n_covered}/{n_total} safety categories have at least one benchmark")
    print(f"  Gap: {n_total - n_covered} categories have NO standardized measurement")


# ---------------------------------------------------------------------------
# Analysis 4: Cohort Comparability
# ---------------------------------------------------------------------------

def build_cohort_comparison(temporal_df: pd.DataFrame,
                            safety_evals_df: pd.DataFrame,
                            safety_benchmarks: set) -> pd.DataFrame:
    if temporal_df.empty or safety_evals_df.empty:
        return pd.DataFrame()

    # Build benchmark sets per model
    model_benchmarks = {}
    for _, row in temporal_df.iterrows():
        key = (row["family_slug"], row["gen_slug"])
        benchmarks = set()
        if row["safety_benchmark_list"]:
            benchmarks = set(b.strip() for b in row["safety_benchmark_list"].split(",") if b.strip())
        model_benchmarks[key] = benchmarks

    # Build score lookup
    score_lookup = {}
    for _, row in safety_evals_df.iterrows():
        key = (row["family_slug"], row["gen_slug"], row["benchmark_slug"])
        if row["state"] == "scored" and pd.notna(row["score"]):
            if key not in score_lookup or row["score"] > score_lookup[key]:
                score_lookup[key] = row["score"]

    # Pairwise comparison within cohorts
    rows = []
    for cohort in sorted(temporal_df["cohort"].unique()):
        if cohort == "Unknown":
            continue
        cohort_models = temporal_df[temporal_df["cohort"] == cohort]
        models = [(row["family_slug"], row["gen_slug"]) for _, row in cohort_models.iterrows()]

        if len(models) < 2:
            continue

        for (fam_a, gen_a), (fam_b, gen_b) in combinations(models, 2):
            set_a = model_benchmarks.get((fam_a, gen_a), set())
            set_b = model_benchmarks.get((fam_b, gen_b), set())

            # Skip pairs where neither has safety benchmarks
            if not set_a and not set_b:
                continue

            jaccard = compute_jaccard(set_a, set_b)
            shared = set_a & set_b

            # Compare scores for shared benchmarks
            shared_scores = {}
            for bench in shared:
                score_a = score_lookup.get((fam_a, gen_a, bench))
                score_b = score_lookup.get((fam_b, gen_b, bench))
                if score_a is not None and score_b is not None:
                    shared_scores[bench] = {"model_a": score_a, "model_b": score_b}

            rows.append({
                "cohort": cohort,
                "model_a": f"{fam_a}/{gen_a}",
                "model_b": f"{fam_b}/{gen_b}",
                "benchmarks_a": len(set_a),
                "benchmarks_b": len(set_b),
                "shared_count": len(shared),
                "shared_benchmarks": ", ".join(sorted(shared)) if shared else "",
                "jaccard_similarity": round(jaccard, 3),
                "shared_scores": str(shared_scores) if shared_scores else "",
                "is_comparable": jaccard > 0,
            })

    return pd.DataFrame(rows)


def print_cohort_summary(cohort_df: pd.DataFrame, temporal_df: pd.DataFrame):
    print("\n\n" + "=" * 80)
    print("  ANALYSIS 4: COHORT COMPARABILITY")
    print("  Can we compare safety across models published at similar times?")
    print("=" * 80)

    if cohort_df.empty:
        print("\n  Not enough data for cohort comparison.")
        return

    # Per-cohort summary
    cohort_stats = (
        cohort_df.groupby("cohort")
        .agg(
            n_pairs=("jaccard_similarity", "count"),
            mean_jaccard=("jaccard_similarity", "mean"),
            comparable_pairs=("is_comparable", "sum"),
        )
        .reset_index()
        .sort_values("cohort")
    )

    print("\n  COHORT OVERVIEW (6-month windows)")
    table_rows = []
    for _, row in cohort_stats.iterrows():
        verdict = "Comparable" if row["mean_jaccard"] > 0.3 else (
            "Partial" if row["mean_jaccard"] > 0.05 else "Incomparable"
        )
        table_rows.append({
            "Cohort": row["cohort"],
            "Pairs": int(row["n_pairs"]),
            "Mean Jaccard": f"{row['mean_jaccard']:.3f}",
            "Comparable Pairs": f"{int(row['comparable_pairs'])}/{int(row['n_pairs'])}",
            "Verdict": verdict,
        })
    print(tabulate(table_rows, headers="keys", tablefmt="simple"))

    # Show best comparisons: pairs with highest Jaccard
    if len(cohort_df) > 0:
        best = cohort_df[cohort_df["jaccard_similarity"] > 0].sort_values(
            "jaccard_similarity", ascending=False
        ).head(10)
        if len(best) > 0:
            print("\n\n  BEST COMPARABLE PAIRS:")
            for _, row in best.iterrows():
                print(f"    {row['cohort']}: {row['model_a']} vs {row['model_b']}")
                print(f"      Jaccard={row['jaccard_similarity']:.3f}, "
                      f"shared: {row['shared_benchmarks']}")
                if row["shared_scores"]:
                    print(f"      Scores: {row['shared_scores'][:120]}")

    # Overall
    overall_jaccard = cohort_df["jaccard_similarity"].mean()
    print(f"\n  OVERALL INDUSTRY COMPARABILITY: Jaccard = {overall_jaccard:.3f}")
    if overall_jaccard < 0.1:
        print("  Verdict: INCOMPARABLE - labs use almost entirely different safety benchmarks")
    elif overall_jaccard < 0.3:
        print("  Verdict: PARTIALLY COMPARABLE - some overlap but large gaps")
    else:
        print("  Verdict: REASONABLY COMPARABLE - meaningful overlap exists")


def plot_cohort_comparability(cohort_df: pd.DataFrame, output_dir: Path):
    if cohort_df.empty:
        print("  Skipping cohort chart - no data.")
        return

    cohort_stats = (
        cohort_df.groupby("cohort")
        .agg(
            mean_jaccard=("jaccard_similarity", "mean"),
            n_pairs=("jaccard_similarity", "count"),
        )
        .reset_index()
        .sort_values("cohort")
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    colors = []
    for _, row in cohort_stats.iterrows():
        j = row["mean_jaccard"]
        if j > 0.3:
            colors.append("#2ecc71")
        elif j > 0.05:
            colors.append("#f39c12")
        else:
            colors.append("#e74c3c")

    bars = ax.bar(range(len(cohort_stats)), cohort_stats["mean_jaccard"],
                  color=colors, width=0.6, edgecolor="white")

    for i, (bar, (_, row)) in enumerate(zip(bars, cohort_stats.iterrows())):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{row['mean_jaccard']:.2f}\n({int(row['n_pairs'])} pairs)",
                ha="center", va="bottom", fontsize=8)

    ax.set_xticks(range(len(cohort_stats)))
    ax.set_xticklabels(cohort_stats["cohort"], rotation=45, ha="right", fontsize=10)
    ax.set_ylabel("Mean Jaccard Similarity", fontsize=11)
    ax.set_title("Safety Benchmark Comparability by Temporal Cohort",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, min(cohort_stats["mean_jaccard"].max() * 1.5, 1.0)
                if len(cohort_stats) > 0 else 1.0)
    ax.axhline(y=0.3, color="green", linestyle=":", alpha=0.4, label="Comparable threshold")
    ax.axhline(y=0.05, color="red", linestyle=":", alpha=0.4, label="Incomparable threshold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    legend_patches = [
        mpatches.Patch(color="#2ecc71", label="Comparable (>0.3)"),
        mpatches.Patch(color="#f39c12", label="Partial (0.05-0.3)"),
        mpatches.Patch(color="#e74c3c", label="Incomparable (<0.05)"),
    ]
    ax.legend(handles=legend_patches, loc="upper right", fontsize=9)

    plt.tight_layout()
    path = output_dir / "cohort_comparability.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Analysis 5: Benchmark Lifecycle & Saturation
# ---------------------------------------------------------------------------

def classify_benchmark_lifecycle(evals_df: pd.DataFrame,
                                 gens_df: pd.DataFrame,
                                 all_benchmarks_df: pd.DataFrame) -> pd.DataFrame:
    """Classify each benchmark's lifecycle status per family.

    For each (family, benchmark) pair, determine:
      - Is it saturated (best score >= 95% of score_max)?
      - Was it superseded (dropped, but successor adopted)?
      - Was it suspiciously dropped (dropped without saturation or successor)?
      - Is it still active in the latest generation?
      - Is it emerging (only in recent generations)?
    """
    if evals_df.empty:
        return pd.DataFrame()

    # Build score_max lookup from benchmark definitions
    score_max_lookup = {}
    for _, b in all_benchmarks_df.iterrows():
        sm = b.get("score_max")
        hib = b.get("higher_is_better", True)
        if pd.notna(sm) and hib:
            score_max_lookup[b["slug"]] = sm

    # Deduplicate evals: best score per (family, gen, benchmark)
    deduped = (
        evals_df.sort_values("score", ascending=False, na_position="last")
        .drop_duplicates(subset=["family_slug", "gen_slug", "benchmark_slug"], keep="first")
    )

    rows = []
    for family in sorted(deduped["family_slug"].unique()):
        fam_evals = deduped[deduped["family_slug"] == family]
        fam_gens = (
            gens_df[gens_df["family_slug"] == family]
            .assign(_sk=lambda d: chrono_sort_key(d["gen_slug"]))
            .sort_values("_sk").drop(columns=["_sk"])
        )
        gen_order = list(fam_gens["gen_slug"])
        if not gen_order:
            continue

        latest_gen = gen_order[-1]
        latest_benchmarks = set(
            fam_evals[fam_evals["gen_slug"] == latest_gen]["benchmark_slug"]
        )

        # For "recent" classification, use last 3 generations
        recent_gens = set(gen_order[-3:]) if len(gen_order) >= 3 else set(gen_order)

        for bench in sorted(fam_evals["benchmark_slug"].unique()):
            bench_evals = fam_evals[fam_evals["benchmark_slug"] == bench]
            gens_with = set(bench_evals["gen_slug"])
            best_score = bench_evals["score"].max()
            score_max = score_max_lookup.get(bench, 100.0)

            # Which generation was the last to report it?
            last_gen_idx = max(
                (gen_order.index(g) for g in gens_with if g in gen_order),
                default=-1,
            )
            last_gen = gen_order[last_gen_idx] if last_gen_idx >= 0 else None

            # Is it in the latest generation?
            in_latest = bench in latest_benchmarks

            # Saturation check
            is_saturated = (
                pd.notna(best_score)
                and score_max > 0
                and best_score >= score_max * SATURATION_THRESHOLD_PCT
            )

            # Was it dropped? (appeared in some gen but not the latest)
            was_dropped = not in_latest and len(gens_with) > 0

            # Successor check
            successor_slug = BENCHMARK_SUCCESSORS.get(bench)
            successor_adopted = (
                successor_slug is not None
                and successor_slug != bench  # exclude sentinels
                and successor_slug in latest_benchmarks
            )

            # Only appeared in recent gens
            only_recent = gens_with.issubset(recent_gens) and in_latest

            # Known-issue flags
            is_contaminated = bench in KNOWN_CONTAMINATED
            is_flawed = bench in KNOWN_FLAWED
            is_format_aged = bench in KNOWN_FORMAT_AGED
            is_gamed = bench in KNOWN_GAMED

            # Internal/proprietary eval detection
            is_internal = (
                bench in KNOWN_INTERNAL_SLUGS
                or any(bench.startswith(pfx) for pfx in KNOWN_INTERNAL_PREFIXES)
            )

            # Capability-specific detection: benchmark is tied to a capability
            # that this family may have de-emphasized
            bench_caps = _BENCH_TO_CAPS.get(bench, set())
            is_capability_specific = len(bench_caps) > 0

            # Cost-prohibitive detection
            is_cost_prohibitive = bench in KNOWN_COST_PROHIBITIVE

            # Metric rescaling detection: if score drops >50% between
            # adjacent generations, likely a metric redefinition
            is_metric_change = False
            if was_dropped and len(gens_with) >= 2:
                # Get scores in chronological order
                bench_gen_scores = []
                for g in gen_order:
                    if g in gens_with:
                        g_eval = bench_evals[bench_evals["gen_slug"] == g]
                        if len(g_eval) > 0 and pd.notna(g_eval.iloc[0]["score"]):
                            bench_gen_scores.append(
                                (g, g_eval.iloc[0]["score"])
                            )
                # Check for >50% relative drop between consecutive reported gens
                for i in range(1, len(bench_gen_scores)):
                    prev_score = bench_gen_scores[i - 1][1]
                    curr_score = bench_gen_scores[i][1]
                    if prev_score > 0 and abs(curr_score) < prev_score * (1 - METRIC_CHANGE_DROP_THRESHOLD):
                        is_metric_change = True
                        break

            # Build list of all applicable drop reasons (a benchmark can have multiple)
            drop_reasons = []
            if is_saturated:
                drop_reasons.append("saturated")
            if successor_adopted:
                drop_reasons.append("superseded")
            if is_contaminated:
                drop_reasons.append("contaminated")
            if is_flawed:
                drop_reasons.append("flawed")
            if is_format_aged:
                drop_reasons.append("format_aged")
            if is_gamed:
                drop_reasons.append("gamed")
            if is_internal:
                drop_reasons.append("internal_eval")
            if is_capability_specific:
                drop_reasons.append(f"capability:{','.join(sorted(bench_caps))}")
            if is_cost_prohibitive:
                drop_reasons.append("cost_prohibitive")
            if is_metric_change:
                drop_reasons.append("metric_change")

            # Classify — priority order for the primary lifecycle label
            # Internal evals and one-time benchmarks first (structural, not quality issues)
            if len(gens_with) == 1 and not in_latest and is_internal:
                lifecycle = LIFECYCLE_INTERNAL
            elif len(gens_with) == 1 and not in_latest:
                lifecycle = LIFECYCLE_ONETIME
            elif only_recent and not was_dropped:
                lifecycle = LIFECYCLE_EMERGING
            elif in_latest:
                lifecycle = LIFECYCLE_ACTIVE
            # Dropped benchmarks: check explanations in priority order
            elif was_dropped and is_internal:
                lifecycle = LIFECYCLE_INTERNAL
            elif was_dropped and is_metric_change:
                lifecycle = LIFECYCLE_METRIC_CHG
            elif was_dropped and is_saturated:
                lifecycle = LIFECYCLE_SATURATED
            elif was_dropped and successor_adopted:
                lifecycle = LIFECYCLE_SUPERSEDED
            elif was_dropped and is_contaminated:
                lifecycle = LIFECYCLE_CONTAMINATED
            elif was_dropped and is_flawed:
                lifecycle = LIFECYCLE_FLAWED
            elif was_dropped and is_format_aged:
                lifecycle = LIFECYCLE_FORMAT_AGED
            elif was_dropped and is_cost_prohibitive:
                lifecycle = LIFECYCLE_COST
            elif was_dropped and is_capability_specific:
                lifecycle = LIFECYCLE_CAP_SHIFT
            elif was_dropped:
                lifecycle = LIFECYCLE_SUSPICIOUS
            else:
                lifecycle = LIFECYCLE_ACTIVE

            # Get the score at drop time
            drop_score = None
            if was_dropped and last_gen:
                last_eval = bench_evals[bench_evals["gen_slug"] == last_gen]
                if len(last_eval) > 0:
                    drop_score = last_eval.iloc[0]["score"]

            rows.append({
                "family_slug": family,
                "benchmark_slug": bench,
                "benchmark_name": bench_evals.iloc[0].get("benchmark_name", bench),
                "lifecycle": lifecycle,
                "drop_reasons": ", ".join(drop_reasons) if drop_reasons else "",
                "best_score": best_score,
                "score_max": score_max,
                "saturation_pct": (
                    round(best_score / score_max * 100, 1)
                    if pd.notna(best_score) and score_max > 0 else None
                ),
                "last_gen_reported": last_gen,
                "drop_score": drop_score,
                "successor": successor_slug if successor_slug != bench else None,
                "successor_adopted": successor_adopted,
                "is_contaminated": is_contaminated,
                "is_flawed": is_flawed,
                "is_format_aged": is_format_aged,
                "is_gamed": is_gamed,
                "is_internal": is_internal,
                "is_capability_specific": is_capability_specific,
                "capability_tags": ",".join(sorted(bench_caps)) if bench_caps else "",
                "is_cost_prohibitive": is_cost_prohibitive,
                "is_metric_change": is_metric_change,
                "n_gens_reported": len(gens_with),
                "in_latest_gen": in_latest,
            })

    return pd.DataFrame(rows)


def print_lifecycle_summary(lifecycle_df: pd.DataFrame):
    print("\n\n" + "=" * 80)
    print("  ANALYSIS 5: BENCHMARK LIFECYCLE & DROP REASONS")
    print("  Why benchmarks get dropped: saturation, contamination, flaws, or cherry-picking?")
    print("=" * 80)

    if lifecycle_df.empty:
        print("\n  No lifecycle data.")
        return

    all_statuses = [
        LIFECYCLE_ACTIVE, LIFECYCLE_EMERGING, LIFECYCLE_SATURATED,
        LIFECYCLE_SUPERSEDED, LIFECYCLE_CONTAMINATED, LIFECYCLE_FLAWED,
        LIFECYCLE_FORMAT_AGED, LIFECYCLE_INTERNAL, LIFECYCLE_CAP_SHIFT,
        LIFECYCLE_METRIC_CHG, LIFECYCLE_COST,
        LIFECYCLE_SUSPICIOUS, LIFECYCLE_ONETIME,
    ]

    # Overall counts
    counts = lifecycle_df["lifecycle"].value_counts()
    print("\n  LIFECYCLE CLASSIFICATION (all family x benchmark pairs):")
    for status in all_statuses:
        n = counts.get(status, 0)
        pct = n / len(lifecycle_df) * 100
        print(f"    {status:14s}  {n:4d}  ({pct:4.1f}%)")

    # --- Legitimate drop categories ---

    saturated = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_SATURATED]
    if len(saturated) > 0:
        print("\n  SATURATED (score >= 95% of max — reasonably retired):")
        table = saturated[["family_slug", "benchmark_slug", "best_score",
                           "score_max", "saturation_pct", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Best Score", "Max", "% of Max", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    superseded = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_SUPERSEDED]
    if len(superseded) > 0:
        print("\n  SUPERSEDED (replaced by harder successor):")
        table = superseded[["family_slug", "benchmark_slug", "successor",
                            "drop_score", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Successor", "Score at Drop", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    contaminated = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_CONTAMINATED]
    if len(contaminated) > 0:
        print("\n  CONTAMINATED (known data leakage into training sets):")
        table = contaminated[["family_slug", "benchmark_slug", "best_score",
                              "drop_score", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Best Score", "Score at Drop", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    flawed = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_FLAWED]
    if len(flawed) > 0:
        print("\n  FLAWED (known methodological issues — label errors, ambiguous questions):")
        table = flawed[["family_slug", "benchmark_slug", "best_score",
                        "drop_score", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Best Score", "Score at Drop", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    format_aged = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_FORMAT_AGED]
    if len(format_aged) > 0:
        print("\n  FORMAT AGED (task format no longer relevant — MCQ shortcuts, isolated tasks):")
        table = format_aged[["family_slug", "benchmark_slug", "best_score",
                             "drop_score", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Best Score", "Score at Drop", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    internal = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_INTERNAL]
    if len(internal) > 0:
        print(f"\n  INTERNAL/PROPRIETARY ({len(internal)} — lab-specific evals, not meant for cross-gen tracking):")
        table = internal[["family_slug", "benchmark_slug", "n_gens_reported",
                          "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Gens Reported", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple"))

    cap_shift = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_CAP_SHIFT]
    if len(cap_shift) > 0:
        print(f"\n  CAPABILITY SHIFT ({len(cap_shift)} — dropped when lab de-emphasized capability):")
        table = cap_shift[["family_slug", "benchmark_slug", "capability_tags",
                           "best_score", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Capability", "Best Score", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    metric_chg = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_METRIC_CHG]
    if len(metric_chg) > 0:
        print(f"\n  METRIC CHANGE ({len(metric_chg)} — score rescaling or metric redefinition):")
        table = metric_chg[["family_slug", "benchmark_slug", "best_score",
                            "drop_score", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Best Score", "Score at Drop", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    cost_prohib = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_COST]
    if len(cost_prohib) > 0:
        print(f"\n  COST PROHIBITIVE ({len(cost_prohib)} — expensive human eval / agent benchmarks):")
        table = cost_prohib[["family_slug", "benchmark_slug", "best_score",
                             "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Best Score", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))

    # --- Suspicious drops ---
    suspicious = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_SUSPICIOUS]
    if len(suspicious) > 0:
        print(f"\n  SUSPICIOUS DROPS ({len(suspicious)} — no identified legitimate reason):")
        table = suspicious[["family_slug", "benchmark_slug", "best_score",
                            "saturation_pct", "drop_score", "last_gen_reported"]].copy()
        table.columns = ["Family", "Benchmark", "Best Score", "% of Max",
                         "Score at Drop", "Last Gen"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple", floatfmt=".1f"))
    else:
        print("\n  No suspicious drops detected.")

    # --- Benchmarks with multiple known issues (even if still active) ---
    multi_issue = lifecycle_df[lifecycle_df["drop_reasons"].str.count(",") >= 1]
    if len(multi_issue) > 0:
        print("\n  BENCHMARKS WITH MULTIPLE KNOWN ISSUES:")
        table = multi_issue[["family_slug", "benchmark_slug", "lifecycle",
                             "drop_reasons"]].drop_duplicates(
            subset=["benchmark_slug", "drop_reasons"]
        ).copy()
        table.columns = ["Family", "Benchmark", "Status", "Known Issues"]
        print(tabulate(table.values.tolist(), headers=table.columns.tolist(),
                       tablefmt="simple"))

    # Per-family summary
    print("\n  LIFECYCLE SUMMARY BY FAMILY:")
    family_stats = (
        lifecycle_df.groupby(["family_slug", "lifecycle"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=all_statuses, fill_value=0)
        .reset_index()
    )
    print(tabulate(family_stats.values.tolist(),
                   headers=family_stats.columns.tolist(), tablefmt="simple"))

    # Adjusted churn
    legitimate_reasons = {
        LIFECYCLE_SATURATED, LIFECYCLE_SUPERSEDED,
        LIFECYCLE_CONTAMINATED, LIFECYCLE_FLAWED, LIFECYCLE_FORMAT_AGED,
        LIFECYCLE_INTERNAL, LIFECYCLE_CAP_SHIFT,
        LIFECYCLE_METRIC_CHG, LIFECYCLE_COST,
    }
    all_dropped = lifecycle_df[~lifecycle_df["lifecycle"].isin(
        [LIFECYCLE_ACTIVE, LIFECYCLE_EMERGING]
    )]
    legit = lifecycle_df[lifecycle_df["lifecycle"].isin(legitimate_reasons)]
    onetime = lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_ONETIME]
    print(f"\n  ADJUSTED CHURN ANALYSIS:")
    print(f"    Total benchmarks ever dropped:      {len(all_dropped)}")
    print(f"    Drops with legitimate explanation:   {len(legit)}")
    print(f"      - Saturated (ceiling reached):     {len(saturated)}")
    print(f"      - Superseded (harder replacement): {len(superseded)}")
    print(f"      - Contaminated (data leakage):     {len(contaminated)}")
    print(f"      - Flawed (methodology issues):     {len(flawed)}")
    print(f"      - Format aged (MCQ/isolated):      {len(format_aged)}")
    print(f"      - Internal/proprietary eval:       {len(internal)}")
    print(f"      - Capability shift:                {len(cap_shift)}")
    print(f"      - Metric change/rescaling:         {len(metric_chg)}")
    print(f"      - Cost prohibitive:                {len(cost_prohib)}")
    print(f"    Suspicious/unexplained drops:        {len(suspicious)}")
    print(f"    One-time (never repeated):           {len(onetime)}")
    if len(all_dropped) > 0:
        legit_pct = len(legit) / len(all_dropped) * 100
        susp_pct = len(suspicious) / len(all_dropped) * 100
        onetime_pct = len(onetime) / len(all_dropped) * 100
        print(f"    Legitimate retirement rate:         {legit_pct:.0f}%")
        print(f"    Suspicious drop rate:               {susp_pct:.0f}%")
        print(f"    One-time rate:                      {onetime_pct:.0f}%")


def plot_lifecycle_chart(lifecycle_df: pd.DataFrame, output_dir: Path):
    if lifecycle_df.empty:
        print("  Skipping lifecycle chart - no data.")
        return

    status_colors = {
        LIFECYCLE_ACTIVE: "#2ecc71",
        LIFECYCLE_EMERGING: "#3498db",
        LIFECYCLE_SATURATED: "#95a5a6",
        LIFECYCLE_SUPERSEDED: "#f39c12",
        LIFECYCLE_CONTAMINATED: "#9b59b6",
        LIFECYCLE_FLAWED: "#e67e22",
        LIFECYCLE_FORMAT_AGED: "#1abc9c",
        LIFECYCLE_INTERNAL: "#7f8c8d",
        LIFECYCLE_CAP_SHIFT: "#2c3e50",
        LIFECYCLE_METRIC_CHG: "#d35400",
        LIFECYCLE_COST: "#8e44ad",
        LIFECYCLE_SUSPICIOUS: "#e74c3c",
        LIFECYCLE_ONETIME: "#bdc3c7",
    }
    status_order = [
        LIFECYCLE_ACTIVE, LIFECYCLE_EMERGING, LIFECYCLE_SATURATED,
        LIFECYCLE_SUPERSEDED, LIFECYCLE_CONTAMINATED, LIFECYCLE_FLAWED,
        LIFECYCLE_FORMAT_AGED, LIFECYCLE_INTERNAL, LIFECYCLE_CAP_SHIFT,
        LIFECYCLE_METRIC_CHG, LIFECYCLE_COST,
        LIFECYCLE_SUSPICIOUS, LIFECYCLE_ONETIME,
    ]

    family_stats = (
        lifecycle_df.groupby(["family_slug", "lifecycle"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=status_order, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(16, 7))
    families = family_stats.index.tolist()
    x = np.arange(len(families))
    n_statuses = len(status_order)
    bar_width = 0.8 / n_statuses

    for i, status in enumerate(status_order):
        if status in family_stats.columns:
            vals = family_stats[status].values
            ax.bar(x + i * bar_width, vals, bar_width,
                   label=status, color=status_colors[status], edgecolor="white")

    ax.set_xticks(x + bar_width * n_statuses / 2)
    ax.set_xticklabels(families, rotation=45, ha="right", fontsize=10)
    ax.set_ylabel("# Benchmarks", fontsize=11)
    ax.set_title("Benchmark Lifecycle Status by Lab",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = output_dir / "benchmark_lifecycle.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def compute_era_appropriate_benchmarks(lifecycle_df: pd.DataFrame,
                                       gens_df: pd.DataFrame) -> pd.DataFrame:
    """For each generation, compute which benchmarks were 'era-appropriate'
    (not yet saturated or superseded at the time of that generation).

    Returns a DataFrame with adjusted benchmark counts."""
    if lifecycle_df.empty:
        return pd.DataFrame()

    rows = []
    for family in sorted(lifecycle_df["family_slug"].unique()):
        fam_lifecycle = lifecycle_df[lifecycle_df["family_slug"] == family]
        fam_gens = (
            gens_df[gens_df["family_slug"] == family]
            .assign(_sk=lambda d: chrono_sort_key(d["gen_slug"]))
            .sort_values("_sk").drop(columns=["_sk"])
        )
        gen_order = list(fam_gens["gen_slug"])

        for gen_idx, gen_slug in enumerate(gen_order):
            # Benchmarks reported by this generation
            gen_benchmarks = set(
                fam_lifecycle[
                    fam_lifecycle["benchmark_slug"].isin(
                        fam_lifecycle[fam_lifecycle["in_latest_gen"] |
                                     (fam_lifecycle["last_gen_reported"].isin(
                                         gen_order[gen_idx:]))]["benchmark_slug"]
                    )
                ]["benchmark_slug"]
            )
            # Actually, let's just count what this gen reported vs what was available
            # "available" = not yet saturated by a PRIOR generation in this family
            reported_by_gen = set(
                fam_lifecycle[
                    fam_lifecycle["benchmark_slug"].isin(
                        fam_lifecycle["benchmark_slug"]
                    ) & (fam_lifecycle["last_gen_reported"].apply(
                        lambda lg: lg in gen_order and gen_order.index(lg) >= gen_idx
                        if lg in gen_order else False
                    ) | fam_lifecycle["in_latest_gen"])
                ]["benchmark_slug"]
            )

            # Simpler approach: count lifecycle categories for benchmarks
            # that were active AT THE TIME of this generation
            active_at_time = []
            saturated_at_time = []
            for _, bench_row in fam_lifecycle.iterrows():
                last_gen = bench_row["last_gen_reported"]
                if last_gen not in gen_order:
                    continue
                last_idx = gen_order.index(last_gen)
                if last_idx >= gen_idx:
                    # This benchmark was still being reported at or after this gen
                    active_at_time.append(bench_row["benchmark_slug"])
                elif bench_row["lifecycle"] in (LIFECYCLE_SATURATED, LIFECYCLE_SUPERSEDED):
                    saturated_at_time.append(bench_row["benchmark_slug"])

            rows.append({
                "family_slug": family,
                "gen_slug": gen_slug,
                "total_benchmarks_reported": len(active_at_time),
                "saturated_by_then": len(saturated_at_time),
                "era_appropriate_pool": len(active_at_time) + len(saturated_at_time),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Final Synthesis: Standardization Recommendation
# ---------------------------------------------------------------------------

def print_standardization_recommendation(catalog_df: pd.DataFrame,
                                         cohort_df: pd.DataFrame,
                                         temporal_df: pd.DataFrame,
                                         matrix_df: pd.DataFrame,
                                         lifecycle_df: pd.DataFrame = None):
    print("\n\n" + "=" * 80)
    print("  SYNTHESIS: STANDARDIZED BENCHMARK RECOMMENDATION")
    print("=" * 80)

    if catalog_df.empty:
        print("\n  Insufficient data for recommendations.")
        return

    # Lifecycle-adjusted context
    if lifecycle_df is not None and not lifecycle_df.empty:
        saturated_slugs = set(
            lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_SATURATED]["benchmark_slug"]
        )
        superseded_slugs = set(
            lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_SUPERSEDED]["benchmark_slug"]
        )
        suspicious_slugs = set(
            lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_SUSPICIOUS]["benchmark_slug"]
        )
        internal_slugs = set(
            lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_INTERNAL]["benchmark_slug"]
        )
        cap_shift_slugs = set(
            lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_CAP_SHIFT]["benchmark_slug"]
        )
        metric_chg_slugs = set(
            lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_METRIC_CHG]["benchmark_slug"]
        )
        cost_slugs = set(
            lifecycle_df[lifecycle_df["lifecycle"] == LIFECYCLE_COST]["benchmark_slug"]
        )
        explained = (len(saturated_slugs) + len(superseded_slugs) + len(internal_slugs) +
                     len(cap_shift_slugs) + len(metric_chg_slugs) + len(cost_slugs))
        print("\n  NOTE: Benchmark lifecycle context applied.")
        print(f"    {len(saturated_slugs)} benchmarks flagged as saturated (near-ceiling scores)")
        print(f"    {len(superseded_slugs)} benchmarks superseded by harder successors")
        print(f"    {len(internal_slugs)} benchmarks identified as internal/proprietary evals")
        print(f"    {len(cap_shift_slugs)} benchmarks dropped due to capability focus shift")
        print(f"    {len(metric_chg_slugs)} benchmarks with metric rescaling detected")
        print(f"    {len(cost_slugs)} benchmarks dropped due to evaluation cost")
        print(f"    {len(suspicious_slugs)} benchmarks dropped without explanation")
    else:
        saturated_slugs = set()
        superseded_slugs = set()
        suspicious_slugs = set()
        internal_slugs = set()
        cap_shift_slugs = set()
        metric_chg_slugs = set()
        cost_slugs = set()

    # Tier 1: 3+ labs
    tier1 = catalog_df[catalog_df["n_labs"] >= 3]
    # Tier 2: 2 labs
    tier2 = catalog_df[(catalog_df["n_labs"] == 2) & (~catalog_df["slug"].isin(tier1["slug"]))]
    # Tier 3: 1 lab, canonical or high-model-count
    tier3 = catalog_df[
        (catalog_df["n_labs"] == 1)
        & ((catalog_df["is_canonical"]) | (catalog_df["n_models"] >= 3))
    ]

    def _lifecycle_tag(slug):
        """Return a lifecycle annotation string for a benchmark."""
        tags = []
        if slug in saturated_slugs:
            tags.append("SATURATED - near ceiling")
        if slug in superseded_slugs:
            succ = BENCHMARK_SUCCESSORS.get(slug, "?")
            tags.append(f"SUPERSEDED by {succ}")
        if slug in internal_slugs:
            tags.append("INTERNAL eval")
        if slug in cap_shift_slugs:
            caps = _BENCH_TO_CAPS.get(slug, set())
            tags.append(f"CAP_SHIFT: {','.join(sorted(caps))}" if caps else "CAP_SHIFT")
        if slug in metric_chg_slugs:
            tags.append("METRIC rescaled")
        if slug in cost_slugs:
            tags.append("COST prohibitive")
        if slug in suspicious_slugs:
            tags.append("DROPPED w/o explanation by some labs")
        if tags:
            return f" [{'; '.join(tags)}]"
        return ""

    print("\n  TIER 1 - MANDATORY DISCLOSURE (used by 3+ labs):")
    if len(tier1) > 0:
        for _, row in tier1.iterrows():
            tag = _lifecycle_tag(row['slug'])
            print(f"    - {row['name']} ({row['slug']}){tag}")
            print(f"      Measures: {row['taxonomy_category'] or 'general'}")
            print(f"      Used by {row['n_labs']} labs, {row['n_models']} models")
            if pd.notna(row['score_mean']):
                print(f"      Score range: {row['score_min_observed']:.1f}-{row['score_max_observed']:.1f} "
                      f"(mean: {row['score_mean']:.1f})")
    else:
        print("    None - no benchmark is used by 3+ labs!")
        print("    This is itself a critical finding: there is NO industry consensus")

    print("\n  TIER 2 - RECOMMENDED (used by 2 labs):")
    if len(tier2) > 0:
        for _, row in tier2.iterrows():
            tag = _lifecycle_tag(row['slug'])
            print(f"    - {row['name']} ({row['slug']}){tag}")
            print(f"      Measures: {row['taxonomy_category'] or 'general'}")
            print(f"      Used by: {row['labs_using']}")
    else:
        print("    None")

    print("\n  TIER 3 - EMERGING (single-lab but noteworthy):")
    if len(tier3) > 0:
        for _, row in tier3.iterrows():
            print(f"    - {row['name']} ({row['slug']}) - {row['labs_using']}")
            print(f"      Measures: {row['taxonomy_category'] or 'unclassified'}")
    else:
        print("    None")

    # Gaps
    measured_cats = set(catalog_df[catalog_df["taxonomy_category"] != ""]["taxonomy_category"])
    unmeasured = [
        (slug, name, nist, eu)
        for slug, name, nist, eu in TAXONOMY_CATEGORIES
        if slug not in measured_cats
    ]
    print(f"\n  CRITICAL GAPS ({len(unmeasured)} of {len(TAXONOMY_CATEGORIES)} "
          f"safety categories have NO benchmark):")
    for slug, name, nist, eu in unmeasured:
        print(f"    - {name}")
        print(f"      NIST: {nist}  |  EU AI Act: {eu}")
        print(f"      NEW BENCHMARK NEEDED")

    # Overall comparability
    if not cohort_df.empty:
        overall = cohort_df["jaccard_similarity"].mean()
        print(f"\n  INDUSTRY COMPARABILITY SCORE: {overall:.3f} (Jaccard)")
    else:
        print("\n  INDUSTRY COMPARABILITY SCORE: N/A (insufficient data)")

    # Temporal trend
    if not temporal_df.empty:
        dated = temporal_df[temporal_df["cohort"] != "Unknown"].copy()
        if len(dated) > 0:
            cohorts = sorted(dated["cohort"].unique())
            if len(cohorts) >= 2:
                early = dated[dated["cohort"] == cohorts[0]]["n_safety_benchmarks"].mean()
                late = dated[dated["cohort"] == cohorts[-1]]["n_safety_benchmarks"].mean()
                if late > early:
                    print(f"\n  TREND: Safety benchmarking is INCREASING "
                          f"({early:.1f} -> {late:.1f} avg benchmarks/model)")
                else:
                    print(f"\n  TREND: Safety benchmarking is STAGNANT or DECLINING "
                          f"({early:.1f} -> {late:.1f} avg benchmarks/model)")

    # External validation
    ext_val_count = catalog_df["has_external_validation"].sum()
    print(f"\n  EXTERNAL VALIDATION: {ext_val_count}/{len(catalog_df)} safety benchmarks "
          f"have independent leaderboards")
    if ext_val_count == 0:
        print("  WARNING: Zero safety benchmarks are tracked by external evaluators.")
        print("  All safety claims are self-reported and unverifiable from public data alone.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Safety benchmark landscape analysis across AI model cards"
    )
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL),
                        help="PostgreSQL connection URL")
    parser.add_argument("--all-evals", action="store_true",
                        help="Analyze ALL benchmarks, not just safety-relevant ones")
    args = parser.parse_args()

    db_url = args.db_url.replace("+asyncpg", "")

    print("Connecting to database...")
    try:
        engine = get_engine(db_url)
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        print(f"  URL: {db_url}")
        print("  Is Docker running?  Try: make dev")
        sys.exit(1)

    # Determine scope
    all_evals_mode = args.all_evals
    scope_label = "ALL BENCHMARKS" if all_evals_mode else "SAFETY BENCHMARKS"
    out_dir = (Path(__file__).parent.parent / "output" / "analysis" / "all_evals"
               if all_evals_mode else OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Load data ---
    print("Querying all eval results...")
    all_evals_df = query_all_evals(engine)
    print(f"  Found {len(all_evals_df)} eval results")

    print("Querying all benchmark definitions...")
    all_benchmarks_df = query_all_benchmarks(engine)
    print(f"  Found {len(all_benchmarks_df)} benchmark definitions")

    print("Querying all generations...")
    gens_df = query_all_generations(engine)
    print(f"  Found {len(gens_df)} model generations")

    # --- Determine benchmark scope ---
    if all_evals_mode:
        print(f"\nMode: ALL EVALS — including every benchmark in the database")
        target_benchmarks = set(all_evals_df["benchmark_slug"].unique())
        print(f"  {len(target_benchmarks)} benchmarks with eval results")
        filtered_evals_df = all_evals_df.copy()
    else:
        print("\nIdentifying safety-relevant benchmarks...")
        target_benchmarks = identify_safety_benchmarks(all_evals_df, all_benchmarks_df)
        print(f"  Found {len(target_benchmarks)} safety-relevant benchmarks:")
        for slug in sorted(target_benchmarks):
            canonical = " (canonical)" if slug in CANONICAL_SAFETY_BENCHMARKS else ""
            print(f"    - {slug}{canonical}")
        filtered_evals_df = all_evals_df[
            all_evals_df["benchmark_slug"].isin(target_benchmarks)
        ].copy()

    print(f"\n  {len(filtered_evals_df)} eval results in scope ({scope_label})")

    if filtered_evals_df.empty:
        print("\nNo eval results found. Nothing to analyze.")
        sys.exit(0)

    # --- Analysis 1: Coverage Matrix ---
    print("\n" + "-" * 40)
    print(f"Building coverage matrix ({scope_label})...")
    matrix_df = build_safety_coverage_matrix(filtered_evals_df, gens_df, target_benchmarks)
    matrix_csv = out_dir / "coverage_matrix.csv"
    matrix_df.to_csv(matrix_csv, index=False)
    print(f"  Saved: {matrix_csv}")
    print_safety_coverage(matrix_df)
    plot_safety_coverage_heatmap(matrix_df, out_dir)

    # --- Analysis 2: Temporal ---
    print("\n" + "-" * 40)
    print(f"Building temporal analysis ({scope_label})...")
    temporal_df = build_temporal_safety(filtered_evals_df, gens_df, target_benchmarks)
    temporal_csv = out_dir / "temporal.csv"
    temporal_df.to_csv(temporal_csv, index=False)
    print(f"  Saved: {temporal_csv}")
    print_temporal_summary(temporal_df)
    plot_temporal_adoption(temporal_df, out_dir)

    # --- Analysis 3: Catalog ---
    print("\n" + "-" * 40)
    print(f"Building benchmark catalog ({scope_label})...")
    catalog_df = build_safety_catalog(filtered_evals_df, all_benchmarks_df, target_benchmarks)
    catalog_csv = out_dir / "benchmark_catalog.csv"
    catalog_df.to_csv(catalog_csv, index=False)
    print(f"  Saved: {catalog_csv}")
    print_safety_catalog(catalog_df)

    # --- Analysis 4: Cohort Comparability ---
    print("\n" + "-" * 40)
    print(f"Building cohort comparability ({scope_label})...")
    cohort_df = build_cohort_comparison(temporal_df, filtered_evals_df, target_benchmarks)
    cohort_csv = out_dir / "cohort_comparison.csv"
    cohort_df.to_csv(cohort_csv, index=False)
    print(f"  Saved: {cohort_csv}")
    print_cohort_summary(cohort_df, temporal_df)
    plot_cohort_comparability(cohort_df, out_dir)

    # --- Analysis 5: Benchmark Lifecycle & Saturation ---
    print("\n" + "-" * 40)
    print(f"Building benchmark lifecycle analysis ({scope_label})...")
    lifecycle_df = classify_benchmark_lifecycle(filtered_evals_df, gens_df, all_benchmarks_df)
    lifecycle_csv = out_dir / "benchmark_lifecycle.csv"
    lifecycle_df.to_csv(lifecycle_csv, index=False)
    print(f"  Saved: {lifecycle_csv}")
    print_lifecycle_summary(lifecycle_df)
    plot_lifecycle_chart(lifecycle_df, out_dir)

    # --- Final Synthesis ---
    print_standardization_recommendation(catalog_df, cohort_df, temporal_df, matrix_df,
                                         lifecycle_df)

    # --- Done ---
    print("\n" + "=" * 80)
    print(f"  ANALYSIS COMPLETE ({scope_label})")
    print(f"  Artifacts saved to: {out_dir.resolve()}")
    print("=" * 80)


if __name__ == "__main__":
    main()
