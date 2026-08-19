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

/* ---- the tuck box ------------------------------------------------------- */
.tuck .wordmark{font-size:34px}
.tuck .art{margin-top:12px;width:100%;flex:1 1 auto;display:flex}
.tuck .art-win{flex:1 1 auto;height:auto;min-height:300px}
.tuck .art-win img{object-position:50% 50%}
.tuck .labs{margin-top:14px;font-family:'JetBrains Mono',monospace;font-size:8.6px;
  font-weight:600;letter-spacing:.13em;color:var(--ink2);line-height:1.85;text-align:center;
  max-width:92%}
.tuck .setline{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;
  letter-spacing:.2em;color:var(--ink2);margin-top:12px;padding-top:9px;
  border-top:1px solid var(--cream3);width:70%}
.tuck .site{font-family:'JetBrains Mono',monospace;font-size:9.5px;
  letter-spacing:.14em;color:var(--ink3);margin-top:5px}

/* ---- cover front: the about card ---------------------------------------- */
.cover .wordmark.sm{font-size:26px}
.coverabout .abouttext{margin-top:18px;text-align:left;width:100%;flex:1 1 auto}
.coverabout .abouttext p{font-family:'Jost',sans-serif;font-size:13px;line-height:1.66;
  color:var(--ink2);margin:0 0 10px}
.coverabout .abouttext p:last-child{margin-bottom:0}
.coverabout .credit{margin-top:auto;padding-top:9px;border-top:1.5px solid var(--gold2);
  display:flex;justify-content:space-between;align-items:baseline;width:100%;
  font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.05em;color:var(--ink3)}
.coverabout .sparkrow{margin-top:14px}

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

/* Its back is the contents panel and carries less than the cover back, so the
   list can be set at a readable size. 23 names fit two columns without the
   ellipsis that three columns forced. */
