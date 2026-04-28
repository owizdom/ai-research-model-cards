"""Build the 2026 overlap heatmap + the % shared over time line chart.

Inputs:
    charts/data/snapshot_<date>.json  — frozen pull from the live Railway API
    charts/release_dates.csv          — hand-curated publication dates (the bedrock)

Outputs:
    charts/data/overlap_2026.csv          — pairwise lab Jaccard for 2026 cards
    charts/data/overlap_over_time.csv     — quarter, pct_shared, n_cards, n_labs
    charts/overlap_2026_heatmap.{svg,png} — lab × lab Jaccard heatmap (2026 cut)
    charts/overlap_over_time.{svg,png}    — % shared per quarter, 4Q trailing window

Metric definitions (see also charts/README.md):
    - Benchmark slugs are family-collapsed first (mmlu_pro→mmlu, gpqa_diamond→gpqa, …)
      using the same rules the existing /api/v1/evals/fragmentation endpoint uses
      so this analysis is comparable to the homepage finding.
    - Lab-equal weighting: each lab contributes one benchmark set per window,
      regardless of how many cards it shipped. Anthropic's 6 cards do not get 6×
      voting weight over AI21's 1.
    - "% shared" = 1 − (n benchmarks reported by exactly one lab) / (n distinct
      benchmarks reported in window).
    - Pairwise Jaccard for the 2026 heatmap: |B_i ∩ B_j| / |B_i ∪ B_j|.
    - Filter: doc_type='model_card' only. Filter: state='scored' so v1/v2
      protocol output is comparable (v1 emitted only 'scored' rows).

Run:
    python3 charts/generate.py                # uses latest snapshot in charts/data/
    python3 charts/generate.py --refresh      # re-pull from live API first
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path

CHARTS_DIR = Path(__file__).parent
DATA_DIR = CHARTS_DIR / "data"
API_BASE = "https://modest-playfulness-production.up.railway.app/api/v1"


# Family canonicalization — ported from apps/api/src/api/v1/evals.py:117 (FAMILY_SQL_EXPR).
# Order matters: longer/more-specific patterns first.
def family_of(slug: str) -> str:
    s = slug.lower()
    if s == "mmlu" or s.startswith("mmlu_") or s == "mmmlu":
        return "mmlu"
    if s.startswith("humaneval"):
        return "humaneval"
    if s.startswith("gpqa"):
        return "gpqa"
    if s.startswith("swe_bench") or s.startswith("swe-bench"):
        return "swe_bench"
    if s == "math" or s.startswith("math_"):
        return "math"
    if s == "gsm8k" or s.startswith("gsm_") or s.startswith("gsm8k_"):
        return "gsm"
    if s.startswith("big_bench") or s.startswith("big-bench") or s == "bbh":
        return "big_bench"
    if s.startswith("livecodebench"):
        return "livecodebench"
    if s.startswith("arc_") or s.startswith("arc-"):
        return "arc"
    if s.startswith("aime"):
        return "aime"
    if s.startswith("mbpp"):
        return "mbpp"
    if s.startswith("mmmu"):
        return "mmmu"
    return s


def load_snapshot() -> dict:
    snaps = sorted(DATA_DIR.glob("snapshot_*.json"))
    if not snaps:
        sys.exit("No snapshot found. Run with --refresh.")
    return json.loads(snaps[-1].read_text())


def refresh_snapshot() -> Path:
    import urllib.request, concurrent.futures
    print(f"Pulling fresh data from {API_BASE} ...")
    def get(path):
        with urllib.request.urlopen(API_BASE + path, timeout=30) as r:
            return json.loads(r.read())
    labs = get("/labs")
    docs = get("/documents?limit=200")
    mcs = [d for d in docs if d["doc_type"] == "model_card"]
    def fetch(d):
        try:
            return d["id"], get(f"/evals/results/by-document/{d['id']}")
        except Exception as e:
            return d["id"], {"error": str(e)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        evals = dict(ex.map(fetch, mcs))
    today = date.today().isoformat()
    snap = {
        "snapshot_date": today, "source_api": API_BASE,
        "labs": labs, "documents": docs,
        "evals_by_document": {str(k): v for k, v in evals.items()},
    }
    out = DATA_DIR / f"snapshot_{today}.json"
    out.write_text(json.dumps(snap, indent=2))
    print(f"Wrote {out}")
    return out


def load_release_dates() -> dict[str, date]:
    rows = csv.DictReader((CHARTS_DIR / "release_dates.csv").open())
    return {r["document_slug"]: date.fromisoformat(r["release_date"]) for r in rows}


def build_card_records(snap: dict, dates: dict[str, date]) -> list[dict]:
    """One row per model card: lab, release_date, set of family-collapsed benchmark slugs."""
    by_slug = {d["slug"]: d for d in snap["documents"] if d["doc_type"] == "model_card"}
    records = []
    for slug, doc in by_slug.items():
        rd = dates.get(slug)
        if not rd:
            print(f"  warn: no release_date for {slug}, skipping")
            continue
        evals_data = snap["evals_by_document"].get(str(doc["id"]), {})
        evals = evals_data.get("evals", []) if isinstance(evals_data, dict) else []
        # state='scored' filter for v1↔v2 comparability. (v1 had no state field;
        # default to including it. v2 emits scored/mentioned/cited and we want only scored.)
        scored = [e for e in evals if (e.get("state") or "scored") == "scored"]
        families = {family_of(e["benchmark"]["slug"]) for e in scored if e.get("benchmark")}
        records.append({
            "doc_id": doc["id"],
            "slug": slug,
            "title": doc["title"],
            "lab_slug": doc["lab"]["slug"],
            "lab_name": doc["lab"]["name"],
            "release_date": rd,
            "n_evals": len(scored),
            "benchmarks": families,
        })
    records.sort(key=lambda r: r["release_date"])
    return records


# ─────────────────────────── 2026 overlap analysis ───────────────────────────

def overlap_2026(records: list[dict]) -> tuple[list[str], dict[tuple[str, str], dict]]:
    """Pairwise Jaccard between labs, on benchmark sets aggregated across each lab's 2026 cards."""
    cards_2026 = [r for r in records if r["release_date"].year == 2026]
    by_lab: dict[str, set[str]] = defaultdict(set)
    cards_per_lab: Counter = Counter()
    for r in cards_2026:
        by_lab[r["lab_slug"]] |= r["benchmarks"]
        cards_per_lab[r["lab_slug"]] += 1
    labs = sorted(by_lab.keys())
    pairs: dict[tuple[str, str], dict] = {}
    for a, b in combinations(labs, 2):
        A, B = by_lab[a], by_lab[b]
        inter = A & B
        union = A | B
        j = (len(inter) / len(union)) if union else 0.0
        pairs[(a, b)] = {"intersection": len(inter), "union": len(union), "jaccard": j}
    return labs, pairs, by_lab, cards_per_lab, cards_2026


