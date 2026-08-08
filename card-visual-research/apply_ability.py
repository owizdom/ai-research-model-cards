#!/usr/bin/env python3
"""Put the ability line on every card front, from card.json.

The ability is the one claim a card's disclosure record can make that none of
its siblings can: "the longest model card published to this date", "zero
benchmark scores in any tracked documentation". It is a factual statement about
the record, not flavour text. Three cards shipped with one (claude-opus-4-7,
claude-opus-4-8, claude-sonnet-4-6) and Andy asked for it across the set.

There is no styling work here: `.ability` CSS is already inlined in all 50
cards, so this only injects markup. The block goes immediately after `.dex` in
the FRONT face, which is where the three reference cards put it.

Idempotent — an existing block is replaced, never appended to.

    python3 apply_ability.py                    # dry run, all cards
    python3 apply_ability.py --apply            # write
    python3 apply_ability.py --apply claude-4-6 # one card
    python3 apply_ability.py --seed abilities.json --apply   # load text into card.json first
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "cards"

# Matches an existing ability block so re-runs replace rather than stack.
ABILITY_RE = re.compile(r'<div class="ability">.*?</div>\s*</div>', re.S)
# The dex line is the anchor; the ability sits between it and the first attack.
DEX_RE = re.compile(r'(<div class="dex">.*?</div>)', re.S)


def block(name: str, text: str) -> str:
    return (
        '<div class="ability"><div class="head">'
        '<span class="tag">Ability</span>'
        f'<span class="nm">{html.escape(name)}</span></div>'
        f'<div class="ds">{html.escape(text)}</div></div>'
    )


def split_faces(doc: str):
    """Return (start, end) offsets of the front face, or None."""
    i = doc.find('<div class="face front">')
    j = doc.find('<div class="face back">')
    if i < 0:
        return None
    return i, (j if j > i else len(doc))


def card_html_path(d: Path, card: dict) -> Path | None:
    p = d / (card.get("html") or f"{d.name}.html")
    if p.exists():
        return p
    cand = [x for x in d.glob("*.html") if not x.name.startswith("print_")]
    return cand[0] if cand else None


def seed(path: Path, only: list[str], apply: bool) -> dict:
    """Merge authored ability text into each card.json.

    Returns the {slug: ability} overlay so a dry run can still preview the
    markup it would inject — otherwise --seed without --apply reports every
    card as missing, which is useless for checking the work before writing.
    """
    data = {k: v for k, v in json.loads(path.read_text()).items() if not k.startswith("_")}
    overlay, n = {}, 0
    for slug, ability in data.items():
        cj = next(CARDS.glob(f"*/{slug}/card.json"), None)
        if cj is None:
            print(f"  ?? no card dir for {slug}")
            continue
        if only and slug not in only:
            continue
        overlay[slug] = ability
        card = json.loads(cj.read_text())
        if card.get("ability") == ability:
            continue
        card["ability"] = ability
        if apply:
            cj.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")
        n += 1
    print(f"  {'seeded' if apply else 'would seed'} ability text into {n} card.json files")
    return overlay


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("slugs", nargs="*", help="Limit to these card dirs")
    p.add_argument("--apply", action="store_true", help="Write (default is a dry run)")
    p.add_argument("--seed", help="JSON of {slug: {name, text}} to merge into card.json first")
    a = p.parse_args(argv)

    overlay: dict = {}
    if a.seed:
        overlay = seed(Path(a.seed), a.slugs, a.apply)

    done = skipped = missing = 0
    for cj in sorted(CARDS.glob("*/*/card.json")):
        d = cj.parent
        if a.slugs and d.name not in a.slugs:
            continue
        card = json.loads(cj.read_text())
        ability = card.get("ability") or overlay.get(d.name)
        if not ability:
            # The two odd-schema cards carry their ability inline already.
            hp = card_html_path(d, card)
            if hp and '<div class="ability">' in hp.read_text():
                skipped += 1
            else:
                missing += 1
                print(f"  MISSING ability text: {d.name}")
            continue

        hp = card_html_path(d, card)
        if hp is None:
            print(f"  !! no source html in {d}")
            continue
        doc = hp.read_text()
        span = split_faces(doc)
        if span is None:
            print(f"  !! no front face in {hp.name}")
            continue
        i, j = span
        front, rest_before, rest_after = doc[i:j], doc[:i], doc[j:]

        new = block(ability["name"], ability["text"])
        if ABILITY_RE.search(front):
            front2 = ABILITY_RE.sub(new, front, count=1)
            action = "updated"
        else:
            m = DEX_RE.search(front)
            if not m:
                print(f"  !! no .dex anchor in {hp.name}, skipping")
                continue
            front2 = front[: m.end()] + "\n" + new + front[m.end() :]
            action = "added"
        if front2 == front:
            skipped += 1
            continue
        if a.apply:
            hp.write_text(rest_before + front2 + rest_after)
        done += 1
        print(f"  {action:7s} {d.name:24s} {ability['name']}")

    print(f"\n{done} card(s) {'written' if a.apply else 'would change'}, "
          f"{skipped} already current, {missing} still missing ability text")
    if not a.apply:
        print("dry run — re-run with --apply to write.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
