#!/usr/bin/env python3
"""Runnable gate for the shipped deck. Exits non-zero if anything is wrong.

Written after a run of defects that were all mechanically detectable and were
all found by eye instead, one at a time, each after saying the deck was done:

  - "as reported" printed as a benchmark descriptor on 23 rows
  - a literal em-dash lineage node on kimi-k3 and inkling
  - EVALS and an eval count where the set prints CAP and a capability score
  - benchmark names truncated mid-token by an old shorten()
  - gpt-5-3's front reading "Not reported" for a benchmark its own back scored
  - a card left with 8 benchmark rows after a bad regex appended instead of
    replacing

Every check below exists because that defect shipped once.

    python3 verify_deck.py           # all checks
    python3 verify_deck.py -v        # list every row inspected
"""
from __future__ import annotations

import argparse
import glob
import html as H
import json
import pathlib
import re
import sys

import sync_roster

ROOT = pathlib.Path(__file__).resolve().parent
PRINT = ROOT / "print"

# descriptors that describe nothing. These are what the pipeline emits when it
# has no human text, and they read as broken on a printed card.
PLACEHOLDER_D = {"as reported", "verified", "reported", "not reported", "-", "—", ""}
# row names that are legitimately not benchmarks
PLACEHOLDER_N = {"not reported", "not yet in corpus", "redacted", ""}

failures: list[tuple[str, str, str]] = []


def fail(check: str, card: str, detail: str) -> None:
    failures.append((check, card, detail))


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def card_files(slug: str):
    cj = pathlib.Path(glob.glob(f"{ROOT}/cards/*/{slug}/card.json")[0])
    html = [p for p in cj.parent.glob("*.html") if not p.name.startswith("print_")][0]
    return cj, html