# ─────────────────────────── % shared over time ───────────────────────────

def quarter_of(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def quarter_end(qstr: str) -> date:
    y, q = qstr.split("-Q")
    y = int(y); q = int(q)
    end_month = q * 3
    end_day = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][end_month - 1]
    return date(y, end_month, end_day)


def all_quarters(start: date, end: date) -> list[str]:
    quarters: list[str] = []
    y, q = start.year, (start.month - 1) // 3 + 1
    end_y, end_q = end.year, (end.month - 1) // 3 + 1
    while (y, q) <= (end_y, end_q):
        quarters.append(f"{y}-Q{q}")
        q += 1
        if q > 4:
            y += 1; q = 1
    return quarters


def overlap_over_time(records: list[dict], window_quarters: int = 4) -> list[dict]:
    """For each quarter, compute % shared over the trailing N-quarter window."""
    if not records:
        return []
    start = min(r["release_date"] for r in records)
    end = max(r["release_date"] for r in records)
    series: list[dict] = []
    quarters = all_quarters(start, end)
    for qi, qstr in enumerate(quarters):
        if qi < window_quarters - 1:
            continue  # need full window
        window = quarters[qi - window_quarters + 1 : qi + 1]
        window_start = quarter_end(window[0]).replace(day=1)  # first day of first quarter
        # easier: reconstruct first-day-of-quarter
        wy, wq = window[0].split("-Q"); wy = int(wy); wq = int(wq)
        window_start = date(wy, (wq - 1) * 3 + 1, 1)
        window_end = quarter_end(window[-1])
        in_window = [r for r in records if window_start <= r["release_date"] <= window_end]
        # Lab-equal: aggregate to per-lab sets
        by_lab: dict[str, set[str]] = defaultdict(set)
        for r in in_window:
            by_lab[r["lab_slug"]] |= r["benchmarks"]
        labs_active = list(by_lab.keys())
        # Count distinct benchmarks and how many labs report each
        bench_lab_count: Counter = Counter()
        for s in by_lab.values():
            for b in s:
                bench_lab_count[b] += 1
        total_distinct = len(bench_lab_count)
        shared = sum(1 for v in bench_lab_count.values() if v >= 2)
        pct_shared = (shared / total_distinct * 100) if total_distinct else 0.0
        series.append({
            "quarter": qstr,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "n_cards": len(in_window),
            "n_labs": len(labs_active),
            "n_distinct_benchmarks": total_distinct,
            "n_shared_2plus": shared,
            "pct_shared": round(pct_shared, 1),
        })
    return series


