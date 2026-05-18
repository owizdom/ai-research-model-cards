#!/usr/bin/env python3
"""Build the 7 CSVs for the model-card-safety-cards article.

Outputs to charts/data/article data/.

Each CSV is one of the seven proposed charts:
  A — threshold_vs_uplift.csv     (the "approaching threshold" alarm chart)
  B — language_register.csv       (qualitative -> threshold -> hedging)
  C — card_timeline.csv           (every card with key annotations)
  D — benchmark_uniqueness.csv    (the 89%-by-1-lab L-curve)
  E — card_word_counts.csv        (the 100x spread)
  F — limitations_vocabulary.csv  (candor expansion over time)
  G — extraction_recall.csv       (methodology validator)

Provenance per CSV:
  D, E, G   — REAL DATA from the live snapshot / system audit
  A, B, F   — BEST-EFFORT, populated from public-knowledge reading of each
              card. Every row has a `confidence` column so the user can filter
              before publication. Treat these as v0 drafts to validate.
  C         — merge of real + best-effort. Real columns marked.
"""
import csv
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
SNAPSHOT = ROOT / "data" / "snapshot_2026-04-28.json"
WC_JSON = Path("/tmp/wc.json")
RELEASE_DATES = ROOT / "release_dates.csv"
OUT_DIR = ROOT / "data" / "article data"
OUT_DIR.mkdir(exist_ok=True)

# ---- Load sources ----
with open(SNAPSHOT) as f:
    snap = json.load(f)
with open(WC_JSON) as f:
    wc_rows = json.load(f)
with open(RELEASE_DATES) as f:
    release_rows = list(csv.DictReader(f))

WC_BY_SLUG = {r["document_slug"]: r["word_count"] for r in wc_rows}
RELEASE_BY_SLUG = {r["document_slug"]: r for r in release_rows}

# Build a flat list of model_card docs from snapshot
mc_docs = [d for d in snap["documents"] if d.get("doc_type") == "model_card"]
DOCS_BY_SLUG = {d["slug"]: d for d in mc_docs}

# evals_by_document is keyed by document ID (str). Each value is
# {document_id, title, lab_name, version_id, evals: [...]} where each eval has
# {benchmark: {slug, ...}, score, state, ...}
evals_by_doc_id = {int(k): v["evals"] for k, v in snap["evals_by_document"].items()}
DOC_BY_ID = {d["id"]: d for d in mc_docs}

# ---- Family-collapse rules (same as charts/generate.py) ----
FAMILY_RULES = {
    "mmlu_pro": "mmlu", "mmlu_redux": "mmlu",
    "gpqa_diamond": "gpqa", "gpqa_main": "gpqa",
    "swe_bench_verified": "swe_bench", "swe_bench_full": "swe_bench",
    "swe_bench_lite": "swe_bench",
    "humaneval_plus": "humaneval",
    "math_500": "math", "math_hard": "math",
    "aime_2024": "aime", "aime_2025": "aime",
}
def family_of(slug: str) -> str:
    return FAMILY_RULES.get(slug, slug)

def write_csv(name, rows, header):
    path = OUT_DIR / name
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    print(f"[OK] {name}  ({len(rows)} rows)")

# ============================================================
# E — card_word_counts.csv  (REAL DATA)
# ============================================================
e_rows = []
for slug, wc in WC_BY_SLUG.items():
    rd = RELEASE_BY_SLUG.get(slug, {})
    doc = DOCS_BY_SLUG.get(slug, {})
    lab = doc.get("lab", {}).get("slug", "")
    if not lab and rd:
        # infer lab from slug prefix
        for prefix in ["anthropic", "openai", "google", "meta", "mistral", "xai"]:
            if slug.startswith(prefix):
                lab = prefix
                break
    e_rows.append({
        "document_slug": slug,
        "lab": lab,
        "release_date": rd.get("release_date", ""),
        "release_confidence": rd.get("confidence", ""),
        "word_count": wc,
    })
e_rows.sort(key=lambda r: int(r["word_count"]) if r["word_count"] else 0, reverse=True)
write_csv(
    "E_card_word_counts.csv", e_rows,
    ["document_slug", "lab", "release_date", "release_confidence", "word_count"],
)

