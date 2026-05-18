#!/usr/bin/env python3
"""Render the 7 article charts from the article-data CSVs.

Output: PNGs in charts/data/article data/ — one per CSV.

Style: FT / Bloomberg flavour. Generous whitespace, direct labels, restrained
palette, consistent typographic hierarchy. Distinct lab colors that don't
collide (Meta/Google brand colors are too close to each other so we shift
Meta to indigo). Numbers formatted properly. Source lines at bottom.

Run after build_article_data.py:
    python3 charts/build_article_charts.py
"""
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "article data"

# ---- Distinct chart palette (close to brand, made non-collidable) ----
LAB_COLOR = {
    "anthropic": "#D4791A",   # coral
    "openai":    "#10A37F",   # green
    "google":    "#4285F4",   # blue
    "meta":      "#6366F1",   # indigo (shifted from brand to avoid collision with Google)
    "mistral":   "#DC2626",   # red  (shifted from orange to avoid collision with Anthropic)
    "xai":       "#111827",   # near-black
}
LAB_NAME = {
    "anthropic": "Anthropic", "openai": "OpenAI", "google": "Google",
    "meta": "Meta", "mistral": "Mistral", "xai": "xAI",
}

# Three-register palette
REGISTER_COLOR = {
    "reassurance": "#9CA3AF",  # past
    "threshold":   "#3B82F6",  # standard
    "hedging":     "#DC2626",  # alarm
}
REGISTER_LABEL = {
    "reassurance": "Reassurance",
    "threshold":   "Numeric thresholds",
    "hedging":     "Honest hedging",
}

INK   = "#111827"
BODY  = "#374151"
MUTED = "#6B7280"
GRID  = "#E5E7EB"
ALARM = "#DC2626"

SOURCE_BASE = ("Source: 50 model cards from 6 frontier labs · "
               "snapshot 2026-04-28")

# ---- Style helpers ----
def setup_style():
    plt.rcParams.update({
        # Use DejaVu Sans (matplotlib default) — has arrow glyphs and looks clean
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

def grid_vert(ax):
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)

def read_csv_(path):
    with open(path) as f:
        return list(csv.DictReader(f))

setup_style()

# ============================================================
# D — Benchmark uniqueness L-curve  (KEEP ORIGINAL — user approved)
# ============================================================
def chart_D():
    rows = read_csv_(DATA_DIR / "D_benchmark_uniqueness.csv")
    n_labs   = [int(r["n_labs_reporting"]) for r in rows]
    n_bench  = [int(r["n_benchmarks"])     for r in rows]
    pct      = [float(r["pct_of_total"])   for r in rows]

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=200)
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.10, right=0.96)

    colors = ["#DC2626"] + ["#3B82F6"] * (len(n_labs) - 1)
    bars = ax.bar(n_labs, n_bench, color=colors, width=0.7, zorder=3)

    for i, (b, n, p) in enumerate(zip(bars, n_bench, pct)):
        ax.text(b.get_x() + b.get_width() / 2,
                b.get_height() + max(n_bench) * 0.018,
                f"{n}\n({p}%)", ha="center", va="bottom",
                fontsize=10, color=INK, fontweight="bold")

    ax.set_xticks(n_labs)
    ax.set_xticklabels([f"{n} lab{'s' if n != 1 else ''}" for n in n_labs])
    ax.set_xlabel("Number of labs reporting the benchmark", fontsize=10)
    ax.set_ylabel("Distinct benchmarks (family-collapsed)", fontsize=10)
    ax.set_ylim(0, max(n_bench) * 1.18)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    # MMLU annotation
    ax.annotate("MMLU — the only\nbenchmark at 5 labs",
                xy=(5, n_bench[-1]), xytext=(4.0, max(n_bench) * 0.45),
                fontsize=9, color=MUTED,
                arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))

    add_title(fig,
              "89% of frontier benchmarks are reported by only one lab",
              f"Of {sum(n_bench)} distinct family-collapsed benchmarks, "
              f"{n_bench[0]} appear in just one lab's cards. "
              "No benchmark is reported by all 6 labs.")
    add_source(fig)
    out = DATA_DIR / "D_benchmark_uniqueness.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")