def overlap_yearly(records: list[dict]) -> list[dict]:
    """Aggregate records by calendar year (lab-equal weighting). Cleaner story than rolling."""
    if not records:
        return []
    by_year_lab: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    cards_per_year: Counter = Counter()
    labs_per_year: dict[int, set[str]] = defaultdict(set)
    for r in records:
        y = r["release_date"].year
        by_year_lab[y][r["lab_slug"]] |= r["benchmarks"]
        cards_per_year[y] += 1
        labs_per_year[y].add(r["lab_slug"])
    rows: list[dict] = []
    for y in sorted(by_year_lab):
        bench_lab_count: Counter = Counter()
        for s in by_year_lab[y].values():
            for b in s:
                bench_lab_count[b] += 1
        total = len(bench_lab_count)
        shared = sum(1 for v in bench_lab_count.values() if v >= 2)
        rows.append({
            "year": y,
            "n_cards": cards_per_year[y],
            "n_labs": len(labs_per_year[y]),
            "n_total_benchmarks": total,
            "n_shared_2plus": shared,
            "n_lab_unique": total - shared,
            "pct_shared": round((shared / total * 100) if total else 0.0, 1),
        })
    return rows


# ─────────────────────────────── render ───────────────────────────────

def render_heatmap(labs, pairs, by_lab, cards_per_lab, cards_2026, out_base: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    n = len(labs)
    if n == 0:
        print("  no 2026 cards — skipping heatmap")
        return
    M = np.full((n, n), np.nan)
    for i, a in enumerate(labs):
        M[i, i] = 1.0
    for (a, b), v in pairs.items():
        i, j = labs.index(a), labs.index(b)
        M[i, j] = v["jaccard"]
        M[j, i] = v["jaccard"]

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    im = ax.imshow(M, cmap="YlOrBr", vmin=0, vmax=1)

    lab_labels = [f"{l}\n({cards_per_lab[l]} card{'s' if cards_per_lab[l] != 1 else ''}, {len(by_lab[l])} bench)" for l in labs]
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(lab_labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(lab_labels, fontsize=9)

    for i in range(n):
        for j in range(n):
            v = M[i, j]
            if np.isnan(v):
                continue
            txt = "1.00" if i == j else f"{v:.2f}"
            color = "white" if v > 0.5 else "#333"
            ax.text(j, i, txt, ha="center", va="center", fontsize=10, color=color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Jaccard similarity (|A∩B| / |A∪B|)", fontsize=9)

    n_cards = len(cards_2026)
    union_total = len(set().union(*by_lab.values())) if by_lab else 0
    max_off_diag = max((v["jaccard"] for v in pairs.values()), default=0.0)
    ax.set_title(
        f"Lab × Lab benchmark overlap — 2026 model cards\n"
        f"{n_cards} cards across {n} labs · {union_total} distinct benchmarks (family-collapsed)",
        fontsize=11, pad=14,
    )
    if max_off_diag == 0:
        fig.text(
            0.5, 0.07,
            "Zero pairwise overlap. Driven by document-mix more than divergence:\n"
            "Anthropic ships comprehensive cards (cap. + safety); Google's Gemini 3.1 Pro card is "
            "safety-only; OpenAI's cards are internal-eval focused (Codex, GPT-5.5).",
            ha="center", fontsize=8, color="#444", style="italic",
        )
    fig.text(
        0.5, 0.01,
        "Family-collapse: mmlu_pro→mmlu, gpqa_diamond→gpqa, etc. · scored evals only · "
        "Free Systems Lab · model-card.vercel.app",
        ha="center", fontsize=7, color="#666",
    )
    fig.tight_layout(rect=(0, 0.13 if max_off_diag == 0 else 0.04, 1, 1))
    fig.savefig(str(out_base) + ".svg", format="svg", bbox_inches="tight")
    fig.savefig(str(out_base) + ".png", format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  wrote {out_base.name}.svg + .png")


def render_over_time(series: list[dict], out_base: Path):
    """Two-line chart on rolling 12-month quarterly windows.

    Quarterly cadence (11 points across 2023-Q4 → 2026-Q2) gives a smooth
    trajectory; yearly bins (4 points) showed a misleading partial-year cliff.
    No stacking — the reader sees two lines diverge: total climbs, shared
    stays flat. The gap = "the lab-unique tail." This is the FT Visual
    Vocabulary "magnitude pair" pattern: when the story is the gap between
    numerator and denominator, show both, side by side.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not series:
        print("  empty series — skipping over-time chart")
        return

    quarters = [s["quarter"].replace("-Q", " Q") for s in series]
    total = [s["n_distinct_benchmarks"] for s in series]
    shared = [s["n_shared_2plus"] for s in series]
    pct = [s["pct_shared"] for s in series]
    n = len(series)

    fig, ax = plt.subplots(figsize=(13.0, 7.0))
    x = list(range(n))

    TOTAL_COLOR = "#A87B4F"
    SHARED_COLOR = "#1A7A6D"
    GAP_FILL = "#F0DCC0"

    # Shade the gap between the two lines — the lab-unique tail
    ax.fill_between(x, shared, total, color=GAP_FILL, alpha=0.55,
                    label="Gap = benchmarks only one lab reports")

    # Two lines on the same axis, no stacking
    ax.plot(x, total, color=TOTAL_COLOR, linewidth=2.6, marker="o", markersize=8,
            markerfacecolor="white", markeredgewidth=2.0,
            label="Total distinct benchmarks reported")
    ax.plot(x, shared, color=SHARED_COLOR, linewidth=3.0, marker="o", markersize=8,
            markerfacecolor=SHARED_COLOR,
            label="Benchmarks reported by ≥2 labs")

    # Endpoint values labeled prominently on both lines
    ax.annotate(f"{total[0]}", (0, total[0]), textcoords="offset points",
                xytext=(0, 14), ha="center", fontsize=11, fontweight="bold", color=TOTAL_COLOR)
    ax.annotate(f"{total[-1]}", (n - 1, total[-1]), textcoords="offset points",
                xytext=(0, 14), ha="center", fontsize=11, fontweight="bold", color=TOTAL_COLOR)
    # Shared-line endpoint labels placed ABOVE the markers (between the two lines),
    # not below — below collides with the cards/labs context strip.
    ax.annotate(f"{shared[0]}", (0, shared[0]), textcoords="offset points",
                xytext=(0, 12), ha="center", fontsize=11, fontweight="bold", color=SHARED_COLOR)
    ax.annotate(f"{shared[-1]}", (n - 1, shared[-1]), textcoords="offset points",
                xytext=(0, 12), ha="center", fontsize=11, fontweight="bold", color=SHARED_COLOR)
    # Mark the peak of the total line so the reader sees absolute magnitudes mid-trajectory
    peak_idx = max(range(n), key=lambda i: total[i])
    if peak_idx not in (0, n - 1):
        ax.annotate(f"{total[peak_idx]}", (peak_idx, total[peak_idx]),
                    textcoords="offset points", xytext=(0, 14), ha="center",
                    fontsize=10, fontweight="bold", color=TOTAL_COLOR)

    # Headline: the percentage trajectory in plain time language.
    # Quarter labels in the chart are rolling-window endpoints, not snapshots —
    # so "In 2023 Q4" would mislead. Use natural-language time anchors.
    fig.text(
        0.5, 0.915,
        f"In late 2023, {pct[0]:.0f}% of benchmarks were shared by ≥2 labs. "
        f"Today: {pct[-1]:.0f}%.",
        ha="center", fontsize=12.5, color="#333", style="italic",
    )

    # Axes
    ax.set_xlim(-0.45, n - 0.55)
    ax.set_ylim(-max(total) * 0.13, max(total) * 1.10)  # leave room below for context strip
    ax.set_xticks(x)
    ax.set_xticklabels(quarters, rotation=30, ha="right", fontsize=9.5)
    ax.set_ylabel("Number of distinct benchmarks", fontsize=11)
    ax.tick_params(axis="y", labelsize=9)
    ax.grid(axis="y", linestyle=":", color="#ccc", alpha=0.6)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    # Pin y-ticks to a sensible set rather than matplotlib's auto-default that included up to 250
    ymax = max(total)
    step = 25 if ymax < 200 else 50
    ax.set_yticks([y for y in range(0, int(ymax) + step, step) if y <= ymax * 1.10])

    fig.suptitle(
        "Frontier labs report many more benchmarks each year — but few are shared",
        fontsize=15.5, fontweight="bold", y=0.985, x=0.5, ha="center",
    )

    ax.legend(loc="upper left", frameon=False, fontsize=10,
              handlelength=2.5, labelspacing=0.5)

    # Context strip below the chart (in the negative-y reserved space)
    strip_y = -max(total) * 0.075
    for i, s in enumerate(series):
        ax.text(i, strip_y,
                f"{s['n_cards']} cards\n{s['n_labs']} labs",
                ha="center", va="center", fontsize=7.5, color="#888")

    fig.text(
        0.5, 0.012,
        f"Each point = all model cards released in the trailing 12 months ending that quarter ({quarters[0]} window includes 2023). "
        "Lab-equal weighting (each lab counted once per window). "
        "Benchmark family-collapsed (mmlu_pro→mmlu, gpqa_diamond→gpqa, swe_bench_verified→swe_bench, etc.) · Scored evals only · Free Systems Lab",
        ha="center", fontsize=7, color="#666",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.89))
    fig.savefig(str(out_base) + ".svg", format="svg", bbox_inches="tight")
    fig.savefig(str(out_base) + ".png", format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  wrote {out_base.name}.svg + .png")


# ─────────────────────────────── csvs ───────────────────────────────

def write_overlap_2026_csv(labs, pairs, by_lab, out: Path):
    fieldnames = ["lab_a", "lab_b", "n_a", "n_b", "n_intersect", "n_union", "jaccard"]
    rows = []
    for (a, b), v in sorted(pairs.items()):
        rows.append({
            "lab_a": a, "lab_b": b,
            "n_a": len(by_lab[a]), "n_b": len(by_lab[b]),
            "n_intersect": v["intersection"], "n_union": v["union"],
            "jaccard": round(v["jaccard"], 4),
        })
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
    print(f"  wrote {out.name} ({len(rows)} pairs)")


def write_over_time_csv(series: list[dict], out: Path):
    if not series:
        out.write_text("no data\n"); return
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(series[0].keys()))
        w.writeheader(); w.writerows(series)
    print(f"  wrote {out.name} ({len(series)} rows)")


# ─────────────────────────────── main ───────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="Re-pull from the live API first")
    args = ap.parse_args()

    if args.refresh:
        refresh_snapshot()
    snap = load_snapshot()
    dates = load_release_dates()
    records = build_card_records(snap, dates)
    print(f"Loaded {len(records)} model cards with release dates and benchmarks")

    # 2026 cut
    print("\n— 2026 overlap analysis —")
    labs, pairs, by_lab, cards_per_lab, cards_2026 = overlap_2026(records)
    print(f"  {len(cards_2026)} cards from {len(labs)} labs in 2026")
    for l in labs:
        print(f"    {l}: {cards_per_lab[l]} card(s), {len(by_lab[l])} distinct benchmarks")
    write_overlap_2026_csv(labs, pairs, by_lab, DATA_DIR / "overlap_2026.csv")
    render_heatmap(labs, pairs, by_lab, cards_per_lab, cards_2026,
                   CHARTS_DIR / "overlap_2026_heatmap")

    # Over-time chart (rolling 12-month windows, quarterly stride)
    print("\n— Overlap over time (rolling 12-month, quarterly stride) —")
    series = overlap_over_time(records, window_quarters=4)
    for s in series:
        flag = "" if s["n_cards"] >= 6 and s["n_labs"] >= 3 else "  *low N*"
        print(f"  {s['quarter']}  pct_shared={s['pct_shared']:5.1f}%  "
              f"shared={s['n_shared_2plus']:3d}  total={s['n_distinct_benchmarks']:3d}  "
              f"n_cards={s['n_cards']:3d}  n_labs={s['n_labs']}{flag}")
    write_over_time_csv(series, DATA_DIR / "overlap_over_time.csv")
    render_over_time(series, CHARTS_DIR / "overlap_over_time")

    # Yearly rollup also written for reference
    yearly = overlap_yearly(records)
    write_over_time_csv(yearly, DATA_DIR / "overlap_by_year.csv")

    print("\nDone.")


if __name__ == "__main__":
    main()
