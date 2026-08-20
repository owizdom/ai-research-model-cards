#!/usr/bin/env python3
"""Rebuild cards/index.html from the live card files.

The gallery inlines its own copy of every card face, so it silently goes stale
the moment a card changes. It sat at its 12 Jun state through the whole ability
rollout and showed zero ability blocks, which made finished work look missing.
Nothing should hand-edit it again — regenerate it instead.

Cards are ordered by `card.json.num`, so the page reads in set order.

    python3 build_gallery.py            # dry run, reports what would change
    python3 build_gallery.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from build_print import CARDS, parse_card   # same extraction the print path uses

ROOT = Path(__file__).resolve().parent
OUT = CARDS / "index.html"

# The only CSS the gallery adds on top of a card's own inlined stylesheet.
GALLERY_CSS = """
body{display:block!important;padding:34px 20px 70px}
.hdr{text-align:center;font-family:'Cinzel',serif;font-size:27px;color:#f0ddb0;letter-spacing:.04em}
.sub{text-align:center;font-family:'JetBrains Mono',monospace;font-size:11px;color:#9a7a50;letter-spacing:.12em;margin:6px 0 30px}
.setgrid{display:flex;flex-wrap:wrap;gap:36px;justify-content:center;max-width:1660px;margin:0 auto}
.setgrid .cardwrap{width:480px}
.setgrid .flipper{height:702px}
.setgrid .face{position:absolute;inset:0}
.setgrid .tcg{height:100%}.setgrid .gold{height:100%}.setgrid .inner{height:100%}
"""


def rules(css: str) -> list[tuple[str, str]]:
    """(selector, body) pairs. Comments stripped; at-rules skipped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        sel = sel.strip()
        if sel and not sel.startswith("@"):
            out.append((sel, body.strip()))
    return out


def scoped_delta(base: str, card: str, anchor_id: str) -> list[str]:
    """Rules this card has that the shared stylesheet does not, scoped to it."""
    if card == base:
        return []
    have = set(rules(base))
    out = []
    for sel, body in rules(card):
        if (sel, body) in have:
            continue
        scoped = ",".join(f"#{anchor_id} {part.strip()}" for part in sel.split(","))
        out.append(f"{scoped}{{{body}}}")
    return out


def sort_key(card: dict, slug: str):
    """Set order. Cards without a number (the two bonus cards) sort last."""
    num = (card.get("num") or "").split("/")[0]
    return (0, int(num)) if num.isdigit() else (1, 0), slug


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--apply", action="store_true")
    a = p.parse_args(argv)

    # Follow the roster, not the directory. A card can sit in cards/ without
    # being in the set (dropped from the deck but kept on disk), and globbing
    # would quietly put it back on the page.
    import sync_roster
    in_set = set(sync_roster.read_roster())

    entries, style, links, extra_css = [], None, None, []
    for cj in sorted(CARDS.glob("*/*/card.json")):
        d = cj.parent
        if d.parent.name != "_pack" and d.name not in in_set:
            continue
        card = json.loads(cj.read_text())
        hp = d / (card.get("html") or f"{d.name}.html")
        if not hp.exists():
            cand = [x for x in d.glob("*.html") if not x.name.startswith("print_")]
            if not cand:
                print(f"  !! no source html for {d.name}")
                continue
            hp = cand[0]
        try:
            s, l, faces, _ = parse_card(hp)
        except ValueError as e:
            print(f"  !! {d.name}: {e}")
            continue
        if style is None:
            style, links = s, l
        # A card may tune its own stylesheet (le-chaton-fat anchors its art
        # crop so the ears survive). The gallery used the FIRST card's style
        # for every card, so those overrides silently vanished here while
        # working fine in print. Carry each card's delta, scoped to it.
        extra_css.extend(scoped_delta(style, s, f"c-{d.name}"))

        # Art paths are relative to the card dir; the gallery sits one level up.
        prefix = f"{d.parent.name}/{d.name}/"
        front = re.sub(r'src="art/', f'src="{prefix}art/', faces["front"])
        back = re.sub(r'src="art/', f'src="{prefix}art/', faces["back"])
        entries.append((sort_key(card, d.name), d.name,
                        f'<div class="cardwrap" id="c-{d.name}">'
                        f'<div class="flipper">{front}{back}</div></div>'))

    entries.sort(key=lambda e: e[0])
    body = "\n".join(e[2] for e in entries)
    n = len(entries)
    doc = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Model Cards — full set</title>"
        + (links or "")
        + "<style>" + (style or "") + GALLERY_CSS + "".join(extra_css)
        + "</style></head><body>"
        + '<div class="hdr">Model Cards — full set</div>'
        + f'<div class="sub">{n} cards · per-lab colors · hover to flip</div>'
        + f'<div class="setgrid">{body}</div>'
        + "</body></html>"
    )

    old = OUT.read_text() if OUT.exists() else ""
    with_ability = doc.count('class="ability"')
    print(f"  {n} cards, {with_ability} ability blocks "
          f"(was {old.count('class=\"ability\"')} in the file on disk)")
    print(f"  size {len(doc):,} bytes (was {len(old):,})")
    if a.apply:
        OUT.write_text(doc)
        print(f"  wrote {OUT}")
    else:
        print("  dry run — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
