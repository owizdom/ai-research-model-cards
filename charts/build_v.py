#!/usr/bin/env python3
"""Build chart V — risk-level escalation across labs (small multiples).

V — Three panels, one per published framework:
    Anthropic ASL · OpenAI Preparedness · Google FSF (CCLs)

Each panel uses its own internal scale (no cross-framework normalization).
Reader sees three independently-rising lines and recognizes the universal
"the dial is turning up" pattern. Meta / Mistral / xAI noted as absent.

Run:
    python3 charts/build_v.py
"""
import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "article data"

LAB_COLOR = {
    "anthropic": "#D4791A", "openai": "#10A37F", "google": "#4285F4",
}
INK   = "#111827"
BODY  = "#374151"
MUTED = "#6B7280"
GRID  = "#E5E7EB"
ALARM = "#DC2626"

SOURCE_BASE = ("Source: 50 model cards from 6 frontier labs · "
               "snapshot 2026-04-28")

def setup_style():
    plt.rcParams.update({
        "font.family":       "sans-serif",
        "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.spines.left":  False,
        "axes.spines.bottom": False,
        "axes.edgecolor":    GRID,
        "axes.labelcolor":   MUTED,
        "axes.titlecolor":   INK,
        "xtick.color":       MUTED,
        "ytick.color":       MUTED,
    })

def add_title(fig, title, subtitle, x=0.05, y_title=0.95, y_sub=0.905):
    fig.text(x, y_title, title,
             fontsize=18, fontweight="bold", color=INK,
             ha="left", va="top")
    if subtitle:
        fig.text(x, y_sub, subtitle,
                 fontsize=12, color=BODY, ha="left", va="top")

def add_source(fig, extra=None, y=0.025):
    text = SOURCE_BASE
    if extra:
        text = f"{text}  ·  {extra}"
    fig.text(0.05, y, text,
             fontsize=8.5, color=MUTED, ha="left", va="bottom",
             style="italic")

setup_style()

