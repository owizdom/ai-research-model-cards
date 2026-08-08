#!/usr/bin/env python3
"""Derive every eval figure on a card from the corpus.

Word counts had a sync script and were 48/48 right. Everything else on the dex
strip and in the benchmark rows was hand-entered and had never been checked: 40
cards printed the wrong eval count, 38 the wrong lab-unique share, and 30
benchmark scores disagreed with the row they were supposedly measured from. The
lab-unique numbers in particular trended neatly upward with model recency, which
is a narrative rather than a measurement.

Definitions here are not guessed. They are the two that exactly reproduce the
six cards whose figures were independently verified by hand (grok-4, fable-5,
opus-5, sonnet-5, gpt-5.5, gpt-5.6):

    evals       every eval_results row for the card's document, scored or not
    lab-unique  share of that document's benchmarks no other lab reports

Benchmark rows print the corpus row *and name the variant*, because the deck's
own cover promises every figure is measured from the published document. A bare
"SWE-BENCH 80.2" next to a corpus row reading 18.4 pass@1 breaks that promise
even when both numbers are real: they are different measurements.

    python3 sync_eval_figures.py --check    # report, write nothing
    python3 sync_eval_figures.py            # apply, then rebuild html

Hand-read cards and the four with no safe corpus pairing are left alone.
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
EVALS_CSV = REPO / "data/dataset/eval_results.csv"

sys.path.insert(0, str(ROOT))
from build_card_html import dex_text  # noqa: E402  (handles manual-cardread)
from sync_word_counts import PAIR, UNMAPPED  # noqa: E402
import sync_roster  # noqa: E402

# Which benchmark to promote to the front of a card when the card's own choice
# is not in the document. Capability before safety, mirroring what the cards
# argue about.
CATEGORY_RANK = ["coding", "reasoning", "math", "knowledge", "agent", "vision",
                 "multimodal", "long_context", "instruction_following",
                 "multilingual", "medical", "general_knowledge", "safety", "other"]

ATK_RUN = re.compile(r'(<div class="atk">.*</div>)(?=\s*<div class="wrr">)', re.S)
BROW_RUN = re.compile(r'(<div class="brow">.*?</div>)(?=\s*</div>)', re.S)
DEX_RE = re.compile(r'(<div class="dex">)([^<]*)(</div>)')


def nb(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def show_score(row: dict) -> str:
    """Corpus scores arrive 0-1, 0-100 and raw (elo). Print them comparably."""
    try:
        v = float(row["score"])
    except (TypeError, ValueError):
        return str(row.get("score") or "—")
    if row.get("metric_path") == "elo" or v > 100:
        return f"{v:g}"
    if v <= 1.0:
        v *= 100
    return f"{v:.1f}"


def variant_label(row: dict, limit: int = 26) -> str:
    """Name the measurement. Cut on a comma, never mid-word: the raw variant
    "verified_hard, resolve_rate" clipped to 26 reads "verified_hard, resolve_rat"."""
    for k in ("variant", "split"):
        v = (row.get(k) or "").strip()
        if v and v not in ("-", "default"):
            if len(v) <= limit:
                return v
            cut = v[:limit]
            return cut[:cut.rindex(",")] if "," in cut else cut.rsplit(" ", 1)[0]
    mp = (row.get("metric_path") or "").strip()
    return (mp.replace("_", " ")[:limit]) if mp else "as reported"


def load_corpus():
    rows = list(csv.DictReader(open(EVALS_CSV)))
    by_doc = defaultdict(list)
    bench_labs = defaultdict(set)
    for r in rows:
        by_doc[r["document_slug"]].append(r)
        if r["benchmark_slug"]:
            bench_labs[r["benchmark_slug"]].add(r["lab_slug"])
    known = {r["slug"] for r in csv.DictReader(open(REPO / "data/dataset/documents.csv"))}
    return by_doc, bench_labs, known


def pick_rows(ev: list[dict]) -> list[dict]:
    """One row per benchmark: the plainest variant, then ranked by category."""
    best: dict[str, dict] = {}
    for r in ev:
        if not (r["score"] or "").strip() or not r["benchmark_name"]:
            continue
        key = nb(r["benchmark_name"])
        cur = best.get(key)
        rank = (0 if (r.get("variant") or "").strip() in ("", "default") else 1,
                len(r.get("variant") or ""))
        if cur is None or rank < cur["_rank"]:
            best[key] = {**r, "_rank": rank}
    out = list(best.values())
    out.sort(key=lambda r: (CATEGORY_RANK.index(r["benchmark_category"])
                            if r["benchmark_category"] in CATEGORY_RANK else 99,
                            r["benchmark_name"].lower()))
    return out


def choose(card: dict, rows: list[dict], n: int) -> list[dict | None]:
    """Keep the card's own benchmarks where the document has them, then fill."""
    taken, out = set(), []
    existing = [b.get("n") for b in (card.get("benches") or [])]
    for want in existing[:n]:
        k = nb(want)
        hit = next((r for r in rows
                    if nb(r["benchmark_name"]) not in taken
                    and (nb(r["benchmark_name"]) == k
                         or nb(r["benchmark_name"]).startswith(k)
                         or k.startswith(nb(r["benchmark_name"])))), None)
        if hit:
            taken.add(nb(hit["benchmark_name"]))
            out.append(hit)
        else:
            out.append(None)                       # keep the slot, mark unreported
    for r in rows:
        if len(out) >= n:
            break
        if nb(r["benchmark_name"]) not in taken:
            taken.add(nb(r["benchmark_name"]))
            out.append(r)
    while len(out) < n:
        out.append(None)
    # a real row beats an empty slot
    out.sort(key=lambda r: r is None)
    return out[:n]


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def sparks(n: int) -> str:
    return "".join('<span class="e"></span>' for _ in range(max(1, min(int(n or 1), 4))))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)

    by_doc, bench_labs, known_docs = load_corpus()
    dirs = sync_roster.card_dirs()
    changed, skipped, rebuild = [], [], []

    for slug in sync_roster.read_roster():
        d = dirs[slug]
        card = json.loads((d / "card.json").read_text())
        doc = PAIR.get(slug)
        if card.get("source") == "manual-cardread":
            skipped.append((slug, "hand-read")); continue
        if slug in UNMAPPED:
            skipped.append((slug, "no corpus pairing")); continue
        if not doc or doc not in known_docs:
            skipped.append((slug, "no corpus document")); continue

        # A document with zero eval rows is a finding, not a gap to skip. Mistral
        # 7B is the 745-word card the cover calls the shortest in the set, and it
        # was printing three benchmark scores the document never reported.
        ev = by_doc.get(doc, [])
        deltas = []

        n_ev = str(len(ev))
        if str(card.get("evals")) != n_ev:
            deltas.append(("evals", card.get("evals"), n_ev))

        bs = {r["benchmark_slug"] for r in ev if r["benchmark_slug"]}
        uq = f"{round(100 * sum(1 for b in bs if len(bench_labs[b]) == 1) / len(bs))}%" if bs else "—"
        if str(card.get("unique")) != uq:
            deltas.append(("lab-unique", card.get("unique"), uq))

        rows = pick_rows(ev)
        picked = choose(card, rows, 3)
        new_benches = []
        for i, r in enumerate(picked):
            old = (card.get("benches") or [{}] * 3)[i] if i < len(card.get("benches") or []) else {}
            if r is None:
                new_benches.append({"n": old.get("n") or "—", "d": "not reported",
                                    "s": "—", **({"cost": old["cost"]} if "cost" in old else {})})
            else:
                new_benches.append({"n": r["benchmark_name"].upper(), "d": variant_label(r),
                                    "s": show_score(r),
                                    **({"cost": old["cost"]} if "cost" in old else {})})
        if new_benches != card.get("benches"):
            deltas.append(("benches", None, None))

        n_btbl = max(3, min(5, len(card.get("btbl") or [])))
        new_btbl = []
        for r in choose(card, rows, n_btbl):
            if r is None:
                new_btbl.append({"n": "Not reported", "s": "—", "l": "—"})
            else:
                labs = len(bench_labs.get(r["benchmark_slug"], ()))
                new_btbl.append({"n": r["benchmark_name"], "s": show_score(r),
                                 "l": f"{labs} lab{'s' if labs != 1 else ''}"})
        if new_btbl != card.get("btbl"):
            deltas.append(("btbl", None, None))

        if not deltas:
            continue
        changed.append((slug, deltas))
        if a.check:
            continue

        card["evals"], card["unique"] = n_ev, uq
        card["benches"], card["btbl"] = new_benches, new_btbl
        (d / "card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")

        if card.get("generated"):
            rebuild.append(slug)
            continue

        hp = d / (card.get("html") or f"{slug}.html")
        if not hp.exists():
            cand = [x for x in d.glob("*.html") if not x.name.startswith("print_")]
            if not cand:
                print(f"  ! {slug}: no source html"); continue
            hp = cand[0]
        html = hp.read_text()

        atk = "".join(
            f'<div class="atk"><div class="cost">{sparks(b.get("cost", 3 - i))}</div>'
            f'<div class="mid"><div class="nm">{esc(b["n"])}</div>'
            f'<div class=ds>{esc(b["d"])}</div></div>'
            f'<div class="dmg">{esc(b["s"])}</div></div>'
            for i, b in enumerate(new_benches))
        brow = "".join(
            f'<div class="brow"><span class="bn">{esc(b["n"])}</span>'
            f'<span class="bs">{esc(b["s"])}</span>'
            f'<span class="bl">{esc(b["l"])}</span></div>'
            for b in new_btbl)

        html2, n1 = ATK_RUN.subn(lambda m: atk, html, count=1)
        html2, n2 = BROW_RUN.subn(lambda m: brow, html2, count=1)
        html2, n3 = DEX_RE.subn(lambda m: m.group(1) + esc(dex_text(card)) + m.group(3),
                                html2, count=1)
        if not (n1 and n2 and n3):
            print(f"  ! {slug}: patched atk={n1} brow={n2} dex={n3} (expected 1 each)")
        hp.write_text(html2)

    for slug, deltas in changed:
        bits = ", ".join(f"{k} {was}->{now}" if was is not None else k
                         for k, was, now in deltas)
        print(f"  {slug:<24} {bits}")

    if rebuild and not a.check:
        subprocess.run([sys.executable, "build_card_html.py", *rebuild],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        print(f"  rebuilt {len(rebuild)} generated card(s)")

    print(f"\n{'would change' if a.check else 'changed'} {len(changed)} card(s); "
          f"left alone {len(skipped)}")
    for slug, why in skipped:
        print(f"    {slug:<22} {why}")
    if not a.check:
        print("\nnext: python3 build_print.py --jobs=2 && python3 build_export.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
