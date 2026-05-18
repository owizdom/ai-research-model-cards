#!/usr/bin/env python3
"""Research-grade one-page scorecard for a single model card.

Pulls live data from the Model Card Explorer API and renders one page (PNG+PDF)
designed so every element does work — no decoration.

  • Pull quote — the strongest hedging sentence from the doc itself
  • Family ladder — this card's place in the lab's generation timeline
  • Canonical capabilities — fixed list (MMLU, GPQA, HumanEval, SWE-bench, MATH,
    AIME, MMMU, HLE, MBPP, IFEval, BBH, LiveCodeBench) with deltas vs prior gen
  • Canonical benchmarks dropped — filtered to public+comparable, not the
    internal-harness churn that inflates a naive diff
  • Hedge rate vs corpus — per-1000-words rate compared to lab + global avg
  • What's new + Safety posture — from the Claude-written chaptered summary
  • Composition strip — heatstrip with section anchors

Usage:
    python3 charts/build_scorecard.py --doc-id 8 --out claude_sonnet_4_6_scorecard
    python3 charts/build_scorecard.py --doc-id 8 --vs-doc-id 5 --out ...

Outputs land in charts/scorecards/ unless --out is an absolute path.
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
from matplotlib.lines import Line2D

API = "https://modest-playfulness-production.up.railway.app/api/v1"

# ── Palette: deliberately constrained. Accent per lab; ink/sub for everything else. ──
INK         = "#1B1816"
SUBINK      = "#6E6960"
HUSH        = "#A8A299"
PAPER       = "#FAF8F4"
PANEL       = "#FFFFFF"
RULE        = "#E2DCD2"
RULE_STRONG = "#9D968B"
GOOD        = "#2D7A4E"
WARN        = "#B83228"
QUOTE_BG    = "#F2EDE3"

LAB_ACCENTS = {
    "anthropic": "#D4791A",
    "openai":    "#10A37F",
    "google":    "#4285F4",
    "meta":      "#6366F1",
    "mistral":   "#DC2626",
    "xai":       "#111827",
}

FAMILY_OF_LAB = {
    "anthropic": "claude", "openai": "gpt", "google": "gemini",
    "meta": "llama", "mistral": "mistral", "xai": "grok",
}

# ── Canonical capability list — the cross-lab-comparable benchmarks ──
CANONICAL = [
    # (display name, slug-aliases-to-match)
    ("MMLU",            ("mmlu", "mmlu_pro")),
    ("GPQA Diamond",    ("gpqa_diamond", "gpqa")),
    ("HumanEval",       ("humaneval", "humaneval_plus")),
    ("SWE-bench",       ("swe_bench_verified", "swe_bench")),
    ("MATH",            ("math", "math_500")),
    ("AIME",            ("aime_2025", "aime_2024", "aime")),
    ("MMMU",            ("mmmu_pro", "mmmu")),
    ("HLE",             ("hle",)),
    ("MBPP",            ("mbpp", "mbpp_plus")),
    ("IFEval",          ("ifeval",)),
    ("BIG-Bench Hard",  ("big_bench_hard",)),
    ("LiveCodeBench",   ("livecodebench",)),
]

# Long enough to be a substantive hedge, short enough to be specific.
HEDGE_PHRASES = [
    "cannot rule out", "could not rule out", "could not verify",
    "we cannot exclude", "approached our threshold", "approaching our threshold",
    "crossed our threshold", "becoming increasingly difficult",
    "we have not been able", "we did not release",
    "we decided not to", "we elected not to",
    "saturated", "we believe",
    "elicited harmful", "elicited dangerous", "elicited unsafe",
    "remain open", "remaining open", "open question",
    "withheld", "not yet well understood",
    "we have not evaluated", "we do not yet",
    "further research", "future work needed",
    "uncertain whether", "not confident",
]


# ───────────────────────────── data ingest ─────────────────────────────

def _fetch(path):
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as r:
        return json.loads(r.read())


def collect_for_doc(doc_id):
    doc      = _fetch(f"/documents/{doc_id}")
    content  = _fetch(f"/documents/{doc_id}/content")
    evals    = _fetch(f"/evals/results/by-document/{doc_id}")
    lab_slug = doc["lab"]["slug"]
    family   = _fetch(f"/families/{FAMILY_OF_LAB[lab_slug]}")
    return {
        "doc": doc, "content": content, "evals": evals, "family": family,
        "lab_slug": lab_slug,
    }


def fetch_evals_for_docs(doc_ids):
    """Parallel fetch by-document evals for a list of doc ids."""
    out = {}
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        future_map = {pool.submit(_fetch, f"/evals/results/by-document/{i}"): i
                      for i in doc_ids}
        for fut in cf.as_completed(future_map):
            try:
                out[future_map[fut]] = fut.result()
            except Exception as e:
                print(f"  (skip doc {future_map[fut]}: {e})", file=sys.stderr)
    return out


def fetch_content_for_docs(doc_ids):
    """Parallel fetch /content for a list of doc ids — used for corpus hedging."""
    out = {}
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        future_map = {pool.submit(_fetch, f"/documents/{i}/content"): i
                      for i in doc_ids}
        for fut in cf.as_completed(future_map):
            try:
                out[future_map[fut]] = fut.result()
            except Exception as e:
                print(f"  (skip content {future_map[fut]}: {e})", file=sys.stderr)
    return out


# ─────────────────────────────── derive ────────────────────────────────

def slug_max_score(evals_list, slug_aliases):
    """Return (score, model_name) for the highest-scored row matching any alias,
    or (None, None)."""
    best = None
    for e in evals_list:
        slug = e["benchmark"]["slug"]
        if slug not in slug_aliases:
            continue
        if e.get("score") is None:
            continue
        if e.get("state") not in (None, "scored"):
            continue
        if e["score"] > 100.5 or e["score"] < 0:
            continue
        if best is None or e["score"] > best[0]:
            best = (e["score"], e.get("model_name"))
    return best if best else (None, None)


def headline_grid(this_evals, prior_evals):
    """For each canonical bench, current score vs prior-gen score."""
    rows = []
    for label, aliases in CANONICAL:
        cur, model = slug_max_score(this_evals, set(aliases))
        prev, _    = slug_max_score(prior_evals, set(aliases))
        rows.append({"label": label, "cur": cur, "prev": prev, "model": model})
    return rows


def derive_diff_canonical(this_evals, prior_evals_flat):
    """Compute kept/added/dropped restricted to canonical benchmarks.

    prior_evals_flat is a list of dicts with keys 'slug','name'.
    """
    canonical_slug_set = set()
    canonical_label_for_slug = {}
    for label, aliases in CANONICAL:
        for a in aliases:
            canonical_slug_set.add(a)
            canonical_label_for_slug[a] = label

    this_canonical_labels = set()
    for e in this_evals:
        slug = e["benchmark"]["slug"]
        if slug in canonical_slug_set:
            this_canonical_labels.add(canonical_label_for_slug[slug])

    prior_canonical_labels = set()
    for e in prior_evals_flat:
        if e["slug"] in canonical_slug_set:
            prior_canonical_labels.add(canonical_label_for_slug[e["slug"]])

    return {
        "kept":    sorted(this_canonical_labels & prior_canonical_labels),
        "added":   sorted(this_canonical_labels - prior_canonical_labels),
        "dropped": sorted(prior_canonical_labels - this_canonical_labels),
    }


LIGATURE_MAP = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl",
    "’": "'",   "‘": "'",
    "“": '"',   "”": '"',
}


def _normalize(s):
    """Normalize unicode ligatures + smart quotes so regex grep works on PDF-derived text."""
    if not s:
        return s
    for k, v in LIGATURE_MAP.items():
        s = s.replace(k, v)
    return s


def hedge_count(md):
    md = _normalize(md)
    return sum(len(re.findall(re.escape(p), md, re.IGNORECASE))
               for p in HEDGE_PHRASES)


def hedge_rate_per_1k(md, word_count):
    if not word_count:
        return 0.0
    return hedge_count(md) / max(word_count, 1) * 1000.0


def pick_pull_quote(md):
    """Find the strongest hedging sentence — substantive predicate, ≤ 280 chars.
    Ligatures and smart quotes are normalized first so the regex hits."""
    priority = [
        "becoming increasingly difficult", "cannot rule out", "could not rule out",
        "ruling out", "approached our threshold", "crossed our threshold",
        "elicited harmful", "elicited dangerous", "elicited unsafe",
        "we decided not to", "we elected not to",
        "could not verify", "we cannot exclude",
        "we have not been able", "not yet well understood",
    ]
    norm = re.sub(r"\s+", " ", _normalize(md))
    for phrase in priority:
        for m in re.finditer(re.escape(phrase), norm, re.IGNORECASE):
            start = max(0, m.start() - 240)
            end   = min(len(norm), m.end() + 240)
            window = norm[start:end]
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", window)
            for s in sentences:
                if phrase.lower() in s.lower() and 50 <= len(s) <= 280:
                    return s.strip().rstrip("., ") + "."
    return None


def family_ladder(family, this_doc_id):
    """Order generations by parsed version tuple so Opus/Sonnet/Haiku of the
    same version land together, in tier order, and dated entries don't get
    clustered up front by an empty-string sort key."""
    TIER_RANK = {"opus": 0, "sonnet": 1, "haiku": 2,
                 "pro": 0, "flash": 1, "nano": 2,
                 "mythos": 99}  # Mythos = "next" preview

    def version_tuple(g):
        name = (g.get("name") or "").lower()
        slug = (g.get("slug") or "").lower()
        text = f"{slug} {name}"
        # Major.minor (3.5, 4.1, 4.6, etc.)
        vm = re.search(r"(\d+)\.(\d+)", text)
        major, minor = (int(vm.group(1)), int(vm.group(2))) if vm else (
            (int(re.search(r"\d+", text).group(0)), 0) if re.search(r"\d", text) else (0, 0)
        )
        tier_rank = 50
        for word, rank in TIER_RANK.items():
            if word in text:
                tier_rank = rank
                break
        # Mythos is a "preview of next" — bump it past everything else in its major
        if "mythos" in text:
            minor = 99
        return (major, minor, tier_rank, slug)

    gens = sorted(family["generations"], key=version_tuple)
    return [{"slug": g["slug"], "name": g["name"],
             "evals": g["eval_count"], "doc_id": g.get("document_id"),
             "release_date": g.get("release_date"),
             "is_this": g.get("document_id") == this_doc_id}
            for g in gens]


def find_section_anchors(content, max_anchors=4):
    """Map a few outline headings to heatstrip-segment positions.

    Use the title text (case-insensitive, normalized) against the body markdown
    so we don't depend on "## " prefix surviving cleanup. Picks up to
    max_anchors evenly-distributed-by-position headings.
    """
    outline = content.get("outline") or []
    md = _normalize(content.get("content_md", ""))
    if not outline or not md:
        return []
    n_seg = max(1, len(content.get("heatstrip") or []) or 20)
    L = len(md)

    # Find every outline title's position via case-insensitive search
    positions = []
    seen_titles = set()
    for h in outline:
        if h["level"] > 3:
            continue
        title = _normalize(h["title"]).strip()
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        idx = md.lower().find(key)
        if idx < 0:
            continue
        positions.append((idx, title))

    if not positions:
        return []
    positions.sort()

    # Down-sample to max_anchors evenly spaced by position
    if len(positions) <= max_anchors:
        chosen = positions
    else:
        step = len(positions) / max_anchors
        chosen = [positions[int(i * step)] for i in range(max_anchors)]

    out = []
    for idx, title in chosen:
        seg = int(idx / L * n_seg)
        seg = max(0, min(n_seg - 1, seg))
        out.append((seg, title))
    return out


# ─────────────────────────────── render ────────────────────────────────

def render(data, prior_doc_id, corpus_hedge_stats, out_stem):
    doc      = data["doc"]
    content  = data["content"]
    evals    = data["evals"]["evals"]
    family   = data["family"]
    lab_slug = data["lab_slug"]
    accent   = LAB_ACCENTS.get(lab_slug, INK)

    # Compute headline grid (cur vs prior gen)
    prior_evals_obj = data["prior_evals_obj"]            # list[dict] with 'benchmark' nesting
    prior_evals_flat = data["prior_evals_flat"]          # flat slug/name list
    h_rows = headline_grid(evals, prior_evals_obj)
    diff = derive_diff_canonical(evals, prior_evals_flat)

    # This card's hedge rate
    md = content.get("content_md", "")
    wc = content.get("word_count", 0) or 0
    this_rate = hedge_rate_per_1k(md, wc)
    quote = pick_pull_quote(md)

    # Family ladder
    ladder = family_ladder(family, this_doc_id=doc["id"])

    # Section anchors
    anchors = find_section_anchors(content)

    # Pull "what's new" + safety posture from chaptered summary
    summary = (content.get("summary") or {}).get("chapters", [])
    by_title = {c["title"].lower(): c["prose"] for c in summary}
    whats_new = (by_title.get("what's new") or "").strip()
    mitigations = (by_title.get("mitigations") or "").strip()
    deployment = (by_title.get("deployment and access") or "").strip()

    # ─── canvas ───
    fig = plt.figure(figsize=(8.5, 11), dpi=200, facecolor=PAPER)

    def panel(x, y, w, h):
        ax = fig.add_axes([x, y, w, h])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        return ax

    def hline(ax, y, x0=0, x1=1, color=RULE, lw=0.6):
        ax.add_line(Line2D([x0, x1], [y, y], color=color, lw=lw))

    # ─── 1. Title block (top 11%) ───
    head = panel(0.055, 0.890, 0.890, 0.105)
    head.text(0, 0.94, doc["lab"]["name"].upper() + " · MODEL CARD SCORECARD",
              fontsize=8, color=accent, weight="bold", family="sans-serif")
    head.text(1.0, 0.94,
              f"{ladder.index([l for l in ladder if l['is_this']][0]) + 1} of "
              f"{len(ladder)} {doc['lab']['name'].split()[0]} cards",
              fontsize=8, color=SUBINK, family="sans-serif", ha="right")
    head.text(0, 0.50, doc["title"],
              fontsize=24, color=INK, weight="bold", family="serif")
    meta = []
    if wc: meta.append(f"{wc:,} words")
    if content.get("read_minutes"): meta.append(f"{content['read_minutes']} min read")
    if content.get("version_date"): meta.append(content["version_date"])
    meta.append(f"doc id {doc['id']}")
    head.text(0, 0.08, "  ·  ".join(meta),
              fontsize=8.5, color=SUBINK, family="sans-serif")

    # ─── 2. Pull quote (boxed) ───
    if quote:
        q = panel(0.055, 0.825, 0.890, 0.060)
        q.add_patch(Rectangle((0, 0), 1, 1, facecolor=QUOTE_BG, lw=0))
        q.add_patch(Rectangle((0, 0), 0.006, 1, facecolor=accent, lw=0))
        # Wrap quote (~75 chars per line)
        words = quote.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 78:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur: lines.append(cur)
        lines = lines[:3]
        for i, ln in enumerate(lines):
            q.text(0.025, 0.78 - i * 0.30,
                   ("“" if i == 0 else "") + ln + ("”" if i == len(lines) - 1 else ""),
                   fontsize=10.5, color=INK, family="serif", style="italic",
                   va="center")
        q.text(0.985, 0.18, "— extracted from doc",
               fontsize=6.8, color=SUBINK, family="sans-serif",
               ha="right", style="italic")

    # ─── 3. Family ladder ───
    lad = panel(0.055, 0.738, 0.890, 0.075)
    lad.text(0, 0.92, "FAMILY LADDER", fontsize=8, color=accent, weight="bold",
             family="sans-serif")
    hline(lad, 0.86, color=RULE)

    n = len(ladder)
    def short_gen_label(name):
        """Hyper-compact label — version digits + tier letter.
        e.g. 'Claude Sonnet 4.5' -> '4.5S', 'Claude Haiku 4.5' -> '4.5H'."""
        s = name
        for prefix in ("Claude ", "GPT-", "Gemini ", "Llama ", "Mistral ", "Grok "):
            s = s.replace(prefix, "")
        s = s.replace("System Card", "").replace("Model Card", "").strip()
        s = re.sub(r"\s*\(.*\)", "", s)
        m = re.match(r"(Sonnet|Opus|Haiku|Mythos)\s*([\d.]+)?", s)
        if m:
            tier_letter = m.group(1)[0]
            ver = m.group(2) or ""
            if m.group(1) == "Mythos":
                return "Myth"
            return f"{ver}{tier_letter}" if ver else tier_letter
        v = re.search(r"\d[\d.]*", s)
        return v.group(0) if v else s[:5]

    for i, g in enumerate(ladder):
        x = (i + 0.5) / n
        if g["is_this"]:
            lad.add_patch(Circle((x, 0.50), 0.013, facecolor=accent,
                                  edgecolor=accent, lw=0))
        else:
            lad.add_patch(Circle((x, 0.50), 0.008, facecolor=PAPER,
                                  edgecolor=RULE_STRONG, lw=1.0))
        if i < n - 1:
            lad.add_line(Line2D([x + 0.012, (i + 1.5) / n - 0.012],
                                 [0.50, 0.50], color=RULE_STRONG, lw=0.6))
        short = short_gen_label(g["name"])
        lad.text(x, 0.72, short, fontsize=6.5,
                 color=accent if g["is_this"] else INK,
                 ha="center", va="center", family="sans-serif",
                 weight="bold" if g["is_this"] else "normal")
        lad.text(x, 0.22, str(g["evals"]), fontsize=6, color=SUBINK,
                 ha="center", va="center", family="sans-serif")

    # ─── 4. Canonical capabilities table ───
    cap = panel(0.055, 0.495, 0.490, 0.235)
    cap.text(0, 0.97, "CANONICAL CAPABILITIES",
             fontsize=8, color=accent, weight="bold", family="sans-serif")
    prior_label = (f"vs {data.get('prior_gen_label') or 'prior gen'}"
                   if prior_doc_id else "no prior gen in family")
    cap.text(1.0, 0.97, prior_label, fontsize=7, color=SUBINK,
             family="sans-serif", ha="right")
    hline(cap, 0.945)

    n_rows = len(h_rows)
    row_h = 0.88 / n_rows
    for i, r in enumerate(h_rows):
        y = 0.92 - (i + 1) * row_h
        # Label
        cap.text(0.0, y + row_h / 2, r["label"],
                 fontsize=8.5, color=INK, family="serif", va="center")
        # Score
        if r["cur"] is not None:
            cap.text(0.58, y + row_h / 2, f"{r['cur']:.1f}",
                     fontsize=10, color=INK, family="serif",
                     weight="bold", va="center", ha="right")
        else:
            cap.text(0.58, y + row_h / 2, "—",
                     fontsize=10, color=HUSH, family="serif",
                     va="center", ha="right")
        # Delta
        if r["cur"] is not None and r["prev"] is not None:
            delta = r["cur"] - r["prev"]
            if abs(delta) < 0.05:
                txt, col = "─ flat", SUBINK
            elif delta > 0:
                txt, col = f"▲ +{delta:.1f}", GOOD
            else:
                txt, col = f"▼ {delta:.1f}", WARN
            cap.text(0.66, y + row_h / 2, txt,
                     fontsize=8.5, color=col, family="sans-serif",
                     weight="bold", va="center")
        elif r["cur"] is None and r["prev"] is not None:
            cap.text(0.66, y + row_h / 2,
                     f"◀ dropped  (prior: {r['prev']:.1f})",
                     fontsize=7.5, color=WARN, family="sans-serif",
                     weight="bold", va="center", style="italic")
        elif r["cur"] is not None and r["prev"] is None:
            cap.text(0.66, y + row_h / 2, "new in this card",
                     fontsize=7.5, color=GOOD, family="sans-serif",
                     style="italic", va="center")
        else:
            cap.text(0.66, y + row_h / 2, "not reported either",
                     fontsize=7.5, color=HUSH, family="sans-serif",
                     style="italic", va="center")
        hline(cap, y, color=RULE, lw=0.3)

    # ─── 5. Canonical dropped/added (right of capabilities) ───
    diff_p = panel(0.560, 0.495, 0.385, 0.235)
    diff_p.text(0, 0.97, "DROPPED  (canonical only)",
                fontsize=8, color=accent, weight="bold", family="sans-serif")
    hline(diff_p, 0.945)
    if diff["dropped"]:
        for i, lbl in enumerate(diff["dropped"][:8]):
            diff_p.text(0, 0.88 - i * 0.07, f"▼  {lbl}",
                        fontsize=8.5, color=WARN, family="serif",
                        weight="bold")
    else:
        diff_p.text(0, 0.88, "none — every canonical benchmark from prior gen retained",
                    fontsize=8, color=SUBINK, family="serif", style="italic")

    diff_p.text(0, 0.36, "NEW  (canonical, first-time in family)",
                fontsize=8, color=accent, weight="bold", family="sans-serif")
    hline(diff_p, 0.335)
    if diff["added"]:
        for i, lbl in enumerate(diff["added"][:5]):
            diff_p.text(0, 0.27 - i * 0.06, f"▲  {lbl}",
                        fontsize=8.5, color=GOOD, family="serif",
                        weight="bold")
    else:
        diff_p.text(0, 0.27, "none — every canonical here was reported before",
                    fontsize=8, color=SUBINK, family="serif", style="italic")

    # ─── 6. Hedge rate vs corpus ───
    hed = panel(0.055, 0.345, 0.490, 0.135)
    hed.text(0, 0.94, "HEDGE RATE vs CORPUS",
             fontsize=8, color=accent, weight="bold", family="sans-serif")
    hed.text(1.0, 0.94, "phrases per 1,000 words",
             fontsize=7, color=SUBINK, family="sans-serif", ha="right")
    hline(hed, 0.90)

    lab_rate    = corpus_hedge_stats["per_lab"].get(lab_slug, 0.0)
    corpus_rate = corpus_hedge_stats["global"]
    max_rate    = corpus_hedge_stats["max"]
    scale_max   = max(0.8, max_rate * 1.15)

    bars = [
        ("this card",     this_rate,   accent, True),
        (f"{lab_slug} avg", lab_rate,  INK,    False),
        ("corpus avg",    corpus_rate, SUBINK, False),
        ("max in corpus", max_rate,    HUSH,   False),
    ]
    bar_x, bar_w = 0.28, 0.62
    for j, (label, rate, color, em) in enumerate(bars):
        y = 0.74 - j * 0.18
        hed.text(0.0, y, label, fontsize=8, color=INK if em else SUBINK,
                 family="sans-serif",
                 weight="bold" if em else "normal", va="center")
        # rail
        hed.add_patch(Rectangle((bar_x, y - 0.02), bar_w, 0.04,
                                  facecolor=RULE, lw=0))
        # fill
        frac = (rate / scale_max) if scale_max else 0.0
        hed.add_patch(Rectangle((bar_x, y - 0.02), bar_w * frac, 0.04,
                                  facecolor=color, lw=0))
        # value
        hed.text(bar_x + bar_w + 0.02, y, f"{rate:.2f}",
                 fontsize=8, color=color, family="sans-serif",
                 weight="bold" if em else "normal", va="center")

    # ─── 7. Composition strip with section anchors ───
    strip = panel(0.560, 0.345, 0.385, 0.135)
    strip.text(0, 0.94, "COMPOSITION  (20 segments)",
               fontsize=8, color=accent, weight="bold", family="sans-serif")
    hline(strip, 0.90)

    segs = content.get("heatstrip") or []
    palette = {
        "safety":      "#B83228", "evals": "#3B6A8B",
        "risks":       "#8E5B2C", "mitigations": "#2D7A4E",
        "deployment":  "#6B5B8B", "other": "#D8D2C5",
    }
    if segs:
        seg_w = 1.0 / len(segs)
        for s in segs:
            color = palette.get(s["dominant"], palette["other"])
            strip.add_patch(Rectangle((s["index"] * seg_w, 0.42),
                                        seg_w * 0.96, 0.20,
                                        facecolor=color, lw=0))
    # Anchor labels — all above the strip, rotated for density
    for k, (seg_i, title) in enumerate(anchors[:4]):
        x = (seg_i + 0.5) / max(1, len(segs))
        strip.add_line(Line2D([x, x], [0.62, 0.70], color=SUBINK, lw=0.6))
        label = title.replace("&", "&").strip()[:24]
        strip.text(x, 0.74, label,
                   fontsize=6.4, color=INK, family="sans-serif",
                   ha="left", weight="bold", rotation=25,
                   rotation_mode="anchor")
    # Legend
    legend_items = [("safety", "safety"), ("evals", "evals"),
                    ("risks", "risks"), ("mitigations", "mitig"),
                    ("deployment", "deploy"), ("other", "other")]
    for j, (k, label) in enumerate(legend_items):
        x = j * 0.165
        strip.add_patch(Rectangle((x, 0.10), 0.018, 0.10,
                                    facecolor=palette[k], lw=0))
        strip.text(x + 0.024, 0.15, label, fontsize=6.2, color=SUBINK,
                   family="sans-serif", va="center")

    # ─── 8. What's new + safety posture ───
    wn = panel(0.055, 0.180, 0.890, 0.150)
    wn.text(0.0, 0.96, "WHAT'S NEW",
            fontsize=8, color=accent, weight="bold", family="sans-serif")
    wn.text(0.50, 0.96, "SAFETY POSTURE & DEPLOYMENT",
            fontsize=8, color=accent, weight="bold", family="sans-serif")
    hline(wn, 0.93, x0=0.0, x1=0.47)
    hline(wn, 0.93, x0=0.50, x1=1.0)

    def wrap(s, width):
        words = s.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > width:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur: lines.append(cur)
        return lines

    new_lines = wrap(whats_new or "Not disclosed in this document.", 56)[:6]
    for i, ln in enumerate(new_lines):
        wn.text(0.0, 0.86 - i * 0.13, ln,
                fontsize=8, color=INK, family="serif")

    # Combine mitigations+deployment into safety posture column
    posture = "  ".join(filter(None, [mitigations, deployment]))
    pos_lines = wrap(posture or "Not disclosed in this document.", 58)[:6]
    for i, ln in enumerate(pos_lines):
        wn.text(0.50, 0.86 - i * 0.13, ln,
                fontsize=8, color=INK, family="serif")

    # ─── 9. Footer ───
    foot = panel(0.055, 0.045, 0.890, 0.115)
    hline(foot, 1.0, color=RULE_STRONG, lw=0.8)
    foot.text(0, 0.85, "INTERPRETATION NOTES",
              fontsize=7.5, color=accent, weight="bold", family="sans-serif")
    notes = [
        f"• Canonical list = {len(CANONICAL)} cross-lab-comparable benchmarks (MMLU, GPQA, "
        f"HumanEval, SWE-bench, MATH, AIME, MMMU, HLE, MBPP, IFEval, BBH, LiveCodeBench).",
        "• Internal harness churn (Anthropic's Claude Code Dual-use, OpenAI's our_test_set_*, "
        "etc.) is excluded from canonical-dropped — those benchmarks are redesigned every release.",
        "• Deltas are vs the prior generation’s document; “not reported” ≠ “not evaluated.”",
        "• Hedge rate counts phrases per 1,000 words. Corpus = all 50 model_cards exposed by the API.",
    ]
    for i, ln in enumerate(notes):
        foot.text(0, 0.70 - i * 0.13, ln, fontsize=6.5, color=SUBINK,
                  family="sans-serif")
    foot.text(0, 0.08, f"Source · {doc.get('source_url', '')}",
              fontsize=6.0, color=SUBINK, family="sans-serif")
    foot.text(1.0, 0.08, "Model Card Explorer · Free Systems Lab · Stanford GSB",
              fontsize=6.0, color=SUBINK, family="sans-serif",
              style="italic", ha="right")

    png = out_stem.with_suffix(".png")
    pdf = out_stem.with_suffix(".pdf")
    fig.savefig(png, dpi=220, facecolor=PAPER)
    fig.savefig(pdf, facecolor=PAPER)
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")
    plt.close(fig)


# ───────────────────────────────── main ─────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-id", type=int, required=True)
    ap.add_argument("--vs-doc-id", type=int,
                    help="Doc id of prior generation; auto-detected if omitted")
    ap.add_argument("--out", type=str, required=True,
                    help="Output stem (.png + .pdf). Relative → charts/scorecards/.")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).parent / "scorecards" / out
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"┃ Fetching doc {args.doc_id}…")
    data = collect_for_doc(args.doc_id)
    doc, family, lab_slug = data["doc"], data["family"], data["lab_slug"]
    print(f"  doc:       {doc['title']}")
    print(f"  lab:       {doc['lab']['name']}")
    print(f"  words:     {data['content'].get('word_count')}")
    print(f"  evals:     {len(data['evals']['evals'])}")

    # ── Fetch every other gen's evals up front so we can both (a) pick the
    #    best comparator and (b) compute the canonical-dropped diff. ──
    all_prior_doc_ids = [g["document_id"] for g in family["generations"]
                         if g.get("document_id") and g["document_id"] != args.doc_id]
    print(f"┃ Fetching prior evals across {len(all_prior_doc_ids)} other gens in family…")
    prior_evals_map = fetch_evals_for_docs(all_prior_doc_ids)

    # ── Prior gen detection: pick the one whose evals best overlap canonical+this card ──
    if args.vs_doc_id:
        prior_doc_id = args.vs_doc_id
        prior_gen_label = next((g["name"] for g in family["generations"]
                                  if g.get("document_id") == prior_doc_id), f"doc {prior_doc_id}")
    else:
        this_canonical = set()
        canonical_aliases = set()
        for _, aliases in CANONICAL:
            canonical_aliases.update(aliases)
        for e in data["evals"]["evals"]:
            if e["benchmark"]["slug"] in canonical_aliases:
                this_canonical.add(e["benchmark"]["slug"])

        # Score each candidate by (# of canonical slugs they share with `this`)
        best_doc_id, best_score, best_name = None, -1, None
        for g in family["generations"]:
            did = g.get("document_id")
            if not did or did == args.doc_id:
                continue
            resp = prior_evals_map.get(did) or {}
            their_canonical = {e["benchmark"]["slug"] for e in resp.get("evals", [])
                               if e["benchmark"]["slug"] in canonical_aliases}
            overlap = len(this_canonical & their_canonical)
            if overlap > best_score:
                best_score = overlap
                best_doc_id = did
                best_name = g["name"]
        prior_doc_id = best_doc_id
        prior_gen_label = best_name
        if prior_doc_id:
            print(f"  prior gen: {prior_gen_label} (doc {prior_doc_id}, "
                  f"canonical overlap = {best_score})")
        else:
            print("  prior gen: (none found in family)")

    prior_evals_obj = []
    if prior_doc_id:
        prior_evals_obj = (prior_evals_map.get(prior_doc_id) or {}).get("evals", [])

    prior_evals_flat = []
    for did, resp in prior_evals_map.items():
        for e in resp.get("evals", []):
            prior_evals_flat.append({
                "slug": e["benchmark"]["slug"],
                "name": e["benchmark"]["name"],
            })

    data["prior_evals_obj"]  = prior_evals_obj
    data["prior_evals_flat"] = prior_evals_flat
    data["prior_gen_label"]  = prior_gen_label

    # ── Corpus-wide hedge stats (50 model_cards) ──
    print("┃ Fetching corpus content for hedge baseline…")
    docs_list = _fetch("/documents?limit=200")
    model_cards = [d for d in docs_list if d["doc_type"] == "model_card"]
    print(f"  corpus size: {len(model_cards)} model_cards")
    content_map = fetch_content_for_docs([d["id"] for d in model_cards])

    rates = []
    rates_by_lab = {}
    for d in model_cards:
        ct = content_map.get(d["id"])
        if not ct:
            continue
        wc = ct.get("word_count") or 0
        if wc < 100:
            continue
        rate = hedge_rate_per_1k(ct.get("content_md", ""), wc)
        rates.append(rate)
        lab = d["lab"]["slug"]
        rates_by_lab.setdefault(lab, []).append(rate)

    def avg(xs): return sum(xs) / len(xs) if xs else 0.0
    corpus_hedge_stats = {
        "global":  avg(rates),
        "max":     max(rates) if rates else 0.0,
        "per_lab": {k: avg(v) for k, v in rates_by_lab.items()},
        "n":       len(rates),
    }
    print(f"  corpus global hedge rate: {corpus_hedge_stats['global']:.2f}/1k")
    print(f"  this card hedge rate:     "
          f"{hedge_rate_per_1k(data['content'].get('content_md', ''), data['content'].get('word_count', 0)):.2f}/1k")

    print("┃ Rendering…")
    render(data, prior_doc_id, corpus_hedge_stats, out)


if __name__ == "__main__":
    main()