# ============================================================
# V data — risk-level declarations per card per framework.
#
# Levels are numeric on each framework's own scale:
#   0 = pre-framework / no declaration
#   1 = lowest declared level  (ASL-1 / Low / CCL-1)
#   2 = mid-low                (ASL-2 / Medium-low or per-category Low / CCL-2)
#   3 = mid-high               (ASL-3 / High in any category / CCL-3)
#   4 = top                    (ASL-4 / Critical / CCL-4)
#
# Anchors verbatim from outline:
#   - GPT-5 (2025-08): "first High rating in biology"
#   - Sonnet 4.5 (2025-09): ASL-3 deployment
# Other cells are best-effort reads of public framework history.
# ============================================================
V_DATA = [
    # (lab, doc_slug, release_date, framework, level_label, level_num, quote, confidence)

    # ---- Anthropic ASL ----
    ("anthropic", "claude2_card",        "2023-07-11", "ASL", "pre-RSP",  0,
     "RSP not yet published", "med (RSP launched late 2023)"),
    ("anthropic", "anthropic_model_card","2024-03-04", "ASL", "ASL-2",    2,
     "Initial RSP-era card",  "med (estimated)"),
    ("anthropic", "anthropic_35_addendum","2024-06-20", "ASL", "ASL-2",   2,
     "ASL-2 deployment",      "med (estimated)"),
    ("anthropic", "anthropic_35h_addendum","2024-10-22","ASL", "ASL-2",   2,
     "ASL-2 deployment",      "med (estimated)"),
    ("anthropic", "anthropic_37_card",   "2025-02-24", "ASL", "ASL-2",    2,
     "Below ASL-3 thresholds", "high (verbatim from card)"),
    ("anthropic", "anthropic_claude4_card","2025-05-22","ASL","ASL-3",    3,
     "ASL-3 deployment",      "med (article-anchored)"),
    ("anthropic", "anthropic_opus41_card","2025-08-05","ASL", "ASL-3",    3,
     "ASL-3 deployment",      "med (estimated)"),
    ("anthropic", "anthropic_sonnet45_card","2025-09-29","ASL","ASL-3",   3,
     "ASL-3 deployment",      "high (verbatim from outline)"),
    ("anthropic", "anthropic_haiku45_card","2025-10-15","ASL","ASL-3",    3,
     "ASL-3 deployment",      "med (estimated)"),
    ("anthropic", "anthropic_opus45_card","2025-11-24","ASL", "ASL-3",    3,
     "ASL-3 deployment",      "med (estimated)"),
    ("anthropic", "anthropic_sonnet46_card","2026-02-15","ASL","ASL-3",   3,
     "Cannot rule out ASL-4-adjacent capabilities",
     "med (article-anchored hedging)"),
    ("anthropic", "anthropic_opus46_card","2026-03-20","ASL", "ASL-3",    3,
     "ASL-3 deployment",      "med (estimated)"),
    ("anthropic", "anthropic_mythos_card","2026-04-08","ASL","ASL-3",     3,
     "ASL-3+ region; saturation language",
     "low (estimated; check card)"),

    # ---- OpenAI Preparedness ----
    ("openai", "gpt4_system_card",       "2023-03-14", "PF", "pre-PF",    0,
     "Preparedness Framework not yet published", "high"),
    ("openai", "gpt4o_system_card",      "2024-08-08", "PF", "Low",       1,
     "Below medium thresholds across categories",
     "med (estimated)"),
    ("openai", "o1_system_card",         "2024-12-05", "PF", "Medium",    2,
     "Medium in some categories",
     "med (estimated)"),
    ("openai", "o3mini_card",            "2025-02-10", "PF", "Medium",    2,
     "Medium",                "med (estimated)"),
    ("openai", "gpt45_system_card",      "2025-02-27", "PF", "Medium",    2,
     "Medium",                "med (estimated)"),
    ("openai", "o3_system_card",         "2025-04-16", "PF", "Medium",    2,
     "Medium",                "med (estimated)"),
    ("openai", "gpt5_system_card",       "2025-08-07", "PF", "High",      3,
     "First 'High' rating in biology",
     "high (verbatim from outline)"),
    ("openai", "gpt51_system_card",      "2025-11-12", "PF", "High",      3,
     "High in biology",       "med (estimated)"),
    ("openai", "gpt52_system_card",      "2025-12-15", "PF", "High",      3,
     "High; deception elevated",
     "med (article-anchored)"),
    ("openai", "gpt53_codex_card",       "2026-01-20", "PF", "High",      3,
     "High",                  "med (estimated)"),
    ("openai", "gpt55_system_card",      "2026-04-23", "PF", "High",      3,
     "High; UK AISI could not verify final config",
     "high (verbatim from outline)"),

    # ---- Google FSF (CCLs) ----
    ("google", "gemini_report",          "2023-12-06", "FSF", "pre-FSF",  0,
     "FSF not yet published", "high"),
    ("google", "gemini_1_5_report",      "2024-02-15", "FSF", "CCL-1",    1,
     "Early FSF mentions",    "med (estimated)"),
    ("google", "gemini_2_card",          "2024-12-11", "FSF", "CCL-1",    1,
     "CCL framing",           "med (estimated)"),
    ("google", "gemini_25_pro_card",     "2025-03-25", "FSF", "CCL-2",    2,
     "CCL-2 reasoning",       "low (estimated)"),
    ("google", "gemini_25_card",         "2025-04-09", "FSF", "CCL-2",    2,
     "CCL-2 reasoning",       "low (estimated)"),
    ("google", "gemini_25dt_card",       "2025-08-01", "FSF", "CCL-2",    2,
     "CCL-2 reasoning",       "low (estimated)"),
    ("google", "gemini_3_pro_card",      "2025-11-18", "FSF", "CCL-2",    2,
     "CCL-2 reasoning",       "low (estimated)"),
    ("google", "gemini_3_card",          "2025-12-15", "FSF", "CCL-2",    2,
     "CCL-2 reasoning",       "low (estimated)"),
    ("google", "gemini_31_pro_card",     "2026-02-20", "FSF", "CCL-3",    3,
     "CCL-3 region per recent FSF revision",
     "low (estimated)"),
]

LEVEL_LABELS = {
    "ASL": ["pre-RSP", "ASL-1", "ASL-2", "ASL-3", "ASL-4"],
    "PF":  ["pre-PF",  "Low",   "Medium", "High",  "Critical"],
    "FSF": ["pre-FSF", "CCL-1", "CCL-2", "CCL-3", "CCL-4"],
}
PANEL_TITLE = {
    "ASL": "Anthropic — Responsible Scaling Policy",
    "PF":  "OpenAI — Preparedness Framework",
    "FSF": "Google — Frontier Safety Framework",
}
PANEL_LAB = {"ASL": "anthropic", "PF": "openai", "FSF": "google"}

