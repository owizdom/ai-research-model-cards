#!/usr/bin/env python3
"""Rebuild the dex strip on each card front from card.json.

The dex strip reads:  NO. 041 · 3.5k words · 24 evals · 62% lab-unique

Patching it with regexes was a mistake and produced silent failures: word
boundaries do not match values that start with "<" or end with "%", so the grok
cards kept rendering "<5k words" and "0% lab-unique" long after card.json had
been corrected, and a substring check ("3k" in "&lt;3k") hid one of them from
the audit too. Rebuilding the whole strip from card.json removes that class of
bug entirely — there is nothing left to partially match.

Only touches main-schema cards (the ones with a `benches` array). The two
odd-schema cards carry a different dex and are left alone.

    python3 sync_dex.py           # dry run
    python3 sync_dex.py --apply
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEX_RE = re.compile(r'(<div class="dex">)([^<]*)(</div>)')


def dex_text(card: dict) -> str:
    num = (card.get("num") or "").split("/")[0] or "000"
    return (f"NO. {num} · {card.get('words','?')} words · "
            f"{card.get('evals','?')} evals · {card.get('unique','?')} lab-unique")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("slugs", nargs="*")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args(argv)

    changed = same = 0
    for cj in sorted(glob.glob(str(ROOT / "cards/*/*/card.json"))):
        cjp = Path(cj)
        d = cjp.parent
        if a.slugs and d.name not in a.slugs:
            continue
        card = json.loads(cjp.read_text())
        if "benches" not in card:
            continue
        hp = d / (card.get("html") or f"{d.name}.html")
        if not hp.exists():
            continue

        doc = hp.read_text()
        m = DEX_RE.search(doc)
        if not m:
            print(f"  !! no dex strip in {hp.name}")
            continue
        want = html.escape(dex_text(card), quote=False)
        if m.group(2) == want:
            same += 1
            continue
        if a.apply:
            hp.write_text(doc[: m.start(2)] + want + doc[m.end(2) :])
        changed += 1
        print(f"  {d.name:22s} {m.group(2)[:52]}")
        print(f"  {'':22s} -> {want[:52]}")

    print(f"\n  {changed} dex strip(s) {'rebuilt' if a.apply else 'would change'}, {same} already correct")
    if not a.apply:
        print("  dry run — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