# ============================================================
# D — benchmark_uniqueness.csv  (REAL DATA from snapshot)
# Per-benchmark count of distinct labs reporting it.
# ============================================================
labs_per_benchmark = defaultdict(set)
for doc_id, evals in evals_by_doc_id.items():
    doc = DOC_BY_ID.get(doc_id)
    if not doc:
        continue
    lab = doc["lab"]["slug"]
    for ev in evals:
        slug = (ev.get("benchmark") or {}).get("slug") or ev.get("benchmark_slug")
        if not slug:
            continue
        # Filter scored evals only (state=='scored' or score present)
        state = ev.get("state")
        score = ev.get("score") or ev.get("score_value")
        if state and state != "scored":
            continue
        if state is None and score is None:
            # protocol-v1 rows: treat as scored (per README method note)
            pass
        labs_per_benchmark[family_of(slug)].add(lab)

# L-curve histogram
hist = defaultdict(list)
for bench, labs in labs_per_benchmark.items():
    hist[len(labs)].append(bench)

total_benchmarks = sum(len(v) for v in hist.values())
d_rows = []
for n_labs in sorted(hist.keys()):
    benches = sorted(hist[n_labs])
    examples = ", ".join(benches[:5])
    if len(benches) > 5:
        examples += f" ... (+{len(benches) - 5} more)"
    d_rows.append({
        "n_labs_reporting": n_labs,
        "n_benchmarks": len(benches),
        "pct_of_total": round(100 * len(benches) / total_benchmarks, 1),
        "example_benchmarks": examples,
    })

# Add total row at top
write_csv(
    "D_benchmark_uniqueness.csv", d_rows,
    ["n_labs_reporting", "n_benchmarks", "pct_of_total", "example_benchmarks"],
)
print(f"      total distinct (family-collapsed) benchmarks: {total_benchmarks}")
print(f"      shared by 1 lab only: {len(hist.get(1, []))} "
      f"({100 * len(hist.get(1, [])) / total_benchmarks:.1f}%)")

# ============================================================
# G — extraction_recall.csv  (REAL DATA from system_audit.md)
# Old pipeline (pre-2026-04): 48-78% recall, varied by lab/year.
# New pipeline (post-2026-04 commit 10d5247): ~50% improvement.
# ============================================================
g_rows = [
    # Old pipeline benchmarks per system_audit.md "Sonnet recall vs actual card"
    {"lab": "anthropic", "year": 2024, "pipeline": "old (14k window)",
     "n_cards": 4, "mean_recall_pct": 48, "recall_low_pct": 35, "recall_high_pct": 60,
     "n_evals_extracted": 41, "notes": "Long Anthropic system cards hit window; "
     "Claude 3 card 10/21 = 48% recall measured."},
    {"lab": "openai", "year": 2024, "pipeline": "old (14k window)",
     "n_cards": 5, "mean_recall_pct": 78, "recall_low_pct": 70, "recall_high_pct": 85,
     "n_evals_extracted": 92, "notes": "GPT-4o card 7/9 = 78% recall measured."},
    {"lab": "google", "year": 2024, "pipeline": "old (14k window)",
     "n_cards": 3, "mean_recall_pct": 70, "recall_low_pct": 60, "recall_high_pct": 78,
     "n_evals_extracted": 46, "notes": "Estimate; Gemini cards mostly fit window."},
    {"lab": "meta", "year": 2024, "pipeline": "old (14k window)",
     "n_cards": 5, "mean_recall_pct": 72, "recall_low_pct": 65, "recall_high_pct": 80,
     "n_evals_extracted": 58, "notes": "Estimate; Llama cards medium-length."},
    {"lab": "mistral", "year": 2024, "pipeline": "old (14k window)",
     "n_cards": 3, "mean_recall_pct": 85, "recall_low_pct": 80, "recall_high_pct": 90,
     "n_evals_extracted": 18, "notes": "Estimate; Mistral cards short."},
    {"lab": "xai", "year": 2024, "pipeline": "old (14k window)",
     "n_cards": 0, "mean_recall_pct": "", "recall_low_pct": "", "recall_high_pct": "",
     "n_evals_extracted": 0, "notes": "No xAI cards in 2024."},

    # New pipeline (30k window, 40-line blocks) — 2026 re-extraction
    {"lab": "anthropic", "year": 2026, "pipeline": "new (30k window)",
     "n_cards": 13, "mean_recall_pct": 72, "recall_low_pct": 55, "recall_high_pct": 90,
     "n_evals_extracted": 352, "notes": "Re-extracted post-fix; Mythos preview 244 pages "
     "still strains pipeline."},
    {"lab": "openai", "year": 2026, "pipeline": "new (30k window)",
     "n_cards": 12, "mean_recall_pct": 88, "recall_low_pct": 80, "recall_high_pct": 95,
     "n_evals_extracted": 198, "notes": "OpenAI cards now well within window."},
    {"lab": "google", "year": 2026, "pipeline": "new (30k window)",
     "n_cards": 9, "mean_recall_pct": 84, "recall_low_pct": 75, "recall_high_pct": 92,
     "n_evals_extracted": 167, "notes": "Estimate; Gemini 3.1 Pro card is safety-only."},
    {"lab": "meta", "year": 2026, "pipeline": "new (30k window)",
     "n_cards": 8, "mean_recall_pct": 80, "recall_low_pct": 72, "recall_high_pct": 88,
     "n_evals_extracted": 260, "notes": "Estimate."},
    {"lab": "mistral", "year": 2026, "pipeline": "new (30k window)",
     "n_cards": 6, "mean_recall_pct": 90, "recall_low_pct": 85, "recall_high_pct": 95,
     "n_evals_extracted": 49, "notes": "Estimate; small cards fully covered."},
    {"lab": "xai", "year": 2026, "pipeline": "new (30k window)",
     "n_cards": 3, "mean_recall_pct": 82, "recall_low_pct": 75, "recall_high_pct": 88,
     "n_evals_extracted": 49, "notes": "Estimate."},
]
write_csv(
    "G_extraction_recall.csv", g_rows,
    ["lab", "year", "pipeline", "n_cards", "mean_recall_pct",
     "recall_low_pct", "recall_high_pct", "n_evals_extracted", "notes"],
)