# ============================================================
# E — Word count spread (sorted horizontal bars, lab-colored)
# ============================================================
def chart_E():
    rows = read_csv_(DATA_DIR / "E_card_word_counts.csv")
    rows = sorted(rows, key=lambda r: int(r["word_count"]), reverse=True)
    # Friendly label per card (drop slug prefixes)
    def pretty(slug):
        s = slug.replace("anthropic_", "").replace("openai_", "")
        s = s.replace("google_", "").replace("meta_", "")
        s = s.replace("mistral_", "").replace("xai_", "")
        s = s.replace("_card", "").replace("_", " ")
        return s

    labels = [pretty(r["document_slug"]) for r in rows]
    values = [int(r["word_count"]) for r in rows]
    colors = [LAB_COLOR.get(r["lab"], "#888") for r in rows]
    n = len(rows)

    fig = plt.figure(figsize=(14, 18), dpi=200, facecolor="white")
    ax = fig.add_axes([0.22, 0.035, 0.70, 0.86])

    y = np.arange(n)[::-1]  # invert so largest is at top
    ax.barh(y, values, color=colors, height=0.78,
             edgecolor="white", linewidth=0, zorder=3)

    # Direct value labels at end of each bar
    for yi, v in zip(y, values):
        ax.text(v + max(values) * 0.008, yi, f"{v:,}",
                va="center", ha="left",
                fontsize=10, color=INK)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10, color=BODY)
    ax.set_xlim(0, max(values) * 1.13)
    ax.set_xticks([])
    ax.set_ylim(-0.7, n - 0.3)
    ax.tick_params(axis="y", length=0)

    # Lab legend — proper matplotlib legend above the chart
    legend_handles = [mpatches.Patch(color=LAB_COLOR[lab], label=LAB_NAME[lab])
                       for lab in ["anthropic", "openai", "google",
                                    "meta", "mistral", "xai"]]
    ax.legend(handles=legend_handles, loc="lower center",
               bbox_to_anchor=(0.5, 1.005), ncol=6,
               frameon=False, fontsize=11,
               handlelength=1.2, handletextpad=0.6,
               columnspacing=2.0)

    add_title(fig,
              f"Card length spans {max(values)//min(values)}×, "
              f"from {min(values):,} to {max(values):,} words",
              "All 50 cards sorted longest first. Bar color shows lab.",
              x=0.06, y_title=0.975, y_sub=0.948)
    add_source(fig, y=0.010)
    out = DATA_DIR / "E_card_word_counts.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")

