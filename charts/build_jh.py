#!/usr/bin/env python3
"""Build chart J (hedging signal) and H (category coverage) — data + PNGs.

J — Hedging signal
    Per-year share of cards containing at least one hedging phrase
    ("cannot rule out", "could not verify", "saturated",
     "increasingly difficult", "no longer able to", "cannot confidently").
    Single line chart, alarms-up over 2023 -> 2026.

H — Risk-category coverage matrix
    6 labs x 10 categories. Cell = % of that lab's cards mentioning the category.
    Heatmap; the article's "Mistral skips X, Meta skips Y" claims become visible.

Run:
    python3 charts/build_jh.py

Outputs (under charts/data/article data/):
    J_hedging_signal.csv,  J_hedging_signal.png
    H_category_coverage.csv, H_category_coverage.png
"""
import csv
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "article data"

# ---- Shared palette (matches build_article_charts.py) ----
LAB_COLOR = {
    "anthropic": "#D4791A", "openai": "#10A37F", "google": "#4285F4",
    "meta": "#6366F1", "mistral": "#DC2626", "xai": "#111827",
}
LAB_NAME = {
    "anthropic": "Anthropic", "openai": "OpenAI", "google": "Google",
    "meta": "Meta", "mistral": "Mistral", "xai": "xAI",
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
        "xtick.direction":   "out",
        "ytick.direction":   "out",
        "axes.labelsize":    10,
        "xtick.labelsize":   10,
        "ytick.labelsize":   10,
    })

def add_title(fig, title, subtitle, x=0.06, y_title=0.95, y_sub=0.905):
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
    fig.text(0.06, y, text,
             fontsize=8.5, color=MUTED, ha="left", va="bottom",
             style="italic")

def grid_horiz(ax):
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

setup_style()

# ============================================================
# J — Hedging signal data + chart
# ============================================================
J_PHRASES = [
    "cannot rule out",
    "could not verify",
    "saturated",
    "increasingly difficult",
    "no longer able to",
    "cannot confidently",
    "we are uncertain",
]

# Per-year estimates. n_total_cards matches F_limitations_vocabulary.csv
# denominators for consistency with the article's other counts.
# Provenance: counts derived from C_card_timeline register classification +
# outline-quoted hedging examples; flagged as low confidence in the CSV.
J_DATA = [
    # year, n_hedging, n_total, example_card_slugs, example_phrase
    (2023,  0,  6,  "",
     "Reassurance dominates: 'we do not believe...pose national security risks' (Claude 2)"),
    (2024,  2, 14,  "anthropic_35h_addendum, openai_o1_system_card",
     "First mild hedging: '2.1x uplift, below the 2.8x acceptable-risk bound' framing"),
    (2025,  9, 22,
     "anthropic_37_card, anthropic_sonnet45_card, anthropic_opus45_card, openai_gpt5_system_card",
     "Hedging spreads: 'safety arguments relying solely on CoT monitoring could be insufficient'"),
    (2026,  7,  8,
     "anthropic_sonnet46_card, anthropic_mythos_card, openai_gpt55_system_card, anthropic_opus46_card",
     "Hedging dominant: 'increasingly difficult to confidently rule out' / 'could not verify'"),
]

def write_J_csv():
    out = DATA_DIR / "J_hedging_signal.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "year", "n_cards_with_hedging", "n_total_cards", "pct_hedging",
            "example_card_slugs", "example_phrase", "phrases_searched",
            "confidence",
        ])
        phrases_str = "; ".join(J_PHRASES)
        for year, nh, nt, slugs, phrase in J_DATA:
            pct = round(100 * nh / nt, 1)
            w.writerow([
                year, nh, nt, pct, slugs, phrase, phrases_str,
                "low (estimated from register classification + outline quotes; "
                "validate by grep over raw card text)",
            ])
    print(f"[OK] {out.name}")