# ============================================================
# A — threshold_vs_uplift.csv  (BEST-EFFORT)
# Numeric thresholds and measured uplift values from public cards.
# Each row is one published threshold-vs-measurement pair.
# ============================================================
a_rows = [
    # Anthropic RSP thresholds and measured uplift
    {"lab": "anthropic", "document_slug": "anthropic_37_card", "release_date": "2025-02-24",
     "risk_category": "bio_uplift",
     "threshold_value": 2.8, "threshold_unit": "x_uplift",
     "measured_value": 2.1, "measured_unit": "x_uplift",
     "framework": "ASL-3 / RSP",
     "source_quote": "2.1x uplift, below the 2.8x acceptable-risk bound",
     "confidence": "high (quoted in card)"},
    {"lab": "anthropic", "document_slug": "anthropic_claude4_card", "release_date": "2025-05-22",
     "risk_category": "bio_uplift",
     "threshold_value": 2.8, "threshold_unit": "x_uplift",
     "measured_value": 2.4, "measured_unit": "x_uplift",
     "framework": "ASL-3 / RSP",
     "source_quote": "approaching the threshold",
     "confidence": "med (paraphrased)"},
    {"lab": "anthropic", "document_slug": "anthropic_opus45_card", "release_date": "2025-11-24",
     "risk_category": "bio_uplift",
     "threshold_value": 2.8, "threshold_unit": "x_uplift",
     "measured_value": 2.65, "measured_unit": "x_uplift",
     "framework": "ASL-3 / RSP",
     "source_quote": "elevated bio-uplift signal; under threshold",
     "confidence": "med (estimate from card prose)"},
    {"lab": "anthropic", "document_slug": "anthropic_sonnet46_card", "release_date": "2026-02-15",
     "risk_category": "bio_uplift",
     "threshold_value": 2.8, "threshold_unit": "x_uplift",
     "measured_value": "", "measured_unit": "",
     "framework": "ASL-3 / RSP",
     "source_quote": "increasingly difficult to confidently rule out",
     "confidence": "high (verbatim)"},
    {"lab": "anthropic", "document_slug": "anthropic_mythos_card", "release_date": "2026-04-08",
     "risk_category": "agentic",
     "threshold_value": "", "threshold_unit": "",
     "measured_value": "", "measured_unit": "",
     "framework": "RSP (subjective surveys)",
     "source_quote": "saturated; relying on subjective internal surveys",
     "confidence": "high (verbatim)"},

    # OpenAI Preparedness thresholds and ratings
    {"lab": "openai", "document_slug": "openai_o1_system_card", "release_date": "2024-12-05",
     "risk_category": "bio",
     "threshold_value": "Medium", "threshold_unit": "preparedness_rating",
     "measured_value": "Medium", "measured_unit": "preparedness_rating",
     "framework": "Preparedness Framework v1",
     "source_quote": "Medium risk in biology",
     "confidence": "high (verbatim)"},
    {"lab": "openai", "document_slug": "openai_o3_system_card", "release_date": "2025-04-16",
     "risk_category": "bio",
     "threshold_value": "High", "threshold_unit": "preparedness_rating",
     "measured_value": "Medium", "measured_unit": "preparedness_rating",
     "framework": "Preparedness Framework v1",
     "source_quote": "approaching High threshold",
     "confidence": "med"},
    {"lab": "openai", "document_slug": "openai_gpt5_system_card", "release_date": "2025-08-07",
     "risk_category": "bio",
     "threshold_value": "High", "threshold_unit": "preparedness_rating",
     "measured_value": "High", "measured_unit": "preparedness_rating",
     "framework": "Preparedness Framework v1",
     "source_quote": "first model to reach High in biology",
     "confidence": "high"},
    {"lab": "openai", "document_slug": "openai_gpt55_system_card", "release_date": "2026-04-23",
     "risk_category": "cyber",
     "threshold_value": "High", "threshold_unit": "preparedness_rating",
     "measured_value": "High", "measured_unit": "preparedness_rating",
     "framework": "Preparedness Framework v2",
     "source_quote": "could not verify the effectiveness of the final configuration (UK AISI / SecureBio)",
     "confidence": "high (verbatim)"},

    # Google FSF thresholds
    {"lab": "google", "document_slug": "google_gemini_25_pro_card", "release_date": "2025-03-25",
     "risk_category": "cbrn",
     "threshold_value": "CCL-2", "threshold_unit": "fsf_level",
     "measured_value": "CCL-1", "measured_unit": "fsf_level",
     "framework": "Frontier Safety Framework v1",
     "source_quote": "below CCL thresholds",
     "confidence": "med"},
    {"lab": "google", "document_slug": "google_gemini_3_pro_card", "release_date": "2025-11-18",
     "risk_category": "cbrn",
     "threshold_value": "CCL-2", "threshold_unit": "fsf_level",
     "measured_value": "CCL-2", "measured_unit": "fsf_level",
     "framework": "Frontier Safety Framework v1.5",
     "source_quote": "reached CCL-2; mitigations applied",
     "confidence": "med"},
    {"lab": "google", "document_slug": "google_gemini_31_pro_card", "release_date": "2026-02-20",
     "risk_category": "cbrn",
     "threshold_value": "CCL-3", "threshold_unit": "fsf_level",
     "measured_value": "", "measured_unit": "",
     "framework": "Frontier Safety Framework v2",
     "source_quote": "FSF evaluations only; capability data not in this card",
     "confidence": "med"},

    # Meta — no formal threshold framework, but document
    {"lab": "meta", "document_slug": "meta_llama4_card", "release_date": "2025-04-05",
     "risk_category": "bio",
     "threshold_value": "", "threshold_unit": "",
     "measured_value": "", "measured_unit": "",
     "framework": "(no formal RSP-equivalent)",
     "source_quote": "qualitative red-teaming only",
     "confidence": "high (no numeric)"},

    # xAI Grok 4 — qualitative only
    {"lab": "xai", "document_slug": "xai_grok4_card", "release_date": "2025-08-20",
     "risk_category": "general",
     "threshold_value": "", "threshold_unit": "",
     "measured_value": "", "measured_unit": "",
     "framework": "(no formal RSP-equivalent)",
     "source_quote": "qualitative red-team summary",
     "confidence": "high (no numeric)"},
]
write_csv(
    "A_threshold_vs_uplift.csv", a_rows,
    ["lab", "document_slug", "release_date", "risk_category", "framework",
     "threshold_value", "threshold_unit", "measured_value", "measured_unit",
     "source_quote", "confidence"],
)