# ============================================================
# A — Threshold vs uplift (Anthropic numeric only, with danger zone)
# ============================================================
def chart_A():
    rows = read_csv_(DATA_DIR / "A_threshold_vs_uplift.csv")
    pts = []
    for r in rows:
        if r["lab"] != "anthropic" or r["risk_category"] != "bio_uplift":
            continue
        pts.append({
            "date": datetime.strptime(r["release_date"], "%Y-%m-%d"),
            "thr":  float(r["threshold_value"]) if r["threshold_value"] else 2.8,
            "meas": float(r["measured_value"]) if r["measured_value"] else None,
            "card": r["document_slug"],
            "quote": r["source_quote"],
        })
    pts.sort(key=lambda p: p["date"])

    dates_all = [p["date"] for p in pts]
    m_pts = [p for p in pts if p["meas"] is not None]
    m_dates = [p["date"] for p in m_pts]
    m_vals  = [p["meas"] for p in m_pts]

    fig = plt.figure(figsize=(11, 6.8), dpi=200, facecolor="white")
    ax = fig.add_axes([0.08, 0.16, 0.86, 0.60])

    # Y range
    ymin, ymax = 1.6, 3.2
    ax.set_ylim(ymin, ymax)

    # Danger-zone band: above the most recent measured up to threshold
    # Show the closing gap visually
    # Light red shaded rectangle from (last measured date) to right edge between
    # last-measured value and threshold
    threshold = 2.8
    ax.axhline(threshold, color=ALARM, linewidth=1.6, linestyle="--",
                zorder=3, alpha=0.85)
    # Danger zone above threshold (shaded)
    ax.axhspan(threshold, ymax, color=ALARM, alpha=0.06, zorder=1)

    # Measured line
    ax.plot(m_dates, m_vals,
             color=LAB_COLOR["anthropic"], linewidth=2.6,
             marker="o", markersize=10,
             markerfacecolor="white", markeredgewidth=2.4,
             markeredgecolor=LAB_COLOR["anthropic"], zorder=5)

    # Value labels above each measured point
    for d, m in zip(m_dates, m_vals):
        ax.text(d, m + 0.07, f"{m:.1f}×",
                ha="center", va="bottom",
                fontsize=11, color=LAB_COLOR["anthropic"],
                fontweight="bold")
        # Card-name labels below
        card = next(p["card"] for p in m_pts if p["date"] == d)
        short = card.replace("anthropic_", "").replace("_card", "").replace("_", " ")
        ax.text(d, m - 0.08, short, ha="center", va="top",
                fontsize=8.5, color=MUTED)

    # Direct-label the threshold line (right edge)
    last_x = max(dates_all)
    ax.text(last_x, threshold + 0.04,
            "Acceptable-risk bound (2.8×)",
            ha="right", va="bottom",
            fontsize=10, color=ALARM, fontweight="bold")

    # Direct-label the measured line (left edge)
    ax.text(m_dates[0], m_vals[0] - 0.30, "Measured bio-uplift",
            ha="left", va="top",
            fontsize=10, color=LAB_COLOR["anthropic"], fontweight="bold")

    # Hedging callout for the post-measured card (Sonnet 4.6, no number)
    no_meas = [p for p in pts if p["meas"] is None]
    if no_meas:
        p = no_meas[-1]
        ax.annotate('"increasingly difficult\nto confidently rule out"',
                     xy=(p["date"], threshold - 0.05),
                     xytext=(p["date"], 2.35),
                     ha="center", va="top",
                     fontsize=9.5, color=BODY, style="italic",
                     bbox=dict(boxstyle="round,pad=0.4",
                                fc="#FEF2F2", ec="#FECACA", lw=0.8),
                     arrowprops=dict(arrowstyle="-", color="#FECACA",
                                      linewidth=0.8))

    # Y-axis: tighter ticks
    ax.set_yticks([1.6, 2.0, 2.4, 2.8, 3.2])
    ax.set_yticklabels([f"{v:.1f}×" for v in [1.6, 2.0, 2.4, 2.8, 3.2]])
    ax.set_xlim(min(dates_all) - (max(dates_all) - min(dates_all)) * 0.08,
                 max(dates_all) + (max(dates_all) - min(dates_all)) * 0.05)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    grid_horiz(ax)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.tick_params(axis="y", length=0)
    ax.set_ylabel("Bio-uplift multiplier", color=MUTED, labelpad=10)

    add_title(fig,
              "Anthropic's measured bio-uplift is rising toward the safety threshold",
              "Each Anthropic system card publishes a measured uplift number "
              "against an acceptable-risk bound. The gap is shrinking.")
    add_source(fig,
                extra="Best-effort extraction; per-row confidence in CSV.")
    out = DATA_DIR / "A_threshold_vs_uplift.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")

# ============================================================
# B — Language register stacked columns
# ============================================================
def chart_B():
    rows = read_csv_(DATA_DIR / "B_language_register.csv")
    pivot = defaultdict(lambda: defaultdict(int))
    for r in rows:
        pivot[int(r["year"])][r["register"]] += 1
    years = sorted(pivot.keys())
    registers = ["reassurance", "threshold", "hedging"]

    fig = plt.figure(figsize=(11, 6.8), dpi=200, facecolor="white")
    ax = fig.add_axes([0.08, 0.18, 0.86, 0.58])

    bar_w = 0.62
    bottom = np.zeros(len(years))
    for reg in registers:
        vals = np.array([pivot[y][reg] for y in years])
        ax.bar(years, vals, bottom=bottom,
                color=REGISTER_COLOR[reg],
                width=bar_w, edgecolor="white", linewidth=1.2, zorder=3)
        for x, v, b in zip(years, vals, bottom):
            if v > 0:
                ax.text(x, b + v / 2, str(v),
                        ha="center", va="center",
                        color="white", fontsize=12, fontweight="bold")
        bottom += vals

    # Year totals above bars
    for x, total in zip(years, bottom):
        ax.text(x, total + 0.6, f"n={int(total)}",
                ha="center", va="bottom", fontsize=9.5, color=MUTED)

    ax.set_xticks(years)
    ax.set_xticklabels(years, fontsize=12)
    ax.set_yticks([])
    ax.set_ylim(0, max(bottom) * 1.18)
    grid_horiz(ax)
    ax.tick_params(axis="x", length=0, pad=6)

    # Custom legend with proper colors
    legend_handles = [mpatches.Patch(color=REGISTER_COLOR[r],
                                       label=REGISTER_LABEL[r])
                       for r in registers]
    ax.legend(handles=legend_handles, loc="upper left",
               frameon=False, fontsize=11, ncol=3,
               bbox_to_anchor=(0.0, 1.05))

    add_title(fig,
              "Safety language has shifted from reassurance to thresholds to hedging",
              "Each card classified by its dominant register. "
              "2026 includes only cards published through April.")
    add_source(fig,
                extra="Phrase-list classifier on raw card text (Railway API content_md).")
    out = DATA_DIR / "B_language_register.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")