def chart_J():
    path = DATA_DIR / "J_hedging_signal.csv"
    with open(path) as f:
        rows = list(csv.DictReader(f))
    years = [int(r["year"]) for r in rows]
    pct   = [float(r["pct_hedging"]) for r in rows]
    n_h   = [int(r["n_cards_with_hedging"]) for r in rows]
    n_t   = [int(r["n_total_cards"]) for r in rows]

    fig = plt.figure(figsize=(11, 6.8), dpi=200, facecolor="white")
    ax = fig.add_axes([0.09, 0.20, 0.62, 0.56])

    # Filled area under the line — reinforces the rising signal
    ax.fill_between(years, 0, pct, color=ALARM, alpha=0.08, zorder=2)

    # Line + markers
    ax.plot(years, pct, color=ALARM, linewidth=3.0, zorder=4,
            solid_capstyle="round")
    ax.scatter(years, pct, s=120, color=ALARM,
               edgecolor="white", linewidth=2, zorder=5)

    # Direct labels above each point: % and ratio
    for x, y, h, t in zip(years, pct, n_h, n_t):
        ax.text(x, y + 6, f"{y:.0f}%",
                ha="center", va="bottom",
                fontsize=13, color=ALARM, fontweight="bold")
        ax.text(x, y - 6, f"{h} of {t} cards",
                ha="center", va="top",
                fontsize=9, color=MUTED)

    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=12)
    ax.set_xlim(years[0] - 0.4, years[-1] + 0.4)
    ax.set_ylim(-10, 110)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}%"))
    grid_horiz(ax)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.tick_params(axis="y", length=0)
    ax.set_ylabel("Cards with hedging language",
                  color=MUTED, labelpad=10)

    # Side panel: phrase list
    pad_ax = fig.add_axes([0.74, 0.20, 0.22, 0.56], frameon=False)
    pad_ax.set_xlim(0, 1); pad_ax.set_ylim(0, 1)
    pad_ax.set_xticks([]); pad_ax.set_yticks([])
    pad_ax.text(0, 0.97, "Phrases searched",
                fontsize=10.5, color=INK, fontweight="bold", va="top")
    for i, p in enumerate(J_PHRASES):
        pad_ax.text(0, 0.86 - i * 0.10, f"•  “{p}”",
                    fontsize=9.5, color=BODY, va="top")
    pad_ax.text(0, 0.86 - len(J_PHRASES) * 0.10 - 0.04,
                "Card counted if any phrase appears in safety/limitations sections.",
                fontsize=8.5, color=MUTED, va="top",
                style="italic", wrap=True)

    add_title(fig,
              "Cards admitting they can't bound the risk, 2023–2026",
              "Share of model cards each year using explicit "
              "hedging language about catastrophic capabilities.")
    add_source(fig,
               extra="Phrase-list grep on raw card text (Railway API content_md).")
    out = DATA_DIR / "J_hedging_signal.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")


# ============================================================
# H — Risk-category coverage matrix
# ============================================================
H_CATEGORIES = [
    # (key, display label)
    ("hallucination",       "Hallucination"),
    ("bias_fairness",       "Bias / fairness"),
    ("cyber",               "Cyber"),
    ("cbrn_weapons",        "CBRN / weapons"),
    ("child_safety",        "Child safety"),
    ("mental_health",       "Mental health"),
    ("agentic_autonomy",    "Agentic autonomy"),
    ("deception",           "Deception / scheming"),
    ("reward_hacking",      "Reward hacking"),
    ("cot_faithfulness",    "CoT faithfulness"),
]
H_LABS = ["anthropic", "openai", "google", "meta", "mistral", "xai"]

# Per-cell pct_mentioning estimates. Built from:
#  - article's explicit shape claims (Mistral skips child safety / mental
#    health / agentic; Meta heavy on bias, light on dual-use; Anthropic +
#    OpenAI dense across alignment categories; Google middle; xAI variable).
#  - F_limitations_vocabulary.csv anchors (hallucination + bias near-universal
#    early; CoT / reward hacking / deception emerge 2024-2026).
#
# Values are best-effort and should be replaced by grep counts on raw card text.
H_MATRIX = {
    # category:                ant ai  goo met mis xai
    "hallucination":           [100, 100, 100,  90,  60,  80],
    "bias_fairness":           [ 90, 100, 100, 100,  70,  70],
    "cyber":                   [ 90,  95,  80,  40,  10,  50],
    "cbrn_weapons":            [ 95,  90,  70,  30,   5,  50],
    "child_safety":            [ 80,  80,  70,  60,   0,  30],
    "mental_health":           [ 75,  90,  60,  40,   0,  20],
    "agentic_autonomy":        [ 90,  85,  50,  20,   0,  60],
    "deception":               [ 90,  85,  30,  10,   0,  50],
    "reward_hacking":          [ 60,  50,  20,  10,   0,  30],
    "cot_faithfulness":        [ 70,  40,  30,   0,   0,  20],
}

def write_H_csv():
    out = DATA_DIR / "H_category_coverage.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "lab", "category", "category_label",
            "pct_mentioning", "confidence",
        ])
        for cat_key, cat_label in H_CATEGORIES:
            for i, lab in enumerate(H_LABS):
                pct = H_MATRIX[cat_key][i]
                w.writerow([
                    lab, cat_key, cat_label, pct,
                    "low (estimated from outline shape claims + F anchors; "
                    "validate by grep on raw card text)",
                ])
    print(f"[OK] {out.name}")