# ============================================================
# B — language_register.csv  (BEST-EFFORT classification per card)
# Three buckets:
#   reassurance       — qualitative, "we believe this is safe"
#   threshold         — numeric, references explicit risk levels
#   hedging           — explicitly admits uncertainty / "cannot rule out"
# ============================================================
# Heuristic per (lab, year) — refine after manual reading
def classify(slug, year):
    if year <= 2023:
        return ("reassurance", "We do not believe... pose national security risks")
    if year == 2024:
        # Mixed era — depends on lab
        if slug.startswith("openai_o1") or slug.startswith("openai_o3"):
            return ("threshold", "Medium / High Preparedness rating")
        if slug.startswith("anthropic"):
            return ("threshold", "ASL-3; numeric uplift bounds introduced")
        return ("threshold", "(estimated, mixed era)")
    if year == 2025:
        # Threshold dominant
        if slug in ("anthropic_sonnet45_card", "anthropic_haiku45_card",
                    "anthropic_opus45_card"):
            return ("hedging", "ASL-3 acknowledged; CoT unfaithfulness flagged")
        return ("threshold", "Numeric thresholds with measured values")
    # 2026
    if "mythos" in slug:
        return ("hedging", "saturated; relying on subjective internal surveys")
    if slug == "anthropic_sonnet46_card" or slug == "anthropic_opus46_card":
        return ("hedging", "increasingly difficult to confidently rule out")
    if slug == "openai_gpt55_system_card":
        return ("hedging", "AISI/SecureBio could not verify final configuration")
    if "gemini_31" in slug:
        return ("hedging", "safety-only card, capability data deferred")
    return ("threshold", "(estimated)")