def write_V_csv():
    out = DATA_DIR / "V_risk_level_escalation.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "lab", "document_slug", "release_date", "framework",
            "declared_level", "declared_level_numeric",
            "source_quote", "confidence",
        ])
        for row in V_DATA:
            w.writerow(row)
    print(f"[OK] {out.name}")

def chart_V():
    fig = plt.figure(figsize=(15, 7), dpi=200, facecolor="white")
    # Three side-by-side panels
    panel_w   = 0.265
    panel_gap = 0.04
    panel_y   = 0.20
    panel_h   = 0.50
    left_pad  = 0.07

    frameworks = ["ASL", "PF", "FSF"]

    for i, fw in enumerate(frameworks):
        rows = [r for r in V_DATA if r[3] == fw]
        rows.sort(key=lambda r: datetime.strptime(r[2], "%Y-%m-%d"))
        dates = [datetime.strptime(r[2], "%Y-%m-%d") for r in rows]
        levels = [r[5] for r in rows]
        lab_color = LAB_COLOR[PANEL_LAB[fw]]

        x = left_pad + i * (panel_w + panel_gap)
        ax = fig.add_axes([x, panel_y, panel_w, panel_h])

        # Background shading: pre-framework region (level 0)
        ax.axhspan(-0.4, 0.4, color="#F3F4F6", zorder=1)

        # Connecting line through declared levels (skip pre-framework)
        post_dates  = [d for d, l in zip(dates, levels) if l > 0]
        post_levels = [l for l in levels                 if l > 0]
        if post_dates:
            ax.plot(post_dates, post_levels,
                    color=lab_color, linewidth=2.4, zorder=4,
                    solid_capstyle="round")
        # Markers — pre-framework hollow gray; declared filled in lab color
        for d, l in zip(dates, levels):
            if l == 0:
                ax.scatter([d], [l], s=70, facecolor="white",
                           edgecolor=MUTED, linewidth=1.5, zorder=5)
            else:
                ax.scatter([d], [l], s=110, color=lab_color,
                           edgecolor="white", linewidth=2, zorder=5)

        # Highlight the most recent declared level
        if post_dates:
            last_d, last_l = post_dates[-1], post_levels[-1]
            ax.scatter([last_d], [last_l], s=240, facecolor="none",
                       edgecolor=lab_color, linewidth=2, zorder=6)
            ax.text(last_d, last_l + 0.45,
                    LEVEL_LABELS[fw][last_l],
                    ha="center", va="bottom",
                    fontsize=11, color=lab_color, fontweight="bold")

        ax.set_yticks([0, 1, 2, 3, 4])
        ax.set_yticklabels(LEVEL_LABELS[fw], fontsize=9.5, color=BODY)
        ax.set_ylim(-0.6, 4.6)
        ax.tick_params(axis="y", length=0, pad=4)
        ax.tick_params(axis="x", length=0, pad=6)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.xaxis.grid(False)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        # set x range
        all_dates = [datetime.strptime(r[2], "%Y-%m-%d")
                      for r in V_DATA if r[3] == fw]
        if all_dates:
            xmin = min(all_dates)
            xmax = datetime(2026, 6, 1)
            span = (xmax - xmin).days
            ax.set_xlim(xmin, xmax)

        # Panel title
        ax.set_title(PANEL_TITLE[fw],
                     fontsize=11.5, fontweight="bold",
                     color=lab_color, loc="left", pad=10)

    # Footer note about absent labs
    fig.text(0.07, 0.085,
             "Meta, Mistral, and xAI publish no comparable framework. "
             "All three escalations above use each lab's own scale; "
             "scales are not directly comparable, the direction is.",
             fontsize=10, color=BODY, ha="left", va="top")

    add_title(fig,
              "Every published risk framework's dial is turning up",
              "Each lab grades itself on its own scale. "
              "All three escalate over the same three years.",
              y_title=0.945, y_sub=0.895)
    add_source(fig,
               extra="Levels include best-effort estimates per CSV confidence column.",
               y=0.020)
    out = DATA_DIR / "V_risk_level_escalation.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_V_csv()
    chart_V()
    print(f"\nV written to: {DATA_DIR}")


if __name__ == "__main__":
    main()