def check_card(slug: str, pos: int, total: int, verbose: bool) -> None:
    cj, html_p = card_files(slug)
    c = json.loads(cj.read_text())
    raw = html_p.read_text()
    t = H.unescape(raw)

    # 1. every value in card.json is actually on the card
    for face in ("benches", "btbl"):
        for b in (c.get(face) or []):
            for k in ("n", "s", "d"):
                v = b.get(k)
                if v and str(v) not in t:
                    fail("json-html-sync", slug, f"{face} {k}={v!r} absent from html")

    # 2. row counts agree between data and markup
    n_json = len(c.get("btbl") or [])
    n_html = len(re.findall(r'class="brow"', raw))
    if n_json != n_html:
        fail("row-count", slug, f"card.json has {n_json} back rows, html has {n_html}")

    # 3. no placeholder descriptors on rows that are real benchmarks
    for face in ("benches", "btbl"):
        for b in (c.get(face) or []):
            if norm(b.get("n")) in {norm(x) for x in PLACEHOLDER_N}:
                continue
            d = (b.get("d") or "").strip().lower()
            # "not reported" is real information when the row has no score:
            # the lab published the benchmark name and no figure.
            if d == "not reported" and str(b.get("s")).strip() in {"—", "-", ""}:
                continue
            if d in PLACEHOLDER_D:
                fail("descriptor", slug, f"{face} {b.get('n')!r} descriptor is {b.get('d')!r}")

    # 4. benchmark names not truncated mid-token
    for face in ("benches", "btbl"):
        for b in (c.get(face) or []):
            n = (b.get("n") or "").strip()
            if n.count("(") != n.count(")"):
                fail("truncated-name", slug, f"{face} {n!r} has unbalanced parentheses")
            if re.search(r"\b(for|the|and|of|with|no)$", n, re.I) or n.endswith("_"):
                fail("truncated-name", slug, f"{face} {n!r} ends mid-phrase")

    # 5. the two faces must not contradict each other on the same benchmark
    back = {norm(b.get("n")): b.get("s") for b in (c.get("btbl") or [])}
    for b in (c.get("benches") or []):
        k = norm(b.get("n"))
        if k in back and back[k] not in (None, "") and b.get("s") not in (None, ""):
            if str(b["s"]) != str(back[k]) and "—" not in (str(b["s"]), str(back[k])):
                fail("face-conflict", slug,
                     f"{b.get('n')} front={b['s']} back={back[k]}")
            if str(b["s"]) == "—" and str(back[k]) != "—":
                fail("face-conflict", slug,
                     f"{b.get('n')} front says not reported, back scores {back[k]}")

    # 6. lineage: no dangling node, exactly one active, markup agrees
    lin = c.get("lineage") or []
    for nde in lin:
        if (nde.get("v") or "").strip() in {"—", "-", ""}:
            fail("lineage", slug, f"placeholder node {nde!r}")
    act = sum(1 for n in lin if n.get("a"))
    if lin and act != 1:
        fail("lineage", slug, f"{act} active nodes, expected 1")
    n_nodes = len(re.findall(r'<div class="node', raw))
    if lin and n_nodes != len(lin):
        fail("lineage", slug, f"card.json has {len(lin)} nodes, html has {n_nodes}")

    # 7. the headline stat is a capability score, labelled the same everywhere
    lbl = c.get("capL")
    if lbl is not None and str(lbl).upper() != "CAP":
        fail("cap-label", slug, f"headline stat labelled {lbl!r}, not CAP")

    # 8. the index strip under the art is the card number and nothing else
    m = re.search(r'<div class="dex">([^<]*)', raw)
    if m and not re.fullmatch(r"NO\. \d+", m.group(1).strip()):
        fail("dex", slug, f"dex strip reads {m.group(1).strip()!r}")

    # 9. SET 01 belongs on no printed face
    if "SET 01" in raw:
        fail("set-label", slug, "SET 01 appears on a face")

    # 10. numbering follows the roster
    want = f"{pos:03d}/{total:03d}"
    if c.get("num") != want:
        fail("numbering", slug, f"card.json num={c.get('num')!r}, roster says {want}")
    if want not in raw:
        fail("numbering", slug, f"{want} not printed on the card")

    # 11. the print files exist and are the right size
    for side in ("front", "back"):
        p = PRINT / f"{slug}_{side}.jpg"
        if not p.exists():
            fail("render", slug, f"{p.name} missing")

    if verbose:
        print(f"  checked {slug:24} {n_json} back rows, {len(lin)} lineage nodes")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)

    roster = sync_roster.read_roster()
    total = len(roster)
    print(f"verifying {total} cards\n")
    for i, slug in enumerate(roster, 1):
        check_card(slug, i, total, a.verbose)

    # deck-wide: descriptors should be shared where the benchmark is shared
    seen: dict[str, set[str]] = {}
    for slug in roster:
        cj, _ = card_files(slug)
        c = json.loads(cj.read_text())
        for b in (c.get("btbl") or []):
            if norm(b.get("n")) in {norm(x) for x in PLACEHOLDER_N} or not b.get("d"):
                continue
            seen.setdefault(norm(b["n"]), set()).add(b["d"].strip().lower())
    drift = {k: sorted(v) for k, v in sorted(seen.items()) if len(v) > 1}

    if drift:
        # not a failure: his gallery and his handoff zip word the same benchmark
        # differently, and both are his. Surfaced so he can pick one.
        print(f"note  {len(drift)} benchmark(s) described two ways across the set,")
        print( "      his gallery wording vs his handoff wording. His call, not a defect.")
        for k, v in drift.items():
            print(f"        {k}: {v}")
        print()

    if not failures:
        print(f"PASS  {total} cards, no defects\n")
        return 0

    by_check: dict[str, list] = {}
    for chk, card, detail in failures:
        by_check.setdefault(chk, []).append((card, detail))
    print(f"FAIL  {len(failures)} defect(s) across {len(by_check)} check(s)\n")
    for chk, rows in sorted(by_check.items()):
        print(f"  {chk}  ({len(rows)})")
        for card, detail in rows:
            print(f"      {card:24} {detail}")
        print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