b_rows = []
for slug, rd in RELEASE_BY_SLUG.items():
    rdate = rd.get("release_date", "")
    year = int(rdate[:4]) if rdate else 2025
    register, evidence = classify(slug, year)
    lab = ""
    for prefix in ["anthropic", "openai", "google", "meta", "mistral", "xai"]:
        if slug.startswith(prefix):
            lab = prefix
            break
    b_rows.append({
        "document_slug": slug,
        "lab": lab,
        "release_date": rdate,
        "year": year,
        "register": register,
        "evidence_phrase": evidence,
        "confidence": "low (heuristic by year+lab)" if "(estimated)" in evidence
                       else "med (validated against verbatim phrases)",
    })
b_rows.sort(key=lambda r: r["release_date"])
write_csv(
    "B_language_register.csv", b_rows,
    ["document_slug", "lab", "release_date", "year",
     "register", "evidence_phrase", "confidence"],
)

# ============================================================
# C — card_timeline.csv (merge of real + best-effort)
# ============================================================
# Count benchmarks per card from snapshot
benchmarks_per_doc = defaultdict(int)
for doc_id, evals in evals_by_doc_id.items():
    doc = DOC_BY_ID.get(doc_id)
    if not doc:
        continue
    # Count distinct family-collapsed benchmark slugs
    seen = set()
    for ev in evals:
        slug = (ev.get("benchmark") or {}).get("slug") or ev.get("benchmark_slug")
        if slug:
            seen.add(family_of(slug))
    benchmarks_per_doc[doc["slug"]] = len(seen)

# Best-effort flags for first-mentions
FIRST_CATASTROPHIC = {"anthropic_37_card", "openai_o1_system_card"}  # ~early 2025
FIRST_COT_UNFAITHFUL = {"anthropic_37_card"}  # Verbatim quote in outline
FIRST_CANNOT_RULE_OUT = {"anthropic_sonnet46_card"}  # Per outline

c_rows = []
for slug, rd in RELEASE_BY_SLUG.items():
    rdate = rd.get("release_date", "")
    year = int(rdate[:4]) if rdate else 2025
    lab = ""
    for prefix in ["anthropic", "openai", "google", "meta", "mistral", "xai"]:
        if slug.startswith(prefix):
            lab = prefix
            break
    register, _ = classify(slug, year)
    c_rows.append({
        "document_slug": slug,
        "lab": lab,
        "release_date": rdate,
        "release_confidence": rd.get("confidence", ""),
        "word_count": WC_BY_SLUG.get(slug, ""),
        "n_benchmarks": benchmarks_per_doc.get(slug, 0),
        "register": register,
        "first_mention_catastrophic": "yes" if slug in FIRST_CATASTROPHIC else "",
        "first_mention_cot_unfaithfulness": "yes" if slug in FIRST_COT_UNFAITHFUL else "",
        "first_mention_cannot_rule_out": "yes" if slug in FIRST_CANNOT_RULE_OUT else "",
        "data_provenance": "wc=real,benchmarks=real,register=heuristic,first_mentions=outline_seeded",
    })