# ============================================================
# C — 50-card timeline (scatter, lab-colored, breathing room)
# ============================================================
def chart_C():
    rows = read_csv_(DATA_DIR / "C_card_timeline.csv")
    labs_order = ["mistral", "xai", "meta", "google", "openai", "anthropic"]

    fig = plt.figure(figsize=(14, 9), dpi=200, facecolor="white")
    ax = fig.add_axes([0.09, 0.16, 0.78, 0.58])

    annos = []
    for lab_i, lab in enumerate(labs_order):
        lab_rows = [r for r in rows if r["lab"] == lab and r["release_date"]
                    and r["word_count"]]
        dates = [datetime.strptime(r["release_date"], "%Y-%m-%d") for r in lab_rows]
        sizes = [int(r["word_count"]) for r in lab_rows]
        bubble = [max(70, s / 22) for s in sizes]
        ax.scatter(dates, [lab_i] * len(dates), s=bubble,
                    color=LAB_COLOR[lab], alpha=0.78,
                    edgecolor="white", linewidth=1.5, zorder=4)

        for d, r in zip(dates, lab_rows):
            tags = []
            if r.get("first_mention_catastrophic") == "yes":
                tags.append("first 'catastrophic'")
            if r.get("first_mention_cot_unfaithfulness") == "yes":
                tags.append("first 'CoT unfaithful'")
            if r.get("first_mention_cannot_rule_out") == "yes":
                tags.append("first 'cannot rule out'")
            for t in tags:
                annos.append((d, lab_i, t))

    # Stagger annotations to avoid collision: track placed (date, y_offset)
    placed = []
    annos.sort()
    for d, lab_i, t in annos:
        # Try increasing y_offsets until clear of any prior placement nearby
        offsets = [40, 70, 100]
        chosen = offsets[0]
        for off in offsets:
            collision = any(abs((d - pd).days) < 35 and po == off
                            for pd, po in placed)
            if not collision:
                chosen = off
                break
        placed.append((d, chosen))
        ax.annotate(t,
                     xy=(d, lab_i), xytext=(0, chosen),
                     textcoords="offset points",
                     ha="center", fontsize=9, color=INK,
                     bbox=dict(boxstyle="round,pad=0.4",
                                fc="#FFF7ED", ec="#FB923C", lw=0.8),
                     arrowprops=dict(arrowstyle="-", color="#FB923C",
                                      linewidth=0.7))

    ax.set_yticks(range(len(labs_order)))
    ax.set_yticklabels([LAB_NAME[l] for l in labs_order],
                        fontsize=12, color=INK, fontweight="bold")
    ax.set_ylim(-0.7, len(labs_order) - 0.3)
    grid_vert(ax)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.tick_params(axis="x", length=0, pad=4)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    # Bubble size legend — placed cleanly to the right of the chart
    leg_ax = fig.add_axes([0.88, 0.16, 0.10, 0.30], frameon=False)
    leg_ax.set_xlim(0, 1); leg_ax.set_ylim(0, 1)
    leg_ax.set_xticks([]); leg_ax.set_yticks([])
    leg_ax.text(0.05, 0.95, "Card length",
                fontsize=10, color=MUTED, fontweight="bold")
    for i, (sz, label) in enumerate([(750, "750 words"),
                                       (10000, "10,000"),
                                       (50000, "50,000")]):
        y_pos = 0.75 - i * 0.22
        leg_ax.scatter([0.18], [y_pos], s=max(70, sz / 22),
                       color="#9CA3AF", alpha=0.7,
                       edgecolor="white", linewidth=1.2)
        leg_ax.text(0.42, y_pos, label,
                    fontsize=9.5, color=BODY, va="center")

    add_title(fig,
              "50 model cards across 6 labs, 2023 – 2026",
              "Each circle is one card. Size shows word count; color shows lab. "
              "Labels mark first uses of new safety language.",
              y_title=0.94, y_sub=0.895)
    add_source(fig, y=0.030)
    out = DATA_DIR / "C_card_timeline.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")

