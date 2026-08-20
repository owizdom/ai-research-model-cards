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
import subprocess
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

/* ---- tuck box panels: full bleed, no card frame -------------------------
   The box is not a card. It carried the card composition, which nests four
   rectangles (parchment sheet, blurred bleed band, gold frame, cream panel,
   art window) and left the artwork holding 33% of the face. Real packs give
   art the whole face and set type on top of it, so these panels do that.

   Authored at 816x1110, the print file size, shown at .588 in the gallery
   where .cardwrap is 480px wide. build_print.py's full-bleed mode sets zoom:1.

   These px ARE print px at 300dpi, where 1pt = 4.167px. The fine print here is
   17-20px because that is 4-5pt, what packs actually set credits at. Sizing it
   off the card CSS (8-11px) would print at 2 to 2.6pt and be unreadable: the
   cards get away with it only because .pframe scales them by 1.581. */
.boxpanel{position:relative;width:816px;height:1110px;overflow:hidden;
  background:#0b0805;color:var(--cream);font-family:'Jost',sans-serif;zoom:.588}
.boxpanel .hero{position:absolute;top:0;left:0;width:816px;height:auto;display:block}
/* The hero is square, the panel is 816 wide, so it lands 816x816 with nothing
   cropped at all. The old window discarded 95px of it. Below 816 the panel's
   own black carries on; the seam starts under the lowest ink (row 932 of 1024
   = y 743 here) so it feathers backdrop into backdrop and cannot be seen. */
.boxpanel .seam{position:absolute;left:0;right:0;top:731px;height:180px;
  background:linear-gradient(180deg,rgba(11,8,5,0),#0b0805 68%)}
.boxpanel .scrim{position:absolute;left:0;right:0;top:0;height:210px;
  background:linear-gradient(180deg,rgba(6,4,2,.80),rgba(6,4,2,.32) 54%,rgba(6,4,2,0))}

/* Ink density measured over the hero on an 8x8 grid: row 0 is 0-18% across the
   whole width, so the mark and the badge sit on backdrop. Columns 5-6 at rows
   1-2 run 44-64% (the dragon), which is why the badge stays in the corner. */
.boxfront .mark{position:absolute;top:74px;left:74px;font-family:'JetBrains Mono',monospace;
  font-size:19px;font-weight:600;letter-spacing:.24em;color:var(--gold)}
.boxfront .badge{position:absolute;top:66px;right:70px;width:150px;height:150px;
  border-radius:50%;border:2px solid var(--gold2);
  background:radial-gradient(circle at 50% 32%,rgba(28,19,7,.93),rgba(9,6,3,.97));
  box-shadow:0 0 0 5px rgba(9,6,3,.5),0 6px 20px rgba(0,0,0,.55);
  display:flex;flex-direction:column;align-items:center;justify-content:center}
.boxfront .badge .n{font-family:'Cinzel',serif;font-size:60px;font-weight:700;line-height:1;
  color:var(--gold);text-shadow:0 2px 6px rgba(0,0,0,.75)}
.boxfront .badge .w{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:600;
  letter-spacing:.22em;color:var(--cream2);margin-top:8px}

.boxfront .lockup{position:absolute;left:74px;right:74px;bottom:205px;text-align:center}
.boxfront .wm{font-family:'Cinzel',serif;font-size:72px;font-weight:700;letter-spacing:.10em;
  line-height:1.05;
  background:linear-gradient(178deg,#fff4d0 0%,var(--gold) 34%,#c9962f 68%,#8a6414 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.boxfront .hair{width:56%;height:2px;margin:17px auto 14px;
  background:linear-gradient(90deg,transparent,var(--gold2),transparent)}
.boxfront .kick{font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:600;
  letter-spacing:.36em;text-indent:.36em;color:var(--cream2)}
.boxfront .labs{position:absolute;left:70px;right:70px;bottom:118px;text-align:center;
  font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:600;letter-spacing:.09em;
  line-height:1.78;color:rgba(226,210,168,.80)}
.boxfront .url{position:absolute;left:70px;right:70px;bottom:72px;text-align:center;
  font-family:'JetBrains Mono',monospace;font-size:18px;letter-spacing:.16em;
  color:rgba(226,210,168,.58)}

/* ---- box back: the cards themselves ------------------------------------
   The numbered set list used to print here AND on the About card back, from
   the same set_list() call. The About card keeps it; this panel shows what is
   actually in the box, which is what the reference packs put on their reverse. */
.boxback .bg{position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% 6%,rgba(184,122,46,.17),transparent 60%)}
.boxback .pad{position:absolute;inset:0;padding:70px 48px 66px;display:flex;flex-direction:column}
.boxback .wm2{margin-left:22px;margin-right:22px;font-family:'Cinzel',serif;font-size:40px;font-weight:700;letter-spacing:.10em;
  text-align:center;line-height:1.05;
  background:linear-gradient(178deg,#fff4d0 0%,var(--gold) 34%,#c9962f 68%,#8a6414 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.boxback .kick2{margin-left:22px;margin-right:22px;font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:600;
  letter-spacing:.30em;text-indent:.30em;text-align:center;margin-top:13px;color:var(--gold)}
.boxback .grid{margin-top:30px;display:flex;flex-wrap:wrap;justify-content:center;gap:10px}
.boxback .grid img{width:111px;height:151px;object-fit:cover;border-radius:4px;
  box-shadow:0 2px 7px rgba(0,0,0,.6)}
.boxback .finding{margin-top:auto;margin-left:22px;margin-right:22px;padding-top:24px;text-align:center;
  font-size:20px;line-height:1.52;color:rgba(236,224,192,.86)}
.boxback .fine{margin:20px 22px 0;padding-top:15px;border-top:1px solid rgba(220,171,68,.34);
  display:flex;justify-content:space-between;align-items:baseline;
  font-family:'JetBrains Mono',monospace;font-size:17px;letter-spacing:.07em;
  color:rgba(226,210,168,.62)}

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


def make_thumbs(slugs: list[str], dest: Path) -> list[tuple[str, str]]:
    """Downscale each rendered card front for the box back.

    Uses sips, which ships with macOS, same as build_print.py already assumes a
    macOS Chrome path. Written at 2x the display size so the grid stays crisp at
    300dpi. Output is build artefact, gitignored alongside print/.

    The cards must already be rendered: this reads print/<slug>_front.jpg, so
    the box has to be built after the deck, not with it.
    """
    tdir = dest / "thumbs"
    tdir.mkdir(parents=True, exist_ok=True)
    got, missing = [], []
    for slug in slugs:
        src = ROOT / "print" / f"{slug}_front.jpg"
        if not src.exists():
            missing.append(slug)
            continue
        out = tdir / f"{slug}.jpg"
        if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
            subprocess.run(["sips", "-Z", "220", str(src), "--out", str(out)],
                           check=True, capture_output=True)
        got.append((slug, f"thumbs/{slug}.jpg"))
    if missing:
        print(f"  ! no render yet, missing from the box back: {', '.join(missing)}")
    return got


def build_tuckbox() -> Path:
    """The pack's outer box, as two full-bleed panels.

    Front: the hero fills the face and the type sits on it, which is what the
    reference packs do. Back: the actual cards, because the numbered list
    already prints on the About card back and did not need printing twice.

    Both are 816x1110 so they still ride build_print.py and check_bleed.py, and
    build_dieline.py places them into the folded box.
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
            # non-breaking space: the strip wraps to two lines and
            # "THINKING MACHINES" was splitting across them
            labs.append(LAB_NAME.get(lab, lab).upper().replace(" ", "\u00a0"))
    labline = " \u00b7 ".join(labs)
    # Split at the midpoint rather than letting it wrap: with the names made
    # unbreakable, greedy wrapping put MISTRAL AI alone on a third line.
    _h = (len(labs) + 1) // 2
    labs_html = (html_escape(" \u00b7 ".join(labs[:_h])) + " \u00b7<br>"
                 + html_escape(" \u00b7 ".join(labs[_h:])))

    style = re.search(r"<style>(.*?)</style>", STYLE_SRC.read_text(), re.S).group(1)
    links = "".join(re.findall(r'<link[^>]+href="https://fonts[^"]+"[^>]*>', STYLE_SRC.read_text()))
    art = dest / "art" / "hero.png"
    hero = ('<img class="hero" src="art/hero.png" alt="">' if art.exists()
            else '<div class="art-ph">HERO ART PENDING</div>')

    face = (
        '<div class="face front"><div class="boxpanel boxfront">'
        + hero
        + '<div class="seam"></div><div class="scrim"></div>'
        '<div class="mark">FREE SYSTEMS LAB</div>'
        f'<div class="badge"><span class="n">{len(slugs)}</span><span class="w">CARDS</span></div>'
        '<div class="lockup"><div class="wm">FREE SYSTEMS</div>'
        '<div class="hair"></div><div class="kick">MODEL CARDS</div></div>'
        f'<div class="labs">{labs_html}</div>'
        '<div class="url">SET 01 \u00b7 freesystems.net</div>'
        "</div></div>"
    )

    lo, hi, spread = spread_figures()
    thumbs = make_thumbs(slugs, dest)
    tiles = "".join(f'<img src="{rel}" alt="">' for _, rel in thumbs)
    back = (
        '<div class="face back"><div class="boxpanel boxback">'
        '<div class="bg"></div><div class="pad">'
        '<div class="wm2">FREE SYSTEMS</div>'
        f'<div class="kick2">SET 01 \u00b7 {len(slugs)} CARDS</div>'
        f'<div class="grid">{tiles}</div>'
        f'<div class="finding">One card per model, every figure read out of the '
        f'lab\'s own published document. The longest runs {hi:,} words and the '
        f'shortest {lo:,}. What a lab chose not to measure is printed here too.</div>'
        '<div class="fine"><span>FREE SYSTEMS LAB \u00b7 STANFORD GSB</span>'
        '<span>freesystems.net</span></div>'
        "</div></div></div>"
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
        "source": "pack-tuckbox", "in_deck": False, "full_bleed": True,
    }, indent=2) + "\n")
    print(f"  wrote {out}")
    print(f"  labs: {labline}")
    print(f"  box back shows {len(thumbs)}/{len(slugs)} card fronts")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    p = build(n)
    build_tuckbox()
    print(f"  wrote {p}")
    print(f"  hero art: {'present' if (DEST/'art'/'hero.png').exists() else 'PENDING — placeholder shown'}")