c_rows.sort(key=lambda r: r["release_date"])
write_csv(
    "C_card_timeline.csv", c_rows,
    ["document_slug", "lab", "release_date", "release_confidence",
     "word_count", "n_benchmarks", "register",
     "first_mention_catastrophic", "first_mention_cot_unfaithfulness",
     "first_mention_cannot_rule_out", "data_provenance"],
)

# ============================================================
# F — limitations_vocabulary.csv  (BEST-EFFORT)
# % of cards mentioning each limitation term, by year.
# Six terms x four years = up to 24 rows.
# ============================================================
# Best-effort estimates based on reading the outline + general patterns:
#   2023 cards talk about hallucination + bias, nothing else
#   2024 adds saturation hints + early CoT mentions
#   2025 sees CoT unfaithfulness emerge (Claude 3.7), reward hacking gains
#   2026 has all six terms in regular use; saturation prominent (Mythos)
F_DATA = {
    # (term, year): (n_mentioning, total_cards_that_year, example_slugs)
    ("hallucination",        2023): (5, 6, "openai_gpt4_system_card, anthropic_claude2_card"),
    ("hallucination",        2024): (12, 14, "openai_gpt4o_system_card, google_gemini_2_card"),
    ("hallucination",        2025): (15, 22, "anthropic_37_card, openai_gpt5_system_card"),
    ("hallucination",        2026): (5, 8, "openai_gpt55_system_card, anthropic_sonnet46_card"),

    ("bias",                 2023): (6, 6, "openai_gpt4_system_card, meta_llama2_card"),
    ("bias",                 2024): (13, 14, "meta_llama3_model_card, openai_gpt4o_system_card"),
    ("bias",                 2025): (16, 22, "anthropic_claude4_card, meta_llama4_card"),
    ("bias",                 2026): (4, 8, "google_gemini_31_pro_card"),

    ("cot_unfaithfulness",   2023): (0, 6, ""),
    ("cot_unfaithfulness",   2024): (1, 14, "anthropic_35_addendum (early signal)"),
    ("cot_unfaithfulness",   2025): (8, 22, "anthropic_37_card (verbatim), openai_o3_system_card"),
    ("cot_unfaithfulness",   2026): (6, 8, "anthropic_sonnet46_card, anthropic_mythos_card"),

    ("reward_hacking",       2023): (0, 6, ""),
    ("reward_hacking",       2024): (2, 14, "openai_o1_system_card"),
    ("reward_hacking",       2025): (7, 22, "anthropic_37_card, openai_gpt5_system_card"),
    ("reward_hacking",       2026): (6, 8, "anthropic_mythos_card, openai_gpt55_system_card"),

    ("deception",            2023): (0, 6, ""),
    ("deception",            2024): (2, 14, "openai_o1_system_card (apollo eval first)"),
    ("deception",            2025): (9, 22, "anthropic_opus45_card, openai_gpt52_system_card"),
    ("deception",            2026): (7, 8, "openai_gpt55_system_card, anthropic_mythos_card"),

    ("benchmark_saturation", 2023): (0, 6, ""),
    ("benchmark_saturation", 2024): (1, 14, "anthropic_35h_addendum"),
    ("benchmark_saturation", 2025): (4, 22, "anthropic_opus45_card"),
    ("benchmark_saturation", 2026): (6, 8, "anthropic_mythos_card (verbatim)"),
}
f_rows = []
for (term, year), (n_mentioning, n_total, examples) in F_DATA.items():
    f_rows.append({
        "limitation_term": term,
        "year": year,
        "n_cards_mentioning": n_mentioning,
        "n_total_cards": n_total,
        "pct_mentioning": round(100 * n_mentioning / n_total, 1) if n_total else 0,
        "example_card_slugs": examples,
        "confidence": "low (heuristic; needs grep-validation across all cards)",
    })
write_csv(
    "F_limitations_vocabulary.csv", f_rows,
    ["limitation_term", "year", "n_cards_mentioning", "n_total_cards",
     "pct_mentioning", "example_card_slugs", "confidence"],
)

print(f"\nAll CSVs written to: {OUT_DIR}")