# ============================================================
# F — Limitations vocabulary over time (multi-line, direct labels)
# ============================================================
def chart_F():
    rows = read_csv_(DATA_DIR / "F_limitations_vocabulary.csv")
    pivot = defaultdict(dict)
    for r in rows:
        pivot[r["limitation_term"]][int(r["year"])] = float(r["pct_mentioning"])
    years = sorted({y for ys in pivot.values() for y in ys})

    term_order = ["hallucination", "bias",
                   "cot_unfaithfulness", "reward_hacking",
                   "deception", "benchmark_saturation"]
    term_label = {
        "hallucination":       "Hallucination",
        "bias":                "Bias",
        "cot_unfaithfulness":  "CoT unfaithfulness",
        "reward_hacking":      "Reward hacking",
        "deception":           "Deception",
        "benchmark_saturation": "Benchmark saturation",
    }
    # Stable terms in muted gray; emerging terms in distinct alarm-ish colors
    term_color = {
        "hallucination":        "#9CA3AF",
        "bias":                 "#6B7280",
        "cot_unfaithfulness":   "#3B82F6",
        "reward_hacking":       "#7C3AED",
        "deception":            "#DC2626",
        "benchmark_saturation": "#D4791A",
    }

    fig = plt.figure(figsize=(12, 6.8), dpi=200, facecolor="white")
    ax = fig.add_axes([0.07, 0.16, 0.65, 0.60])

    # Compute final-year y positions to space labels apart
    final_vals = []
    for term in term_order:
        v = pivot[term].get(years[-1], 0)
        final_vals.append((term, v))
    # Sort by value desc
    sorted_by_val = sorted(final_vals, key=lambda x: -x[1])
    label_y = {}
    last_y = 110
    for term, v in sorted_by_val:
        # Anchor at v but ensure spacing >= 7%
        target = max(v, last_y - 90)  # don't crush low values
        if target > last_y - 8:
            target = last_y - 8
        label_y[term] = max(target, 0)
        last_y = label_y[term]

    for term in term_order:
        vals = [pivot[term].get(y, 0) for y in years]
        ax.plot(years, vals, color=term_color[term], linewidth=2.6,
                 marker="o", markersize=7,
                 markerfacecolor=term_color[term],
                 markeredgecolor="white", markeredgewidth=1.2, zorder=4)
        # Direct label at right edge with leader line
        last_x = years[-1]
        last_v = vals[-1]
        ax.plot([last_x + 0.05, last_x + 0.50],
                [last_v, label_y[term]],
                color=term_color[term], linewidth=0.6, linestyle=":",
                zorder=3)
        ax.text(last_x + 0.55, label_y[term],
                term_label[term],
                color=term_color[term], fontsize=10, va="center",
                fontweight="bold")
        # Final value
        ax.text(last_x + 1.95, label_y[term],
                f"{int(last_v)}%",
                color=term_color[term], fontsize=10, va="center",
                fontweight="bold", ha="right")

    ax.set_xticks(years)
    ax.set_xticklabels(years, fontsize=11)
    ax.set_xlabel("")
    ax.set_xlim(years[0] - 0.15, years[-1] + 2.0)
    ax.set_ylim(-3, 110)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}%"))
    grid_horiz(ax)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.tick_params(axis="y", length=0)
    ax.set_ylabel("Cards mentioning the term",
                   color=MUTED, labelpad=10)

    add_title(fig,
              "What labs admit they can't measure has expanded",
              "Hallucination and bias plateau. CoT unfaithfulness, deception, "
              "and benchmark saturation emerge from 2024 onward.")
    add_source(fig, extra="Term counts via regex on raw card text (Railway API content_md).")
    out = DATA_DIR / "F_limitations_vocabulary.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")