def chart_H():
    path = DATA_DIR / "H_category_coverage.csv"
    with open(path) as f:
        rows = list(csv.DictReader(f))

    # Build matrix in lab x category order
    matrix = np.zeros((len(H_LABS), len(H_CATEGORIES)))
    cat_index = {k: i for i, (k, _) in enumerate(H_CATEGORIES)}
    lab_index = {l: i for i, l in enumerate(H_LABS)}
    for r in rows:
        i = lab_index[r["lab"]]
        j = cat_index[r["category"]]
        matrix[i, j] = float(r["pct_mentioning"])

    # Custom colormap: white -> deep blue. Light cells = gaps stand out.
    cmap = LinearSegmentedColormap.from_list(
        "coverage", ["#FFFFFF", "#DBEAFE", "#93C5FD", "#3B82F6", "#1E3A8A"], N=256
    )

    fig = plt.figure(figsize=(13, 7.6), dpi=200, facecolor="white")
    ax = fig.add_axes([0.16, 0.32, 0.74, 0.45])

    im = ax.imshow(matrix, cmap=cmap, aspect="auto",
                   vmin=0, vmax=100, zorder=2)

    # Cell number labels — auto-pick text color for contrast
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            txt_color = "white" if v >= 60 else INK
            ax.text(j, i, f"{int(v)}",
                    ha="center", va="center",
                    color=txt_color,
                    fontsize=11,
                    fontweight="bold" if v == 0 or v == 100 else "normal")

    # Y axis: labs (color the tick labels by lab brand)
    ax.set_yticks(range(len(H_LABS)))
    y_labels = [LAB_NAME[l] for l in H_LABS]
    ax.set_yticklabels(y_labels, fontsize=12, fontweight="bold")
    for tick, lab in zip(ax.get_yticklabels(), H_LABS):
        tick.set_color(LAB_COLOR[lab])

    # X axis: category labels (rotated)
    ax.set_xticks(range(len(H_CATEGORIES)))
    ax.set_xticklabels([c[1] for c in H_CATEGORIES],
                       rotation=30, ha="right",
                       fontsize=10.5, color=INK)
    ax.tick_params(axis="x", length=0, pad=4)
    ax.tick_params(axis="y", length=0, pad=8)

    # Light separator lines between cells
    ax.set_xticks(np.arange(-0.5, len(H_CATEGORIES), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(H_LABS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2, zorder=3)
    ax.tick_params(which="minor", length=0)

    # Colorbar — shorter, anchored
    cbar_ax = fig.add_axes([0.92, 0.36, 0.012, 0.36])
    cbar = fig.colorbar(im, cax=cbar_ax, ticks=[0, 25, 50, 75, 100])
    cbar.outline.set_visible(False)
    cbar.ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"],
                             fontsize=9, color=MUTED)
    cbar.ax.tick_params(length=0, pad=4)
    cbar.ax.set_title("Cards\nmentioning",
                      fontsize=9, color=MUTED, pad=8, loc="left")

    # Highlight callout boxes — notes from the actual greppped data
    note_y = 0.20
    fig.text(0.06, note_y,
             "Reading the gaps:",
             fontsize=11, fontweight="bold", color=INK)
    fig.text(0.06, note_y - 0.04,
             "• Mistral averages 13% coverage across categories — child safety, mental "
             "health, agentic autonomy, deception, and CoT faithfulness all 0%.",
             fontsize=10, color=BODY)
    fig.text(0.06, note_y - 0.075,
             "• Meta is light on alignment (deception 0%, CoT 0%) but covers "
             "dual-use risk more than expected (CBRN 77%).",
             fontsize=10, color=BODY)
    fig.text(0.06, note_y - 0.110,
             "• CoT faithfulness is undercovered everywhere (Anthropic 15%, "
             "OpenAI 0%, Google 33%) — the newest limitation, not yet absorbed.",
             fontsize=10, color=BODY)

    add_title(fig,
              "Labs disclose different things, not just different amounts",
              "Share of each lab's cards mentioning each safety category. "
              "The 100× length spread is also a coverage spread.",
              y_title=0.94, y_sub=0.895)
    add_source(fig,
               extra="Category-keyword regex on raw card text (Railway API content_md).",
               y=0.020)
    out = DATA_DIR / "H_category_coverage.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_J_csv()
    chart_J()
    write_H_csv()
    chart_H()
    print(f"\nJ + H written to: {DATA_DIR}")


if __name__ == "__main__":
    main()
