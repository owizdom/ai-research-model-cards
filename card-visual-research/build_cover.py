#!/usr/bin/env python3
"""Build the Free Systems pack cover card.

A cover at the same 816x1110 spec as every other card, so it rides the same MPC
order and inherits the bleed layers, the floating frame and check_bleed.py from
build_print.py. Wordmark is set in type (Jost + the deck's gold treatment)
because no Free Systems logo asset exists.

The shared card stylesheet is lifted from an existing card rather than copied by
hand, so the cover cannot drift from the set.

    python3 build_cover.py            # writes the html
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CARDS = ROOT / "cards"
DEST = CARDS / "_pack" / "free-systems-cover"
STYLE_SRC = CARDS / "anthropic" / "claude-2" / "claude-2.html"

COVER_CSS = """
/* ---- pack cover only ---------------------------------------------------- */
.lab-freesystems{--t1:#e8c87a;--t2:#c9962f;--t3:#8a6414;--spark:#d8a63a}
.cover{display:flex;flex-direction:column;align-items:center;text-align:center;
  padding:26px 22px 20px!important}
.cover .wordmark{font-family:'Cinzel',serif;font-size:38px;font-weight:700;
  letter-spacing:.10em;line-height:1.02;
  background:linear-gradient(178deg,#fff4d0 0%,var(--gold) 34%,#c9962f 68%,#8a6414 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  text-shadow:0 1px 0 rgba(255,255,255,.25)}
.cover .rule{width:70%;height:2px;margin:9px 0 7px;
  background:linear-gradient(90deg,transparent,var(--gold2),transparent)}
.cover .kicker{font-family:'JetBrains Mono',monospace;font-size:12.5px;font-weight:600;
  letter-spacing:.34em;color:var(--ink2);text-indent:.34em}
.cover .art{margin-top:13px;width:100%;flex:1 1 auto;display:flex}
.cover .art-win{flex:1 1 auto;height:auto;min-height:200px}
.cover .art-win img{object-position:50% 30%}
.cover .setline{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;
  letter-spacing:.2em;color:var(--ink2);margin-top:13px}
.cover .site{font-family:'JetBrains Mono',monospace;font-size:9.5px;
  letter-spacing:.14em;color:var(--ink3);margin-top:5px}
.cover .sparkrow{display:flex;gap:7px;justify-content:center;margin-top:11px}

/* ---- cover back: the set list ------------------------------------------- */
.coverback .wordmark{font-size:26px}
.coverback .setlist{columns:3;column-gap:11px;width:100%;margin-top:11px;text-align:left}
.coverback .setlist div{font-family:'JetBrains Mono',monospace;font-size:7.6px;line-height:1.62;
  color:var(--ink2);break-inside:avoid;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.coverback .setlist .n{color:var(--ink3)}
.coverback .finding{margin-top:12px;padding-top:9px;border-top:1px solid var(--cream3);
  font-style:italic;font-size:10.5px;line-height:1.42;color:var(--ink2)}
.coverback .sigil{display:flex;gap:9px;justify-content:center;margin-top:22px;opacity:.85}
.coverback .tagline{margin-top:14px;font-family:'Jost',sans-serif;font-style:italic;
  font-size:11.5px;line-height:1.5;color:var(--ink3);text-align:center}
.coverback .credit{margin-top:auto;padding-top:9px;border-top:1.5px solid var(--gold2);
  display:flex;justify-content:space-between;align-items:baseline;width:100%;
  font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.05em;color:var(--ink3)}
"""


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def set_list() -> list[tuple[str, str]]:
    """(number, name) for every card in the printed deck, in set order.

    Read from cards/_roster.yaml, which is the print order. This used to read the
    exported deck folders because card.json's `num` counted a different set and
    disagreed with them; sync_roster.py now drives both, so the roster is the one
    place the order lives.
    """
    import sync_roster
    out = []
    dirs = sync_roster.card_dirs()
    for slug in sync_roster.read_roster():
        c = json.loads((dirs[slug] / "card.json").read_text())
        out.append((c["num"].split("/")[0], c.get("name") or slug))
    return out


def spread_figures() -> tuple[int, int, int]:
    """Shortest and longest card in the deck, measured from the corpus.

    Measured over the cards actually in the roster, not hardcoded. The old
    hardcoded pair named Opus 4.8 as the longest at 61,922 while Opus 4.7
    (62,813) and Mythos Preview (65,849) were already in the deck and longer,
    so the headline figure on the back understated its own finding.
    """
    import csv
    import sync_roster
    from sync_word_counts import PAIR

    docs = {r["slug"]: int(r["word_count_latest"] or 0)
            for r in csv.DictReader(open(REPO / "data/dataset/documents.csv"))}
    counts = [docs[PAIR[s]] for s in sync_roster.read_roster()
              if s in PAIR and docs.get(PAIR[s])]
    lo, hi = min(counts), max(counts)
    return lo, hi, round(hi / lo)


def build(n_cards: int | None = None) -> Path:
    if n_cards is None:
        n_cards = len(set_list())
    style = re.search(r"<style>(.*?)</style>", STYLE_SRC.read_text(), re.S).group(1)
    links = "".join(re.findall(r'<link[^>]+href="https://fonts[^"]+"[^>]*>', STYLE_SRC.read_text()))

    art = DEST / "art" / "hero.png"
    art_inner = ('<img src="art/hero.png" alt="">' if art.exists()
                 else '<div class="art-ph">HERO ART PENDING</div>')

    front = (
        '<div class="face front"><div class="tcg lab-freesystems"><div class="gold">'
        '<div class="inner cover">'
        '<div class="wordmark">FREE<br>SYSTEMS</div>'
        '<div class="rule"></div>'
        '<div class="kicker">MODEL CARDS</div>'
        f'<div class="art"><div class="art-win">{art_inner}</div></div>'
        '<div class="sparkrow"><span class="e"></span><span class="e"></span><span class="e"></span></div>'
        f'<div class="setline">SET 01 · {n_cards} CARDS</div>'
        '<div class="site">modelcards.net</div>'
        "</div></div></div></div>"
    )
    # The back carries the set list and the finding the set exists to make.
    entries = set_list()
    items = "".join(
        f'<div><span class="n">{num}</span> {html_escape(name)}</div>' for num, name in entries
    )
    lo, hi, spread = spread_figures()
    back = (
        '<div class="face back"><div class="tcg lab-freesystems"><div class="gold">'
        '<div class="inner cover coverback">'
        '<div class="wordmark">FREE SYSTEMS</div>'
        '<div class="rule"></div>'
        f'<div class="kicker">SET 01 · {len(entries)} CARDS</div>'
        f'<div class="setlist">{items}</div>'
        f'<div class="finding">Documentation across this set spans {spread}×. The shortest '
        f'card here runs {lo:,} words, the longest {hi:,}. Every figure printed here is '
        'measured from the published document, not reported by the lab.</div>'
        '<div class="sigil"><span class="e"></span><span class="e"></span><span class="e"></span></div>'
        '<div class="tagline">Every card in this set is a real disclosure record.<br>'
        'What a lab chose not to measure is printed too.</div>'
        '<div class="credit"><span>FREE SYSTEMS LAB · STANFORD GSB</span>'
        '<span>modelcards.net</span></div>'
        "</div></div></div></div>"
    )

    doc = ('<!DOCTYPE html><html><head><meta charset="UTF-8">' + links
           + "<style>" + style + COVER_CSS + "</style></head><body>"
           + '<div class="stage"><div class="cardwrap"><div class="flipper">'
           + front + back + "</div></div></div></body></html>")

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "art").mkdir(exist_ok=True)
    out = DEST / "free-systems-cover.html"
    out.write_text(doc)

    (DEST / "card.json").write_text(json.dumps({
        "lab": "freesystems", "name": "Free Systems", "slug": "free-systems-cover",
        "html": "free-systems-cover.html", "num": None, "tier": "cover",
        "source": "pack-cover", "in_deck": False,
    }, indent=2) + "\n")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    p = build(n)
    print(f"  wrote {p}")
    print(f"  hero art: {'present' if (DEST/'art'/'hero.png').exists() else 'PENDING — placeholder shown'}")
