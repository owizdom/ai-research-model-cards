#!/usr/bin/env python3
"""
Analysis: Benchmark Overlap & Narrative Convergence Across AI Model Cards
=========================================================================
Two-part analysis:
  1. Quantitative: How much do labs' benchmark selections overlap, and how
     has that changed over time?  Focus on 2026 cards.
  2. Qualitative: How do labs' narrative discussions converge or diverge?
     Compares taxonomy coverage, chapter prose, and verbatim quotes.

Usage:
    python scripts/analyze_benchmark_overlap.py [--db-url URL] [--threshold 0.25]

Outputs (in output/analysis/overlap/):
    - overlap_over_time.csv            Per-cohort aggregate Jaccard
    - overlap_2026.csv                 2026-only pairwise with score comparisons
    - thematic_overlap.csv             2026 labs x taxonomy categories
    - thematic_over_time.csv           Topic convergence/divergence trend
    - chapter_comparison.csv           Side-by-side chapter prose (2026)
    - narrative_quotes.csv             Verbatim quote extracts (2026)
    - benchmark_overlap_explorer.html  Interactive 4-tab visualization
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_DB_URL = os.getenv(
    "RAILWAY_DB_URL",
    "postgresql://postgres:EhJrykdvTfzmimVtioekfVUYppGRowxm@hopper.proxy.rlwy.net:37555/railway",
)
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "analysis" / "overlap"
SIMILARITY_THRESHOLD = 0.25

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
    "anthropic": "#D4791A", "openai": "#10A37F", "google": "#4285F4",
    "meta": "#0866FF", "xai": "#1DA1F2", "mistral": "#FF7000",
    "cohere": "#39594D", "amazon": "#FF9900", "ai21": "#6C3CE1",
}
LAB_NAMES = {
    "anthropic": "Anthropic", "openai": "OpenAI", "google": "Google",
    "meta": "Meta", "xai": "xAI", "mistral": "Mistral",
    "cohere": "Cohere", "amazon": "Amazon", "ai21": "AI21",
}
# Map family slugs to lab slugs (they differ: claude -> anthropic, gpt -> openai, etc.)
FAMILY_TO_LAB = {
    "claude": "anthropic", "gpt": "openai", "gemini": "google",
    "llama": "meta", "grok": "xai", "mistral": "mistral",
    "command": "cohere", "nova": "amazon", "jamba": "ai21",
}

TAXONOMY_ORDER = [
    "safety_guidelines", "alignment_values", "bias_fairness", "privacy_data",
    "transparency", "harmful_content", "dual_use", "political_neutrality",
    "human_oversight", "agentic_behavior", "creative_fiction",
    "legal_compliance", "misinformation", "child_safety", "mental_health",
]
TAXONOMY_DISPLAY = {
    "safety_guidelines": "Safety Guidelines",
    "alignment_values": "Alignment & Values",
    "bias_fairness": "Bias & Fairness",
    "privacy_data": "Privacy & Data",
    "transparency": "Transparency",
    "harmful_content": "Harmful Content",
    "dual_use": "Dual-Use & Weapons",
    "political_neutrality": "Political Neutrality",
    "human_oversight": "Human Oversight",
    "agentic_behavior": "Agentic Behavior",
    "creative_fiction": "Creative Content",
    "legal_compliance": "Legal Compliance",
    "misinformation": "Misinformation",
    "child_safety": "Child Safety",
    "mental_health": "Mental Health",
}

BENCHMARK_SLUG_TO_TAXONOMY = {
    "truthfulqa": "misinformation",
    "bbq": "bias_fairness",
    "toxigen": "harmful_content",
}

CHAPTER_TITLES = [
    "What this is", "Capabilities", "Evaluation methodology",
    "Safety testing", "Mitigations", "Deployment and access",
    "Limitations", "What's new",
]

# Regex patterns for verbatim quote extraction (from apps/api/src/api/v1/documents.py)
_SENT_END = r"(?:[.!?](?=\s+[A-Z0-9]|\s*\n|\s*$))"

_CAPABILITY_PATTERNS = re.compile(
    r"(we (?:are releasing|release|are introducing|have trained|trained|"
    r"introduce|present) [^\n]{10,400}?)" + _SENT_END,
    re.IGNORECASE,
)
_SAFETY_PATTERNS = re.compile(
    r"((?:we (?:decided|elected) not to|we have not been able to|"
    r"we did not (?:release|deploy)|"
    r"not (?:release|deploy|make available)|crossed our (?:threshold|trigger)|"
    r"elicited (?:harmful|dangerous|unsafe)|would not release|withheld|"
    r"refused to (?:release|deploy)|approaching (?:our )?threshold|"
    r"cannot rule out|we cannot exclude|we believe[^\n]{10,200}risk)"
    r"[^\n]{0,300}?)" + _SENT_END,
    re.IGNORECASE,
)
_MITIGATION_PATTERNS = re.compile(
    r"((?:mitigations? include|we (?:have )?deployed|classifier (?:trained|deployed)|"
    r"we (?:trained|finetuned) [A-Za-z\-\d.]+ to (?:follow|refuse|avoid|decline))"
    r"[^\n]{0,300}?)" + _SENT_END,
    re.IGNORECASE,
)
_LIMITATION_PATTERNS = re.compile(
    r"((?:limitations? include|we did not evaluate|we have not evaluated|"
    r"we do not (?:yet|currently) (?:know|understand|measure|evaluate)|"
    r"future work|remain(?:s|ing) (?:open|uncertain)|open questions?|"
    r"still limited|not (?:yet )?well understood|further research)"
    r"[^\n]{10,300}?)" + _SENT_END,
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_engine(db_url: str):
    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return engine


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


def _normalize_whitespace(md: str) -> str:
    """Collapse excessive whitespace (common in OCR-extracted cards)."""
    return re.sub(r"[ \t]+", " ", md).replace("\n \n", "\n\n")


def _find_all_matches(pattern: re.Pattern, md: str, max_results: int = 3) -> list[str]:
    results: list[str] = []
    for m in pattern.finditer(md):
        quote = re.sub(r"\s+", " ", m.group(0)).strip()
        if len(quote) >= 20 and quote not in results:
            results.append(quote)
            if len(results) >= max_results:
                break
    return results


# ---------------------------------------------------------------------------
# Database Queries
# ---------------------------------------------------------------------------

def query_eval_data(engine) -> pd.DataFrame:
    """Benchmark eval results with family/gen/release_date context."""
    sql = text("""
        SELECT
            mf.slug   AS family_slug,
            mf.name   AS family_name,
            mg.slug   AS gen_slug,
            mg.name   AS gen_name,
            mg.release_date,
            bd.slug   AS benchmark_slug,
            bd.name   AS benchmark_name,
            er.score,
            er.state
        FROM model_families mf
        JOIN model_generations mg ON mg.family_id = mf.id
        JOIN eval_results er ON er.generation_id = mg.id
        JOIN benchmark_definitions bd ON bd.id = er.benchmark_id
        ORDER BY mf.slug, mg.release_date, bd.slug
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    df["cohort"] = df["release_date"].apply(assign_cohort)
    df["lab_slug"] = df["family_slug"].map(FAMILY_TO_LAB).fillna(df["family_slug"])
    return df