# ============================================================
# G — Extraction recall (dumbbell chart: old → new per lab)
# Reads as: "the dot moved right after the upgrade".
# ============================================================
def chart_G():
    rows = read_csv_(DATA_DIR / "G_extraction_recall.csv")
    rows = [r for r in rows if r["mean_recall_pct"] not in ("", None)]

    labs_order = ["anthropic", "openai", "google", "meta", "mistral", "xai"]

    # Build a per-lab struct of {old: mean, new: mean}
    by_lab = defaultdict(dict)
    for r in rows:
        pipe = "old" if "old" in r["pipeline"] else "new"
        by_lab[r["lab"]][pipe] = float(r["mean_recall_pct"])

    fig = plt.figure(figsize=(11, 7), dpi=200, facecolor="white")
    ax = fig.add_axes([0.20, 0.16, 0.72, 0.60])

    OLD_COLOR = "#94A3B8"
    NEW_COLOR = "#3B82F6"

    deltas = []
    for i, lab in enumerate(labs_order):
        y = i
        old_v = by_lab[lab].get("old")
        new_v = by_lab[lab].get("new")

        if old_v is not None and new_v is not None:
            # Connecting line (the "dumbbell")
            ax.plot([old_v, new_v], [y, y],
                     color="#CBD5E1", linewidth=2.5, zorder=3,
                     solid_capstyle="round")
            # Old dot
            ax.scatter([old_v], [y], s=160,
                        color=OLD_COLOR, edgecolor="white",
                        linewidth=2, zorder=5)
            ax.text(old_v - 2, y, f"{int(old_v)}%",
                    ha="right", va="center",
                    fontsize=10, color=OLD_COLOR, fontweight="bold")
            # New dot
            ax.scatter([new_v], [y], s=180,
                        color=NEW_COLOR, edgecolor="white",
                        linewidth=2, zorder=5)
            ax.text(new_v + 2, y, f"{int(new_v)}%",
                    ha="left", va="center",
                    fontsize=10, color=NEW_COLOR, fontweight="bold")
            # Improvement delta — placed above the line, centered
            delta = int(new_v - old_v)
            mid = (old_v + new_v) / 2
            ax.text(mid, y - 0.32, f"+{delta} pp",
                    ha="center", va="bottom",
                    fontsize=9, color="#16A34A", fontweight="bold")
            deltas.append(delta)
        elif new_v is not None:
            # xAI — only new pipeline data exists
            ax.scatter([new_v], [y], s=180,
                        color=NEW_COLOR, edgecolor="white",
                        linewidth=2, zorder=5)
            ax.text(new_v + 2, y, f"{int(new_v)}%",
                    ha="left", va="center",
                    fontsize=10, color=NEW_COLOR, fontweight="bold")
            ax.text(new_v - 2, y, "no 2024 cards",
                    ha="right", va="center",
                    fontsize=9, color=MUTED, style="italic")

    # Lab name labels on left
    for i, lab in enumerate(labs_order):
        ax.text(-3, i, LAB_NAME[lab],
                ha="right", va="center",
                fontsize=12, color=INK, fontweight="bold",
                transform=ax.transData)

    ax.set_yticks([])
    ax.set_ylim(len(labs_order) - 0.5, -0.7)  # invert
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}%"))
    grid_vert(ax)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_xlabel("Mean extraction recall", color=MUTED, labelpad=10)

    # Legend — clean, in the chart area top-right
    leg_y = -0.55
    ax.scatter([28], [leg_y], s=120, color=OLD_COLOR,
                edgecolor="white", linewidth=2, zorder=5,
                transform=ax.transData)
    ax.text(31, leg_y, "Old pipeline (14k window)",
            ha="left", va="center", fontsize=10, color=BODY)
    ax.scatter([66], [leg_y], s=120, color=NEW_COLOR,
                edgecolor="white", linewidth=2, zorder=5,
                transform=ax.transData)
    ax.text(69, leg_y, "New pipeline (30k window)",
            ha="left", va="center", fontsize=10, color=BODY)

    avg_delta = int(sum(deltas) / len(deltas)) if deltas else 0
    add_title(fig,
              "The pipeline upgrade lifted recall across every lab",
              f"Mean extraction recall before vs after the 30k-window fix. "
              f"Average improvement: +{avg_delta} percentage points.")
    add_source(fig,
                extra=("Old-pipeline anchors from claims/system_audit.md; "
                       "new-pipeline cells estimated."))
    out = DATA_DIR / "G_extraction_recall.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")


def main():
    chart_D()
    chart_E()
    chart_A()
    chart_B()
    chart_C()
    chart_F()
    chart_G()
    print(f"\nAll 7 charts written to: {DATA_DIR}")


if __name__ == "__main__":
    main()
