#!/usr/bin/env python3
"""Print only what a card's own document actually reports.

Two layers were wrong before this. The cards carried headline capability numbers
(Claude 4 Opus "SWE-BENCH 79.4", "GPQA 83.1", "MMLU 88.5") that appear nowhere in
the Claude 4 system card -- that document is a safety document reporting Cyber
CTF, StrongREJECT, BBQ, prompt injection, METR and ASL-3 autonomy, and mentions
SWE-bench only as a hard-subset autonomy figure. Those numbers came off a launch
blog. Then eval_results.csv, used to replace them, had its own defects: it labels
Claude 3's *Multilingual* MMLU row (79.1) as plain "MMLU", and attributes every
row of a family report to one model, so Sonnet and Haiku inherited Opus's scores.

So neither the old cards nor the corpus is trusted here. Every row printed must
survive a check against the document text itself:

  1. the score string occurs in the document
  2. the benchmark label is read back *out of the document* at that point, so a
     qualifier the corpus dropped ("Multilingual", "hard subset") comes back
  3. the row belongs to this model, not a sibling in the same family report

Anything that fails is printed as "not reported", which is the honest answer and
the claim the deck exists to make.

    python3 derive_from_source.py --report   # what survives, per card
    python3 derive_from_source.py            # apply
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CACHE = REPO / "charts/data/article data/_card_text_cache"

sys.path.insert(0, str(ROOT))
from build_card_html import dex_text  # noqa: E402
from sync_word_counts import PAIR, UNMAPPED  # noqa: E402
import sync_roster  # noqa: E402

# Qualifiers that change what a benchmark measures. If one sits in front of the
# name in the document, it belongs on the card.
QUALIFIERS = ["multilingual", "hard subset", "verified", "diamond", "pro",
              "0-shot", "5-shot", "25-shot", "10-shot", "3-shot", "maj@32", "cot"]

# Family reports document several models in one table. The corpus flattens them
# onto whichever model it saw first, so these are read out of the source by hand.
# Column order is taken from the table header in the cached text.
HAND_READ: dict[str, dict[str, tuple[str, str]]] = {
    # card slug -> {benchmark: (score, label as printed in the document)}
    # anthropic_model_card Table 1, columns: Opus | Sonnet | Haiku | GPT-4 | ...
    "claude-3-opus":   {"MMLU": ("86.8", "5-shot"), "HUMANEVAL": ("84.9", "0-shot"),
                        "GPQA": ("50.4", "Diamond, 0-shot CoT")},
    "claude-3-sonnet": {"MMLU": ("79.0", "5-shot"), "HUMANEVAL": ("73.0", "0-shot"),
                        "GPQA": ("40.4", "Diamond, 0-shot CoT")},
    "claude-3-haiku":  {"MMLU": ("75.2", "5-shot"), "HUMANEVAL": ("75.9", "0-shot"),
                        "GPQA": ("33.3", "Diamond, 0-shot CoT")},
    # anthropic_fable5_card documents TWO models and its header reads
    #   Mythos 5 | Fable 5 | Mythos Preview | Opus 4.8 | GPT-5.5 | Gemini 3.1 Pro
    # so Fable 5 is column ONE, not zero. Column zero is Mythos 5, and the prose
    # says it outright: "Mythos 5 achieved 95.5% and Fable 5 achieved 95%".
    "claude-fable-5":  {"SWE-BENCH VERIFIED": ("95", "Verified"),
                        "SWE-BENCH PRO": ("80", "Pro"),
                        "TERMINAL-BENCH 2.1": ("84.3", "as reported")},
    # anthropic_opus5_card. Both of the card's old figures were the flattering
    # secondary metric: the document says an 11.7% all-pass rate alongside the
    # 94.1% mean criterion-pass rate on LAB, and an 85.8% pass rate alongside
    # 89.1% mean claim coverage on MCP Atlas. ARC-AGI "100" is in no table; the
    # ARC Prize Foundation reports 97.50% on ARC-AGI-1 at max effort.
    "claude-opus-5":   {"ARC-AGI-1": ("97.50", "max effort, semi-private"),
                        "LEGAL AGENT BENCH": ("11.7", "all-pass rate"),
                        "MCP ATLAS": ("85.8", "pass rate")},
}

ATK_RUN = re.compile(r'(<div class="atk">.*</div>)(?=\s*<div class="wrr">)', re.S)
BROW_RUN = re.compile(r'(<div class="brow">.*?</div>)(?=\s*</div>)', re.S)
DEX_RE = re.compile(r'(<div class="dex">)([^<]*)(</div>)')


def nb(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sparks(n: int) -> str:
    return "".join('<span class="e"></span>' for _ in range(max(1, min(int(n or 1), 4))))


def score_variants(raw: str) -> list[str]:
    """How the same score can be written in the document.

    The corpus has transformed some of these on the way in: a 0.7865 fraction is
    stored as 78.64999999999999, and 23.0 is written "23" in prose. Matching the
    stored string exactly finds neither.
    """
    out = {raw.strip()}
    try:
        v = float(raw)
    except ValueError:
        return list(out)
    for cand in (v, v * 100, v / 100):
        for fmt in (f"{cand:g}", f"{cand:.1f}", f"{cand:.2f}"):
            # A rendering that distorts the value is not the same number:
            # 95.5/100 formatted "%.1f" is "1.0", which matches almost any table.
            if abs(float(fmt) - cand) < 0.005:
                out.add(fmt)
    return [x for x in out if x]


def shorten(s: str, n: int) -> str:
    """Never cut mid-word: "LONG-FORM VIROLOGY TAS" is not a benchmark."""
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip(" ,:-")


def label_from_document(text: str, name: str, score: str):
    """Read the label AND the printed form back out of the document.

    Returns (label, score_as_written). The card prints the second value, so the
    number on the card is literally a string present in the source. This is what
    keeps a BBQ bias score of -0.60 from being rendered "-60.0" by a percentage
    assumption that does not apply to it.
    """
    for s in score_variants(score):
        for m in re.finditer(rf"(?<![\d.]){re.escape(s)}(?![\d])", text):
            win = text[max(0, m.start() - 190):m.start()].lower()
            if nb(name) and nb(name) not in nb(win):
                continue
            pre = win[max(0, len(win) - 60):]
            quals = [q for q in QUALIFIERS if q in pre]
            return (", ".join(quals[:2]) if quals else "as reported"), s
    return None, None


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--report", action="store_true")
    a = p.parse_args(argv)

    rows = list(csv.DictReader(open(REPO / "data/dataset/eval_results.csv")))
    by_doc = defaultdict(list)
    bench_labs = defaultdict(set)
    for r in rows:
        by_doc[r["document_slug"]].append(r)
        if r["benchmark_slug"]:
            bench_labs[r["benchmark_slug"]].add(r["lab_slug"])

    have = {p_.stem: p_ for p_ in CACHE.glob("*.md")}
    dirs = sync_roster.card_dirs()
    kept = dropped = 0
    changed, no_text = [], []

    for slug in sync_roster.read_roster():
        d = dirs[slug]
        card = json.loads((d / "card.json").read_text())
        if card.get("source") == "manual-cardread" or slug in UNMAPPED:
            continue
        doc = PAIR.get(slug)
        if not doc:
            continue
        if doc not in have:
            no_text.append((slug, doc))
            continue
        text = have[doc].read_text()

        verified: list[tuple[str, str, str, int]] = []      # name, label, score, labs

        for bm, (sc, lab) in HAND_READ.get(slug, {}).items():
            if re.search(rf"(?<![\d.]){re.escape(sc)}(?![\d])", text):
                verified.append((bm, lab, sc, 0))
                kept += 1

        if slug not in HAND_READ:
            seen = set()
            for r in by_doc.get(doc, []):
                sc = (r["score"] or "").strip()
                nm_ = r["benchmark_name"]
                if not sc or not nm_ or nb(nm_) in seen:
                    continue
                lab, as_written = label_from_document(text, nm_, sc)
                if lab is None:
                    dropped += 1
                    continue
                seen.add(nb(nm_))
                verified.append((nm_, lab, as_written,
                                 len(bench_labs.get(r["benchmark_slug"], ()))))
                kept += 1

        old_b = card.get("benches") or []
        new_b, new_t = [], []
        for i in range(3):
            if i < len(verified):
                n_, lab, sc, _ = verified[i]
                new_b.append({"n": shorten(n_.upper(), 22), "d": shorten(lab, 26), "s": sc,
                              **({"cost": old_b[i]["cost"]} if i < len(old_b) and "cost" in old_b[i] else {})})
            else:
                keep = old_b[i]["n"] if i < len(old_b) else "—"
                new_b.append({"n": keep, "d": "not reported", "s": "—",
                              **({"cost": old_b[i]["cost"]} if i < len(old_b) and "cost" in old_b[i] else {})})
        for i in range(max(3, min(5, len(card.get("btbl") or [])))):
            if i < len(verified):
                n_, lab, sc, labs = verified[i]
                new_t.append({"n": shorten(n_, 26), "s": sc,
                              "l": f"{labs} lab{'s' if labs != 1 else ''}" if labs else "—"})
            else:
                new_t.append({"n": "Not reported", "s": "—", "l": "—"})

        if new_b == card.get("benches") and new_t == card.get("btbl"):
            continue
        changed.append((slug, len(verified), [b["n"] for b in new_b]))
        if a.report:
            continue

        card["benches"], card["btbl"] = new_b, new_t
        (d / "card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")

        if card.get("generated"):
            continue
        hp = d / (card.get("html") or f"{slug}.html")
        if not hp.exists():
            cand = [x for x in d.glob("*.html") if not x.name.startswith("print_")]
            if not cand:
                continue
            hp = cand[0]
        html = hp.read_text()
        atk = "".join(
            f'<div class="atk"><div class="cost">{sparks(b.get("cost", 3 - i))}</div>'
            f'<div class="mid"><div class="nm">{esc(b["n"])}</div>'
            f'<div class=ds>{esc(b["d"])}</div></div>'
            f'<div class="dmg">{esc(b["s"])}</div></div>' for i, b in enumerate(new_b))
        brow = "".join(
            f'<div class="brow"><span class="bn">{esc(b["n"])}</span>'
            f'<span class="bs">{esc(b["s"])}</span>'
            f'<span class="bl">{esc(b["l"])}</span></div>' for b in new_t)
        html = ATK_RUN.sub(lambda m: atk, html, count=1)
        html = BROW_RUN.sub(lambda m: brow, html, count=1)
        html = DEX_RE.sub(lambda m: m.group(1) + esc(dex_text(card)) + m.group(3), html, count=1)
        hp.write_text(html)

    gen = [s for s, _, _ in changed
           if json.loads((dirs[s] / "card.json").read_text()).get("generated")]
    if gen and not a.report:
        subprocess.run([sys.executable, "build_card_html.py", *gen],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)

    for slug, n, names in changed:
        print(f"  {slug:<24} {n} row(s) survived the document  {names}")
    print(f"\nrows verified against the document text: {kept}")
    print(f"rows dropped (score not in the document): {dropped}")
    print(f"{'would change' if a.report else 'changed'}: {len(changed)} cards")
    if no_text:
        print(f"\nno cached document text ({len(no_text)}), left untouched:")
        for s, doc in no_text:
            print(f"    {s:<22} {doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