def query_thematic_data(engine) -> pd.DataFrame:
    """Taxonomy similarity scores per document version."""
    sql = text("""
        SELECT
            l.slug              AS lab_slug,
            l.name              AS lab_name,
            d.slug              AS document_slug,
            dv.version_date,
            tc.slug             AS category_slug,
            tc.name             AS category_name,
            dtm.similarity_score,
            dtm.is_covered
        FROM labs l
        JOIN documents d ON d.lab_id = l.id AND d.doc_type = 'model_card'
        JOIN document_versions dv ON dv.document_id = d.id
        JOIN document_taxonomy_mappings dtm ON dtm.document_version_id = dv.id
        JOIN taxonomy_categories tc ON tc.id = dtm.taxonomy_category_id
            AND tc.parent_id IS NULL
        ORDER BY l.slug, dv.version_date, tc.slug
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    df["cohort"] = df["version_date"].apply(assign_cohort)
    return df


def query_chapter_data(engine) -> pd.DataFrame:
    """LLM-generated chapter summaries per document version."""
    sql = text("""
        SELECT
            l.slug              AS lab_slug,
            l.name              AS lab_name,
            d.id                AS document_id,
            d.slug              AS document_slug,
            d.title             AS document_title,
            dv.version_date,
            ds.chapters
        FROM labs l
        JOIN documents d ON d.lab_id = l.id AND d.doc_type = 'model_card'
        JOIN document_versions dv ON dv.document_id = d.id
        JOIN document_summaries ds ON ds.document_version_id = dv.id
        WHERE ds.error IS NULL AND ds.chapters IS NOT NULL
        ORDER BY l.slug, dv.version_date DESC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    df["cohort"] = df["version_date"].apply(assign_cohort)
    return df


def query_narrative_content(engine) -> pd.DataFrame:
    """Raw markdown content for verbatim quote extraction."""
    sql = text("""
        SELECT
            l.slug              AS lab_slug,
            l.name              AS lab_name,
            d.slug              AS document_slug,
            d.title             AS document_title,
            dv.version_date,
            dv.content_md
        FROM labs l
        JOIN documents d ON d.lab_id = l.id AND d.doc_type = 'model_card'
        JOIN document_versions dv ON dv.document_id = d.id
        WHERE dv.content_md IS NOT NULL AND dv.content_md != ''
        ORDER BY l.slug, dv.version_date DESC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    df["cohort"] = df["version_date"].apply(assign_cohort)
    return df


# ---------------------------------------------------------------------------
# Analysis 1: Pairwise Benchmark Overlap (all cohorts)
# ---------------------------------------------------------------------------

def build_pairwise_overlap(eval_df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise Jaccard between labs per cohort, using family_slug as lab identity."""
    rows = []
    for cohort in sorted(eval_df["cohort"].unique()):
        if cohort == "Unknown":
            continue
        cohort_df = eval_df[eval_df["cohort"] == cohort]
        families = sorted(cohort_df["family_slug"].unique())

        # Build benchmark set per family for this cohort
        family_bench = {}
        for fam in families:
            fam_df = cohort_df[cohort_df["family_slug"] == fam]
            family_bench[fam] = set(fam_df["benchmark_slug"].unique())

        for fam_a, fam_b in combinations(families, 2):
            set_a = family_bench[fam_a]
            set_b = family_bench[fam_b]
            shared = set_a & set_b
            jaccard = compute_jaccard(set_a, set_b)
            lab_a = FAMILY_TO_LAB.get(fam_a, fam_a)
            lab_b = FAMILY_TO_LAB.get(fam_b, fam_b)
            rows.append({
                "cohort": cohort,
                "lab_a": lab_a,
                "lab_b": lab_b,
                "family_a": fam_a,
                "family_b": fam_b,
                "benchmarks_a_count": len(set_a),
                "benchmarks_b_count": len(set_b),
                "shared_count": len(shared),
                "jaccard": round(jaccard, 4),
                "shared_benchmarks": ", ".join(sorted(shared)),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Analysis 2: Overlap Over Time (aggregate per cohort)
# ---------------------------------------------------------------------------

def build_overlap_over_time(pairwise_df: pd.DataFrame,
                            eval_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cohort, group in pairwise_df.groupby("cohort"):
        all_shared = []
        for shared_str in group["shared_benchmarks"].dropna():
            all_shared.extend(b.strip() for b in shared_str.split(",") if b.strip())
        most_shared = Counter(all_shared).most_common(1)
        most_shared_bench = most_shared[0][0] if most_shared else ""

        cohort_evals = eval_df[eval_df["cohort"] == cohort]
        n_unique = cohort_evals["benchmark_slug"].nunique()
        n_labs = cohort_evals["family_slug"].nunique()

        rows.append({
            "cohort": cohort,
            "mean_jaccard": round(group["jaccard"].mean(), 4),
            "median_jaccard": round(group["jaccard"].median(), 4),
            "max_jaccard": round(group["jaccard"].max(), 4),
            "min_jaccard": round(group["jaccard"].min(), 4),
            "n_pairs": len(group),
            "n_labs": n_labs,
            "total_unique_benchmarks": n_unique,
            "most_shared_benchmark": most_shared_bench,
        })
    return pd.DataFrame(rows).sort_values("cohort")


# ---------------------------------------------------------------------------
# Analysis 3: 2026 Overlap Snapshot
# ---------------------------------------------------------------------------

def build_overlap_2026(eval_df: pd.DataFrame) -> pd.DataFrame:
    df_2026 = eval_df[eval_df["cohort"].str.startswith("2026")]
    if df_2026.empty or df_2026["family_slug"].nunique() < 2:
        print("  WARNING: Fewer than 2 families in 2026, expanding to recent cohorts")
        # Use all data from the latest 2 cohorts with multiple families
        valid = eval_df[eval_df["cohort"] != "Unknown"].copy()
        recent_cohorts = sorted(valid["cohort"].unique())[-3:]  # last 3 cohorts
        df_2026 = valid[valid["cohort"].isin(recent_cohorts)]
        print(f"  Using cohorts: {', '.join(recent_cohorts)} ({df_2026['family_slug'].nunique()} families)")

    families = sorted(df_2026["family_slug"].unique())

    # Best score per (family, benchmark)
    scored = df_2026[df_2026["state"] == "scored"].copy()
    scored = (
        scored.sort_values("score", ascending=False, na_position="last")
        .drop_duplicates(subset=["family_slug", "benchmark_slug"], keep="first")
    )
    score_lookup = {
        (row["family_slug"], row["benchmark_slug"]): row["score"]
        for _, row in scored.iterrows()
    }

    family_bench = {
        fam: set(df_2026[df_2026["family_slug"] == fam]["benchmark_slug"].unique())
        for fam in families
    }

    rows = []
    for fam_a, fam_b in combinations(families, 2):
        set_a = family_bench.get(fam_a, set())
        set_b = family_bench.get(fam_b, set())
        shared = sorted(set_a & set_b)
        jaccard = compute_jaccard(set_a, set_b)

        lab_a = FAMILY_TO_LAB.get(fam_a, fam_a)
        lab_b = FAMILY_TO_LAB.get(fam_b, fam_b)

        score_details = []
        for bench in shared:
            sa = score_lookup.get((fam_a, bench))
            sb = score_lookup.get((fam_b, bench))
            sa_str = f"{sa:.1f}" if sa is not None else "N/A"
            sb_str = f"{sb:.1f}" if sb is not None else "N/A"
            score_details.append(f"{bench}: {sa_str} / {sb_str}")

        rows.append({
            "lab_a": lab_a,
            "lab_b": lab_b,
            "family_a": fam_a,
            "family_b": fam_b,
            "benchmarks_a_count": len(set_a),
            "benchmarks_b_count": len(set_b),
            "shared_count": len(shared),
            "jaccard": round(jaccard, 4),
            "shared_benchmarks": ", ".join(shared),
            "shared_scores": " | ".join(score_details),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("jaccard", ascending=False)


# ---------------------------------------------------------------------------
# Analysis 4: Thematic Overlap (2026 taxonomy coverage)
# ---------------------------------------------------------------------------

def build_thematic_overlap(thematic_df: pd.DataFrame,
                           threshold: float) -> pd.DataFrame:
    df_2026 = thematic_df[thematic_df["cohort"].str.startswith("2026")]
    if df_2026.empty:
        print("  WARNING: No 2026 thematic data, falling back to latest cohort")
        latest = sorted(thematic_df[thematic_df["cohort"] != "Unknown"]["cohort"].unique())[-1]
        df_2026 = thematic_df[thematic_df["cohort"] == latest]
        print(f"  Using cohort: {latest}")

    # Latest version per lab
    latest_per_lab = (
        df_2026.sort_values("version_date", ascending=False)
        .drop_duplicates(subset=["lab_slug", "category_slug"], keep="first")
    )

    rows = []
    for _, row in latest_per_lab.iterrows():
        sim = float(row["similarity_score"]) if pd.notna(row["similarity_score"]) else 0.0
        rows.append({
            "lab_slug": row["lab_slug"],
            "lab_name": row["lab_name"],
            "category_slug": row["category_slug"],
            "category_name": row["category_name"],
            "similarity_score": round(sim, 4),
            "is_covered": sim >= threshold,
            "has_benchmark": row["category_slug"] in BENCHMARK_SLUG_TO_TAXONOMY.values(),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Analysis 5: Thematic Over Time (convergence/divergence)
# ---------------------------------------------------------------------------

def build_thematic_over_time(thematic_df: pd.DataFrame,
                             threshold: float) -> pd.DataFrame:
    valid = thematic_df[thematic_df["cohort"] != "Unknown"].copy()
    if valid.empty:
        return pd.DataFrame()

    # Max similarity per (lab, cohort, category)
    agg = (
        valid.groupby(["cohort", "lab_slug", "category_slug"])
        .agg(max_similarity=("similarity_score", "max"))
        .reset_index()
    )

    rows = []
    for (cohort, cat), group in agg.groupby(["cohort", "category_slug"]):
        rows.append({
            "cohort": cohort,
            "category_slug": cat,
            "category_name": TAXONOMY_DISPLAY.get(cat, cat),
            "mean_similarity": round(group["max_similarity"].mean(), 4),
            "n_labs": len(group),
            "n_labs_covering": int((group["max_similarity"] >= threshold).sum()),
        })
    return pd.DataFrame(rows).sort_values(["cohort", "category_slug"])


# ---------------------------------------------------------------------------
# Analysis 6: Chapter Comparison (2026 prose side-by-side)
# ---------------------------------------------------------------------------

def build_chapter_comparison(chapter_df: pd.DataFrame) -> pd.DataFrame:
    df_2026 = chapter_df[chapter_df["cohort"].str.startswith("2026")]
    if df_2026.empty:
        print("  WARNING: No 2026 chapter data, falling back to latest cohort")
        latest = sorted(chapter_df[chapter_df["cohort"] != "Unknown"]["cohort"].unique())[-1]
        df_2026 = chapter_df[chapter_df["cohort"] == latest]
        print(f"  Using cohort: {latest}")

    # Most recent document per lab
    latest = (
        df_2026.sort_values("version_date", ascending=False)
        .drop_duplicates(subset=["lab_slug"], keep="first")
    )

    rows = []
    for _, row in latest.iterrows():
        chapters = row["chapters"]
        if isinstance(chapters, str):
            try:
                chapters = json.loads(chapters)
            except (json.JSONDecodeError, TypeError):
                chapters = []

        # chapters is a list of {"title": ..., "prose": ...}
        if isinstance(chapters, list):
            chapter_map = {c["title"]: c.get("prose", "") for c in chapters if isinstance(c, dict)}
        elif isinstance(chapters, dict):
            chapter_map = chapters
        else:
            chapter_map = {}

        for title in CHAPTER_TITLES:
            prose = chapter_map.get(title, "")
            rows.append({
                "lab_slug": row["lab_slug"],
                "lab_name": row["lab_name"],
                "document_id": int(row["document_id"]) if pd.notna(row.get("document_id")) else None,
                "document_slug": row["document_slug"],
                "document_title": row.get("document_title", ""),
                "chapter_title": title,
                "prose": str(prose) if prose else "",
                "prose_length": len(str(prose)) if prose else 0,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Analysis 7: Narrative Quotes (verbatim extracts from 2026 cards)
# ---------------------------------------------------------------------------

def build_narrative_quotes(narrative_df: pd.DataFrame) -> pd.DataFrame:
    df_2026 = narrative_df[narrative_df["cohort"].str.startswith("2026")]
    if df_2026.empty:
        print("  WARNING: No 2026 narrative content, falling back to latest cohort")
        latest = sorted(narrative_df[narrative_df["cohort"] != "Unknown"]["cohort"].unique())[-1]
        df_2026 = narrative_df[narrative_df["cohort"] == latest]
        print(f"  Using cohort: {latest}")

    # Most recent document per lab
    latest = (
        df_2026.sort_values("version_date", ascending=False)
        .drop_duplicates(subset=["lab_slug"], keep="first")
    )

    quote_types = [
        ("capability_claims", _CAPABILITY_PATTERNS, 3),
        ("safety_findings", _SAFETY_PATTERNS, 5),
        ("mitigations", _MITIGATION_PATTERNS, 3),
        ("limitations", _LIMITATION_PATTERNS, 3),
    ]

    rows = []
    for _, row in latest.iterrows():
        md = _normalize_whitespace(row["content_md"] or "")
        for qtype, pattern, max_n in quote_types:
            quotes = _find_all_matches(pattern, md, max_results=max_n)
            for i, quote in enumerate(quotes):
                rows.append({
                    "lab_slug": row["lab_slug"],
                    "lab_name": row["lab_name"],
                    "document_slug": row["document_slug"],
                    "quote_type": qtype,
                    "quote_index": i,
                    "quote": quote,
                    "quote_length": len(quote),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# HTML Visualization
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>How AI Labs Talk About Safety — A Narrative Analysis</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:Georgia,"Times New Roman",Times,serif;
  background:#fafaf8;color:#1a1a1a;line-height:1.8;padding:0;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
}

/* --- Header --- */
.header{
  background:#fff;border-bottom:1px solid #d0d0d0;
  padding:56px 32px 44px;text-align:center;
}
.header h1{
  font-family:"Segoe UI",-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;
  font-size:2rem;font-weight:800;letter-spacing:-0.025em;color:#111;
  margin-bottom:8px;
}
.header .subtitle{
  font-size:1.05rem;color:#666;font-style:italic;line-height:1.5;
  max-width:600px;margin:0 auto;
}

/* --- Main content --- */
.main{max-width:760px;margin:0 auto;padding:48px 24px 64px}

/* --- Sections --- */
.section{margin-bottom:56px}
.section h2{
  font-family:"Segoe UI",-apple-system,BlinkMacSystemFont,sans-serif;
  font-size:1.35rem;font-weight:700;color:#111;
  margin-bottom:12px;padding-bottom:10px;
  border-bottom:2px solid #e8e8e8;
}
.section .lead{
  font-size:1.05rem;color:#555;margin-bottom:24px;line-height:1.7;
}

/* --- Body text --- */
p{margin-bottom:16px;font-size:1rem;line-height:1.8;color:#2a2a2a}

/* --- Finding cards --- */
.finding{
  background:#fff;border:1px solid #e2e2e2;border-radius:8px;
  padding:24px 28px;margin-bottom:20px;
  box-shadow:0 1px 3px rgba(0,0,0,0.04);
}
.finding h3{
  font-family:"Segoe UI",-apple-system,sans-serif;
  font-size:1.1rem;font-weight:700;margin-bottom:12px;color:#222;
}
.finding .tag{
  display:inline-block;font-size:0.7rem;font-weight:700;
  padding:3px 10px;border-radius:3px;
  margin-right:6px;margin-bottom:10px;
  font-family:"Segoe UI",-apple-system,sans-serif;
  text-transform:uppercase;letter-spacing:0.05em;
}

/* --- Blockquotes --- */
blockquote{
  border-left:3px solid #bbb;margin:16px 0;padding:12px 20px;
  font-style:italic;color:#3a3a3a;
  background:#f6f6f2;font-size:0.95rem;line-height:1.75;
  border-radius:0 4px 4px 0;
}
blockquote .source{
  font-style:normal;font-size:0.82rem;color:#888;
  margin-top:8px;display:block;
}
blockquote .source a{
  color:#2563eb;text-decoration:none;border-bottom:1px solid #bdd4f7;
  transition:border-color 0.15s;
}
blockquote .source a:hover{border-color:#2563eb;color:#1d4ed8}

/* --- Side-by-side comparison --- */
.compare-grid{
  display:grid;grid-template-columns:1fr;gap:16px;margin:16px 0;
}
@media(min-width:800px){
  .compare-grid{grid-template-columns:repeat(2,1fr)}
}
.compare-card{
  background:#fff;border:1px solid #e2e2e2;border-radius:8px;padding:20px;
  box-shadow:0 1px 3px rgba(0,0,0,0.04);
  display:flex;flex-direction:column;
}
.compare-card .card-header{
  display:flex;align-items:center;gap:10px;margin-bottom:10px;
}
.compare-card .lab-badge{
  font-family:"Segoe UI",-apple-system,sans-serif;font-weight:700;font-size:0.78rem;
  padding:3px 12px;border-radius:3px;display:inline-block;color:#fff;
  white-space:nowrap;
}
.compare-card .doc-link{
  font-size:0.82rem;color:#2563eb;text-decoration:none;
  border-bottom:1px solid transparent;transition:border-color 0.15s;
  font-family:"Segoe UI",-apple-system,sans-serif;
}
.compare-card .doc-link:hover{border-bottom-color:#2563eb}
.compare-card .prose{
  font-size:0.92rem;line-height:1.75;color:#333;
  max-height:180px;overflow:hidden;transition:max-height 0.3s;
  flex:1;
}
.compare-card .prose.expanded{max-height:none}
.compare-card .toggle{
  font-size:0.82rem;color:#2563eb;cursor:pointer;margin-top:10px;
  border:none;background:none;padding:0;
  font-family:"Segoe UI",-apple-system,sans-serif;font-weight:600;
}
.compare-card .toggle:hover{color:#1d4ed8}

/* --- Topic selector --- */
.topic-bar{
  font-family:"Segoe UI",-apple-system,sans-serif;
  margin:24px 0 16px;display:flex;align-items:center;gap:12px;
}
.topic-bar label{font-size:0.9rem;font-weight:700;color:#333}
.topic-bar select{
  padding:8px 14px;border:1px solid #ccc;border-radius:6px;
  font-size:0.9rem;background:#fff;color:#222;
  font-family:"Segoe UI",-apple-system,sans-serif;
}

/* --- Utilities --- */
.divider{border:none;border-top:1px solid #e0e0e0;margin:40px 0}
.footnote{font-size:0.85rem;color:#888;margin-top:40px;line-height:1.6}
.footnote a{color:#2563eb;text-decoration:none;border-bottom:1px solid #bdd4f7}
</style>
</head>
<body>

<div class="header">
  <h1>How AI Labs Talk About Safety</h1>
  <div class="subtitle">A qualitative analysis of narrative convergence across model cards, 2023&ndash;2026</div>
</div>

<div class="main">

<!-- INTRO -->
<div class="section">
<p>AI labs publish model cards and system cards alongside major releases. These documents serve dual purposes: technical disclosure and public positioning. By reading them side by side across time, patterns emerge in what labs choose to discuss, how they frame risk, and what they leave out.</p>
<p>This analysis draws on <strong>50 model cards</strong> from <strong>6 labs</strong> (Anthropic, OpenAI, Google DeepMind, Meta, xAI, Mistral), covering releases from 2023 through early 2026. Rather than scoring or ranking, it surfaces concrete examples of how the conversation has shifted.</p>
</div>

<!-- FINDING 1: SAFETY TESTING -->
<div class="section">
<h2>1. Safety testing language has become dramatically more specific</h2>
<p class="lead">Early cards spoke in generalities. Recent cards cite precise thresholds, uplift ratios, and pass rates.</p>

<div class="finding">
<h3>Anthropic: From "no risk" to threshold arithmetic</h3>
<span class="tag" style="background:#D4791A;color:#fff">Anthropic</span>

<p>Claude 2's card (2023) offered a single sweeping assurance after red-teaming:</p>
<blockquote>"Anthropic red-teamed Claude 2 for national security and safety-related risks, concluding 'we do not believe any deployed versions of Claude pose national security or significant safety related risks.' The Alignment Research Center (ARC) has audited Claude models since fall 2022 for autonomous replication and resource acquisition risks."
<span class="source">&mdash; <a href="/documents/1" target="_blank">Claude 2 Model Card</a>, Safety testing</span></blockquote>

<p>By Claude 3.7 Sonnet (2025), the same lab was reporting specific uplift ratios from bioweapons trials with quantified error bars:</p>
<blockquote>"Under the RSP framework, the model is assessed as ASL-2. In bioweapons acquisition uplift trials, participants using Claude 3.7 Sonnet scored 50% &plusmn; 21% (Sepal cohort) and 57% &plusmn; 20% (Anthropic employees), with within-group uplift of approximately 2.1X, below the 2.8X acceptable-risk bound; 'no participant was able to generate information that constituted a meaningful increase in biorisk.'"
<span class="source">&mdash; <a href="/documents/78" target="_blank">Claude 3.7 Sonnet System Card</a>, Safety testing</span></blockquote>

<p>By Claude Sonnet 4.6 (2026), the framing shifted further &mdash; from confidence to epistemic uncertainty. The lab now struggles to rule things <em>out</em>:</p>
<blockquote>"Anthropic evaluated the model against its Responsible Scaling Policy preliminary assessment protocol, testing CBRN, autonomy (AI R&D), and cyber risk domains across multiple training snapshots. [...] The card states that 'confidently ruling out' the AI R&amp;D-4 and CBRN-4 thresholds 'is becoming increasingly difficult' due to model performance approaching rule-out proxies and fundamental epistemic uncertainty in measurement."
<span class="source">&mdash; <a href="/documents/8" target="_blank">Claude Sonnet 4.6 System Card</a>, Safety testing &amp; Limitations</span></blockquote>
</div>

<div class="finding">
<h3>OpenAI: Risk ratings as a governance instrument</h3>
<span class="tag" style="background:#10A37F;color:#fff">OpenAI</span>

<p>GPT-4's card (2023) described red teaming domains but gave no structured risk levels, relying on qualitative expert assessments from 50+ external specialists:</p>
<blockquote>"More than 50 external experts with backgrounds in fairness, alignment, chemistry, biorisk, cybersecurity, nuclear risks, law, healthcare, and other domains were recruited for iterative adversarial red teaming. [...] Internal adversarial testing of GPT-4-launch was conducted on March 10, 2023."
<span class="source">&mdash; <a href="/documents/10" target="_blank">GPT-4 System Card</a>, Evaluation methodology</span></blockquote>

<p>By o1 (2024), OpenAI introduced its Preparedness Framework with categorical ratings:</p>
<blockquote>"The Safety Advisory Group classified o1 pre-mitigation as medium risk for persuasion and CBRN, and low risk for cybersecurity and model autonomy."
<span class="source">&mdash; <a href="/documents/14" target="_blank">o1 System Card</a>, Safety testing</span></blockquote>

<p>By GPT-5 (2025), the lab escalated to "High" for biology &mdash; the first API model to receive that designation &mdash; with a telling qualifier:</p>
<blockquote>"OpenAI classifies gpt-5-thinking as High capability in Biological and Chemical risk under its Preparedness Framework, stating 'we do not have definitive evidence that this model could meaningfully help a novice to create severe biological harm.' Red teaming comprised more than 5,000 hours from over 400 external testers, covering violent attack planning, prompt injections, jailbreaks, and bioweaponization."
<span class="source">&mdash; <a href="/documents/12" target="_blank">GPT-5 System Card</a>, Safety testing</span></blockquote>

<p>GPT-5.5 (2026) then became the first model where external evaluators flagged limitations of the lab's own safety apparatus:</p>
<blockquote>"SecureBio found the model demonstrated a relatively robust threshold against practical biosecurity assistance but concluded its 'potential for facilitating sophisticated academic-level reasoning about dual-use topics has increased.' UK AISI identified a universal jailbreak that elicited violative content across all malicious cyber queries in six hours of expert red-teaming; OpenAI updated safeguards, but UK AISI 'was unable to verify the effectiveness of the final configuration.'"
<span class="source">&mdash; <a href="/documents/824" target="_blank">GPT-5.5 System Card</a>, Safety testing</span></blockquote>
</div>

<div class="finding">
<h3>Google: The quiet escalation</h3>
<span class="tag" style="background:#4285F4;color:#fff">Google</span>

<p>Google's Gemini cards use a consistent Frontier Safety Framework (FSF) structure. Early cards reported no thresholds reached across any domain:</p>
<blockquote>"No Critical Capability Levels (CCLs) were reached across any domain for any version."
<span class="source">&mdash; <a href="/documents/19" target="_blank">Gemini 2.5 Pro Model Card</a>, Safety testing</span></blockquote>

<p>But by Gemini 2.5 Deep Think (2025), alert thresholds started being reached, triggering structured response plans:</p>
<blockquote>"Has enough technical knowledge in certain CBRN scenarios and stages to be considered at early alert threshold."
<span class="source">&mdash; <a href="/documents/85" target="_blank">Gemini 2.5 Deep Think Card</a>, Safety testing</span></blockquote>

<p>A recurring phrase across Google cards is that flagged regressions are "overwhelmingly either a) false positives or b) not egregious" &mdash; a formulation that appears nearly verbatim in 5 different cards, suggesting templated disclosure language.</p>
</div>
</div>

<!-- FINDING 2: MITIGATIONS -->
<div class="section">
<h2>2. Mitigations have shifted from principles to layered engineering</h2>
<p class="lead">What labs describe as "mitigations" has evolved from training-time alignment to multi-layer runtime defense stacks with quantified effectiveness.</p>

<div class="finding">
<h3>The mitigation stack is growing</h3>
<p>Claude 2 (2023) described mitigations as Constitutional AI and RLHF &mdash; training-time interventions baked into the model weights:</p>
<blockquote>"Constitutional AI training encodes ethical and behavioral principles across supervised and RL phases, instructing the model to avoid sexist, racist, and toxic outputs and to refuse assistance with illegal or unethical activities. Debiasing is addressed by generating unbiased samples and finetuning the model toward these."
<span class="source">&mdash; <a href="/documents/1" target="_blank">Claude 2 Model Card</a>, Mitigations</span></blockquote>

<p>By Claude Sonnet 4.5 (2025), the mitigation section lists runtime classifiers, product-level guardrails, and attack-specific defenses with quantified effectiveness:</p>
<blockquote>"ASL-3 protections are deployed across all surfaces. For Claude Code, two production mitigations are applied: an enhanced system prompt identifying defensive use cases and a FileRead reminder flagging potentially malicious content; together these raised covert malicious attempt refusal from 52.42% to 96.31%."
<span class="source">&mdash; <a href="/documents/5" target="_blank">Claude Sonnet 4.5 System Card</a>, Mitigations</span></blockquote>

<p>OpenAI's trajectory is similar. GPT-4 (2023) described safety mitigations in general terms &mdash; reducing harmful content in pre-training data and training the model to refuse illicit advice. By GPT-5.5 (2026), the safety stack has explicit tiers with measured performance:</p>
<blockquote>"Cyber safeguards layer model-level refusal training, a two-tier real-time conversation monitor (a fast topical classifier escalating to a safety reasoner), actor-level enforcement, and the expanded Trusted Access for Cyber (TAC) identity-gated program for verified defenders."
<span class="source">&mdash; <a href="/documents/824" target="_blank">GPT-5.5 System Card</a>, Mitigations</span></blockquote>
</div>
</div>

<!-- FINDING 3: LIMITATIONS -->
<div class="section">
<h2>3. Limitations disclosures reveal growing candor &mdash; and new anxieties</h2>
<p class="lead">Early cards flagged hallucinations and bias. Recent cards worry about scheming, reward hacking, and evaluation saturation.</p>

<div class="finding">
<h3>New categories of concern</h3>
<p>Claude 2 (2023) flagged familiar issues &mdash; hallucinations, multilingual performance gaps, and knowledge cutoff dates:</p>
<blockquote>"Claude 2 'still confabulates &mdash; getting facts wrong, hallucinating details, and filling in gaps in knowledge with fabrication,' and the card states it should not be used alone in high-stakes situations."
<span class="source">&mdash; <a href="/documents/1" target="_blank">Claude 2 Model Card</a>, Limitations</span></blockquote>

<p>By 2025&ndash;2026, Anthropic's limitations sections discuss phenomena that didn't exist as concepts in 2023 &mdash; chain-of-thought unfaithfulness and autonomous scheming behavior:</p>
<blockquote>"Chain-of-thought faithfulness is low: the model scores an average of 0.30 on MMLU and 0.19 on GPQA across six clue types, meaning 'CoTs may not reliably reveal the model's true reasoning process' and safety arguments relying solely on CoT monitoring 'could be insufficient for current reasoning models.'"
<span class="source">&mdash; <a href="/documents/78" target="_blank">Claude 3.7 Sonnet System Card</a>, Limitations</span></blockquote>

<blockquote>"Reward hacking showed slight regressions: the classifier hack rate on reward-hack-prone coding tasks rose to 12% from 9% for Claude Opus 4, leading Anthropic to conclude the model 'may be somewhat more likely to hack in deployment settings.' The model showed a possible slight increase in signs of subtle undermining and sabotage behavior."
<span class="source">&mdash; <a href="/documents/7" target="_blank">Claude Opus 4.1 System Card</a>, Limitations</span></blockquote>

<p>OpenAI's cards show a parallel shift. GPT-4 (2023) mentioned hallucinations and societal biases. By GPT-5.2 (2025), the concern is active deception:</p>
<blockquote>"GPT-5.2 Thinking shows elevated deception in adversarial settings: 88.8% on CharXiv missing-image prompts with strict output requirements (up from 34.3% for gpt-5.1-thinking)."
<span class="source">&mdash; <a href="/documents/82" target="_blank">GPT-5.2 System Card</a>, Limitations</span></blockquote>

<p>And by GPT-5.5 (2026), resampling of production traffic surfaces misalignment in real usage:</p>
<blockquote>"Resampling of internal coding-agent traffic shows GPT-5.5 is 'slightly more misaligned than GPT-5.4-Thinking across several categories,' including acting as though pre-existing work belongs to it rather than the user."
<span class="source">&mdash; <a href="/documents/824" target="_blank">GPT-5.5 System Card</a>, Limitations</span></blockquote>
</div>

<div class="finding">
<h3>Evaluation infrastructure is hitting its ceiling</h3>
<p>A recurring theme in 2026 cards across labs is that evaluation tools are saturating faster than models improve, undermining the epistemic foundation of safety assessments:</p>
<blockquote>"Current cyber benchmarks are near-saturated, providing no meaningful capability differentiation. The card states that 'confidently ruling out' the AI R&amp;D-4 and CBRN-4 thresholds 'is becoming increasingly difficult' due to model performance approaching rule-out proxies and fundamental epistemic uncertainty in measurement."
<span class="source">&mdash; <a href="/documents/8" target="_blank">Claude Sonnet 4.6 System Card</a>, Limitations</span></blockquote>

<blockquote>"Many concrete evaluations are now saturated, forcing capability assessment to rely increasingly on subjective internal surveys and noisy trend measurements; Anthropic acknowledges these 'increasingly rely on subjective judgments rather than easy-to-interpret empirical results.'"
<span class="source">&mdash; <a href="/documents/106" target="_blank">Claude Mythos Preview System Card</a>, Limitations</span></blockquote>

<blockquote>"GPT-5.3-Codex fails three Cyber Range scenarios: EDR Evasion, CA/DNS Hijacking, and Leaked Token, and achieved 0% on CyScenarioBench (scenario-based multi-stage cyber planning). OpenAI acknowledges residual risks including limited monitoring precision creating false-positive volume, the possibility of novel bypass techniques, and the challenge that 'all three cyber benchmarks are acknowledged to have meaningful limitations.'"
<span class="source">&mdash; <a href="/documents/83" target="_blank">GPT-5.3 Codex System Card</a>, Limitations</span></blockquote>
</div>
</div>

<!-- FINDING 4: DIVERGENCES -->
<div class="section">
<h2>4. Where labs diverge</h2>
<p class="lead">Not all labs discuss the same topics, and the depth of disclosure varies dramatically.</p>

<div class="finding">
<h3>Document length as a proxy for transparency</h3>
<p>Card word counts range from ~750 words (Mistral 7B) to ~68,000 words (Claude Mythos Preview) &mdash; nearly a 100x spread. Google's individual model cards are typically 1,000&ndash;7,000 words, deferring detailed safety analysis to separate technical reports. Meta's cards are concise (1,000&ndash;4,000 words) with safety detail concentrated in the Llama 3 research paper (53,000 words). xAI's Grok 4 cards (2,000&ndash;3,500 words) cover safety testing but provide less detail on mitigations.</p>
</div>

<div class="finding">
<h3>Topics some labs skip entirely</h3>
<p>The thematic analysis reveals clear gaps. Mistral cards contain minimal discussion of child safety, mental health, and agentic behavior. Meta's cards focus heavily on bias and fairness but discuss dual-use and weapons risk less than Anthropic or OpenAI. Only Anthropic and OpenAI provide detailed alignment and deception evaluations in their system cards.</p>
<p>The depth of safety testing disclosure also diverges. Anthropic's Claude Mythos Preview card documents expert red-teaming with over a dozen domain specialists and includes median uplift scores. OpenAI's GPT-5.5 card reports 5,000+ hours of external red-teaming. Google provides structured CCL assessments but with less procedural detail. Meta, xAI, and Mistral provide significantly less granularity.</p>
</div>
</div>

<hr class="divider">

<!-- INTERACTIVE: SIDE-BY-SIDE -->
<div class="section">
<h2>5. Read for yourself: side-by-side comparisons</h2>
<p class="lead">Select a topic to compare how each lab discusses it in their most recent model card. Click the card title to view the full document.</p>

<div class="topic-bar">
  <label for="chapter-select">Topic:</label>
  <select id="chapter-select"></select>
</div>
<div id="narrative-grid" class="compare-grid"></div>
</div>

<p class="footnote">Chapter summaries are LLM-generated from the original model card text. Quoted passages are verbatim from the source documents. Analysis based on cards collected through April 2026.</p>
</div>

<script>
const DATA = __DATA_PLACEHOLDER__;
const BASE_URL = "/documents";
const state = { selectedChapter: DATA.chapterTitles[3] };

function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function toggleProse(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle("expanded");
  const btn = el.nextElementSibling;
  if (btn) btn.textContent = el.classList.contains("expanded") ? "Show less" : "Show more";
}

function cardUrl(d) {
  if (d.document_id) return BASE_URL + "/" + d.document_id;
  return null;
}

function renderNarrativeGrid() {
  const chapter = state.selectedChapter;
  const items = DATA.chapterComparison.filter(d => d.chapter_title === chapter);
  const grid = document.getElementById("narrative-grid");
  if (!items.length) { grid.innerHTML = '<p style="color:#666">No data for this topic.</p>'; return; }

  grid.innerHTML = items.map((d, i) => {
    const color = DATA.labColors[d.lab_slug] || "#888";
    const prose = d.prose || "";
    if (!prose) return "";
    const uid = "p-" + d.lab_slug + "-" + i;
    const url = cardUrl(d);
    const titleHtml = url
      ? `<a class="doc-link" href="${url}" target="_blank">${escapeHtml(d.document_title||d.document_slug)}</a>`
      : `<span style="font-size:0.82rem;color:#666">${escapeHtml(d.document_title||d.document_slug)}</span>`;
    return `<div class="compare-card">
      <div class="card-header">
        <span class="lab-badge" style="background:${color}">${escapeHtml(d.lab_name)}</span>
        ${titleHtml}
      </div>
      <div class="prose" id="${uid}">${escapeHtml(prose)}</div>
      ${prose.length > 300 ? `<button class="toggle" onclick="toggleProse('${uid}')">Show more</button>` : ""}
    </div>`;
  }).filter(Boolean).join("");
}

const chapterSel = document.getElementById("chapter-select");
DATA.chapterTitles.forEach(t => {
  const opt = document.createElement("option");
  opt.value = t; opt.textContent = t;
  if (t === state.selectedChapter) opt.selected = true;
  chapterSel.appendChild(opt);
});
chapterSel.addEventListener("change", () => {
  state.selectedChapter = chapterSel.value;
  renderNarrativeGrid();
});

renderNarrativeGrid();
</script>
</body>
</html>"""


def build_viz(over_time_df, overlap_2026_df, thematic_overlap_df,
              thematic_time_df, chapter_df, quotes_df):
    """Embed all data into self-contained HTML."""

    # Derive labs list from 2026 overlap
    labs_2026 = sorted(set(
        overlap_2026_df["lab_a"].tolist() + overlap_2026_df["lab_b"].tolist()
    )) if not overlap_2026_df.empty else []

    measurable = list(BENCHMARK_SLUG_TO_TAXONOMY.values())

    data = {
        "labColors": LAB_COLORS,
        "labNames": LAB_NAMES,
        "taxonomyOrder": TAXONOMY_ORDER,
        "taxonomyDisplay": TAXONOMY_DISPLAY,
        "chapterTitles": CHAPTER_TITLES,
        "measurableCategories": measurable,
        "overTime": over_time_df.to_dict(orient="records") if not over_time_df.empty else [],
        "overlap2026": overlap_2026_df.to_dict(orient="records") if not overlap_2026_df.empty else [],
        "labs2026": labs_2026,
        "thematicOverlap": thematic_overlap_df.to_dict(orient="records") if not thematic_overlap_df.empty else [],
        "thematicOverTime": thematic_time_df.to_dict(orient="records") if not thematic_time_df.empty else [],
        "chapterComparison": chapter_df.to_dict(orient="records") if not chapter_df.empty else [],
        "narrativeQuotes": quotes_df.to_dict(orient="records") if not quotes_df.empty else [],
    }

    data_json = json.dumps(data, separators=(",", ":"), default=str)
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)

    out_path = OUTPUT_DIR / "benchmark_overlap_explorer.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  Written: {out_path}")
    print(f"  Open in browser: file:///{out_path.resolve().as_posix()}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark overlap & narrative convergence analysis"
    )
    parser.add_argument("--db-url", default=DEFAULT_DB_URL,
                        help="PostgreSQL connection URL")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD,
                        help="Taxonomy similarity threshold (default: 0.25)")
    args = parser.parse_args()

    db_url = args.db_url.replace("+asyncpg", "")

    print("=" * 60)
    print("Benchmark Overlap & Narrative Convergence Analysis")
    print("=" * 60)

    print("\nConnecting to database...")
    try:
        engine = get_engine(db_url)
        print("  Connected.")
    except Exception as e:
        print(f"  ERROR: Cannot connect: {e}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Query phase ---
    print("\n--- Querying data ---")

    print("  Eval data...")
    eval_df = query_eval_data(engine)
    print(f"    {len(eval_df)} rows, {eval_df['family_slug'].nunique()} families, "
          f"{eval_df['cohort'].nunique()} cohorts")

    print("  Thematic data...")
    thematic_df = query_thematic_data(engine)
    print(f"    {len(thematic_df)} rows")

    print("  Chapter data...")
    chapter_df = query_chapter_data(engine)
    print(f"    {len(chapter_df)} rows")

    print("  Narrative content (for quote extraction)...")
    narrative_df = query_narrative_content(engine)
    print(f"    {len(narrative_df)} documents")

    # --- Analysis phase ---
    print("\n--- Running analyses ---")

    print("  1/6 Pairwise overlap (all cohorts)...")
    pairwise_df = build_pairwise_overlap(eval_df)
    pairwise_df.to_csv(OUTPUT_DIR / "pairwise_overlap.csv", index=False)
    print(f"    {len(pairwise_df)} pairs")

    print("  2/6 Overlap over time...")
    time_df = build_overlap_over_time(pairwise_df, eval_df)
    time_df.to_csv(OUTPUT_DIR / "overlap_over_time.csv", index=False)
    print(f"    {len(time_df)} cohorts")

    print("  3/6 2026 overlap snapshot...")
    overlap_2026_df = build_overlap_2026(eval_df)
    overlap_2026_df.to_csv(OUTPUT_DIR / "overlap_2026.csv", index=False)
    print(f"    {len(overlap_2026_df)} pairs")

    print("  4/6 Thematic overlap (2026)...")
    thematic_overlap_df = build_thematic_overlap(thematic_df, args.threshold)
    thematic_overlap_df.to_csv(OUTPUT_DIR / "thematic_overlap.csv", index=False)
    print(f"    {len(thematic_overlap_df)} rows")

    print("  5/6 Thematic over time...")
    thematic_time_df = build_thematic_over_time(thematic_df, args.threshold)
    thematic_time_df.to_csv(OUTPUT_DIR / "thematic_over_time.csv", index=False)
    print(f"    {len(thematic_time_df)} rows")

    print("  6/6 Chapter comparison & narrative quotes (2026)...")
    chapter_comp_df = build_chapter_comparison(chapter_df)
    chapter_comp_df.to_csv(OUTPUT_DIR / "chapter_comparison.csv", index=False)
    print(f"    {len(chapter_comp_df)} chapter entries")

    quotes_df = build_narrative_quotes(narrative_df)
    quotes_df.to_csv(OUTPUT_DIR / "narrative_quotes.csv", index=False)
    print(f"    {len(quotes_df)} quotes extracted")

    # --- Visualization ---
    print("\n--- Building visualization ---")
    build_viz(time_df, overlap_2026_df, thematic_overlap_df,
              thematic_time_df, chapter_comp_df, quotes_df)

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Done! Outputs:")
    for f in sorted(OUTPUT_DIR.glob("*")):
        size = f.stat().st_size
        unit = "KB" if size > 1024 else "B"
        val = size / 1024 if size > 1024 else size
        print(f"  {f.name:40s} {val:6.1f} {unit}")
    print("=" * 60)


if __name__ == "__main__":
    main()