.tuckback .setlist{columns:2;column-gap:20px;margin-top:20px}
.tuckback .setlist div{font-size:11.4px;line-height:2.12}
.tuckback .finding{margin-top:22px;padding-top:14px;font-size:12.5px;line-height:1.5}
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

    lo, hi, spread = spread_figures()
    art = DEST / "art" / "hero.png"
    art_inner = ('<img src="art/hero.png" alt="">' if art.exists()
                 else '<div class="art-ph">HERO ART PENDING</div>')

    # The pack's first card. James asked for an "about" on the reverse of the
    # all-cards list, so the wordmark front becomes the explanation and the list
    # stays on the back. Voice per feedback_free_systems_writing_style: empirical,
    # direct, slightly strange. No em-dashes, no tricolons, no "from X to Y".
    front = (
        '<div class="face front"><div class="tcg lab-freesystems"><div class="gold">'
        '<div class="inner cover coverabout">'
        '<div class="wordmark sm">FREE SYSTEMS</div>'
        '<div class="rule"></div>'
        '<div class="kicker">ABOUT THIS SET</div>'
        '<div class="abouttext">'
        '<p>Every model in this set ships with a document its own lab wrote about '
        'it. Those documents are the industry\'s record of what a model can do and '
        'what it was tested for. Almost nobody reads them.</p>'
        f'<p>They are also wildly uneven. The longest card here runs {hi:,} words. '
        f'The shortest runs {lo:,}. Some report dozens of benchmarks and some '
        'report none at all.</p>'
        '<p>So we read them. One card per model, every figure taken from the '
        'lab\'s own published document. Where a lab reported nothing, the card '
        'says nothing.</p>'
        '<p>The set runs in release order, so you can read along the shelf and '
        'watch capability climb while the disclosure behind it does whatever it '
        'happens to do. The two do not move together.</p>'
        '<p>Laid out side by side they show the shape of the record: the handful '
        'of benchmarks every lab reports, and the much larger number only one lab '
        'has ever run. What a lab chose not to measure is printed here too.</p>'
        '</div>'
        '<div class="sparkrow"><span class="e"></span><span class="e"></span><span class="e"></span></div>'
        '<div class="credit"><span>FREE SYSTEMS LAB · STANFORD GSB</span>'
        '<span>freesystems.net</span></div>'
        "</div></div></div></div>"
    )

    # The back carries the set list and the finding the set exists to make.
    entries = set_list()
    items = "".join(
        f'<div><span class="n">{num}</span> {html_escape(name)}</div>' for num, name in entries
    )
    back = (
        '<div class="face back"><div class="tcg lab-freesystems"><div class="gold">'
        '<div class="inner cover coverback">'
        '<div class="wordmark">FREE SYSTEMS</div>'
        '<div class="rule"></div>'
        f'<div class="kicker">SET 01 · {len(entries)} CARDS</div>'
        f'<div class="setlist">{items}</div>'
        # The old line claimed every figure was "measured from the published
        # document, not reported by the lab". Word counts are measured. Every
        # benchmark score in the corpus is is_self_reported=True, so the second
        # half was false for most of the deck.
        f'<div class="finding">Documentation across this set spans {spread}×. The shortest '
        f'card here runs {lo:,} words, the longest {hi:,}. Word counts are measured from '
        "the published document. Benchmark scores are the lab's own, printed with the "
        'variant named.</div>'
        '<div class="sigil"><span class="e"></span><span class="e"></span><span class="e"></span></div>'
        '<div class="tagline">Every card in this set is a real disclosure record.<br>'
        'What a lab chose not to measure is printed too.</div>'
        '<div class="credit"><span>FREE SYSTEMS LAB · STANFORD GSB</span>'
        '<span>freesystems.net</span></div>'
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


def build_tuckbox() -> Path:
    """The pack's outer box.

    James's version carried five creatures and named six labs, and read SET 01 ·
    18 CARDS. The set is 23 across eight labs now, so the art was regenerated to
    hold all eight and xAI and Meta are named. Same 816x1110 card spec so it
    rides the same print pipeline and bleed check as everything else.
    """
    import sync_roster
    from build_card_html import LAB_NAME

    dest = CARDS / "_pack" / "free-systems-tuckbox"
    (dest / "art").mkdir(parents=True, exist_ok=True)
    src = CARDS / "_pack" / "free-systems-cover" / "art" / "tuckbox-hero.png"
    if src.exists():
        (dest / "art" / "hero.png").write_bytes(src.read_bytes())

    dirs = sync_roster.card_dirs()
    slugs = sync_roster.read_roster()
    seen, labs = set(), []
    for s_ in slugs:                       # first-appearance order, deck order
        lab = json.loads((dirs[s_] / "card.json").read_text())["lab"]
        if lab not in seen:
            seen.add(lab)
            labs.append(LAB_NAME.get(lab, lab).upper())
    labline = " · ".join(labs)

    style = re.search(r"<style>(.*?)</style>", STYLE_SRC.read_text(), re.S).group(1)
    links = "".join(re.findall(r'<link[^>]+href="https://fonts[^"]+"[^>]*>', STYLE_SRC.read_text()))
    art = dest / "art" / "hero.png"
    art_inner = ('<img src="art/hero.png" alt="">' if art.exists()
                 else '<div class="art-ph">HERO ART PENDING</div>')

    face = (
        '<div class="face front"><div class="tcg lab-freesystems"><div class="gold">'
        '<div class="inner cover tuck">'
        '<div class="wordmark">FREE<br>SYSTEMS</div>'
        '<div class="rule"></div>'
        '<div class="kicker">MODEL CARDS</div>'
        f'<div class="art"><div class="art-win">{art_inner}</div></div>'
        '<div class="sparkrow"><span class="e"></span><span class="e"></span><span class="e"></span></div>'
        f'<div class="labs">{html_escape(labline)}</div>'
        f'<div class="setline">SET 01 · {len(slugs)} CARDS</div>'
        '<div class="site">freesystems.net</div>'
        "</div></div></div></div>"
    )
    # The box back is the contents panel. It used to be a copy of the front,
    # which printed the same artwork on both sides of the box.
    lo, hi, spread = spread_figures()
    items = "".join(
        f'<div><span class="n">{num}</span> {html_escape(name)}</div>'
        for num, name in set_list())
    back = (
        '<div class="face back"><div class="tcg lab-freesystems"><div class="gold">'
        '<div class="inner cover coverback tuckback">'
        '<div class="wordmark">FREE SYSTEMS</div>'
        '<div class="rule"></div>'
        f'<div class="kicker">SET 01 · {len(slugs)} CARDS</div>'
        f'<div class="setlist">{items}</div>'
        f'<div class="finding">One card per model, every figure read out of the '
        f'lab\'s own published document. The longest runs {hi:,} words and the '
        f'shortest {lo:,}. What a lab chose not to measure is printed here too.</div>'
        '<div class="sigil"><span class="e"></span><span class="e"></span><span class="e"></span></div>'
        '<div class="credit"><span>FREE SYSTEMS LAB · STANFORD GSB</span>'
        '<span>freesystems.net</span></div>'
        "</div></div></div></div>"
    )
    doc = ('<!DOCTYPE html><html><head><meta charset="UTF-8">' + links
           + "<style>" + style + COVER_CSS + "</style></head><body>"
           + '<div class="stage"><div class="cardwrap"><div class="flipper">'
           + face + back + "</div></div></div></body></html>")
    out = dest / "free-systems-tuckbox.html"
    out.write_text(doc)
    (dest / "card.json").write_text(json.dumps({
        "lab": "freesystems", "name": "Free Systems Tuck Box", "slug": "free-systems-tuckbox",
        "html": "free-systems-tuckbox.html", "num": None, "tier": "cover",
        "source": "pack-tuckbox", "in_deck": False,
    }, indent=2) + "\n")
    print(f"  wrote {out}")
    print(f"  labs: {labline}")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    p = build(n)
    build_tuckbox()
    print(f"  wrote {p}")
    print(f"  hero art: {'present' if (DEST/'art'/'hero.png').exists() else 'PENDING — placeholder shown'}")

