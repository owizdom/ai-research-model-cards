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

/* ---- tuck box panels: parchment and gold, like the cards ----------------
   The box was near-black (#0b0805), darker than any colour in the deck: card
   faces are cream, frames gold, and the only dark is the art window's #1a1005.
   A shelf of these cards reads cream and gold, so a black box read as a
   different product. Solid dark also cracks white along a crease when folded
   board is scored, and a tuck box has six creases, plus it shows every scuff
   on something people handle.

   Authored at 816x1110, the print file size, shown at .588 in the gallery.
   build_print.py's full-bleed mode sets zoom:1. These px ARE print px at
   300dpi where 1pt = 4.167px, so fine print is 16-20px, not the card CSS's
   8-11px, which only works because .pframe scales it by 1.581.

   No outer keyline: on the dieline the panel edge IS a crease, and a hairline
   running parallel to one advertises every millimetre of die-cut drift. Gold
   appears on the art panel, the wordmark and the rules instead. */
.boxpanel{position:relative;width:816px;height:1110px;overflow:hidden;color:var(--ink);
  background:linear-gradient(158deg,var(--cream) 0%,var(--cream2) 54%,var(--cream3) 100%);
  font-family:'Jost',sans-serif;zoom:.588}
.boxpanel .pad{position:absolute;inset:0;padding:74px 70px 66px;display:flex;flex-direction:column}
.boxpanel .grain{position:absolute;inset:0;opacity:.05;pointer-events:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E")}

.boxfront .top{display:flex;justify-content:space-between;align-items:flex-start}
.boxfront .mark{font-family:'JetBrains Mono',monospace;font-size:19px;font-weight:600;
  letter-spacing:.24em;color:var(--t3);padding-top:16px}
.boxfront .badge{width:112px;height:112px;border-radius:50%;border:2.5px solid var(--gold2);
  background:radial-gradient(circle at 50% 32%,#fff8e2,var(--cream2));
  box-shadow:0 3px 11px rgba(90,61,28,.22);flex:0 0 auto;
  display:flex;flex-direction:column;align-items:center;justify-content:center}
.boxfront .badge .n{font-family:'Cinzel',serif;font-size:44px;font-weight:700;
  line-height:1;color:var(--ink)}
.boxfront .badge .w{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;
  letter-spacing:.2em;color:var(--ink3);margin-top:4px}

/* The mosaic is the set's REAL artwork. The old hero was generated from a text
   description of the creatures, so its eagle, whale and cat were repaints that
   appear on no card. These are the actual files: 21 arts, a 6x4 grid with one
   featured 2x2, which is 20 singles + 4 cells = exactly 24. */
.boxfront .art{margin-top:24px;padding:5px;border-radius:7px;
  background:linear-gradient(150deg,#e8c878,#b8902e,#8a6420);
  box-shadow:0 4px 15px rgba(90,61,28,.30),inset 0 1px 2px rgba(255,255,255,.45)}
.boxfront .mosaic{display:grid;grid-template-columns:repeat(6,1fr);grid-auto-flow:dense;
  gap:2px;border-radius:4px;overflow:hidden;background:#1a1005}
.boxfront .mosaic img{width:100%;aspect-ratio:1/1;object-fit:cover;display:block}
.boxfront .mosaic img.feat{grid-column:3/span 2;grid-row:2/span 2}

.boxfront .lockup{margin-top:30px;text-align:center}
.boxfront .wm{font-family:'Cinzel',serif;font-size:70px;font-weight:700;letter-spacing:.10em;
  line-height:1.05;
  background:linear-gradient(178deg,#f6dd9c 0%,var(--gold2) 30%,#a87a1e 66%,#6d4d0e 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.boxfront .hair{width:54%;height:2px;margin:15px auto 13px;
  background:linear-gradient(90deg,transparent,var(--gold2),transparent)}
.boxfront .kick{font-family:'JetBrains Mono',monospace;font-size:23px;font-weight:600;
  letter-spacing:.36em;text-indent:.36em;color:var(--ink2)}
.boxfront .labs{margin-top:auto;text-align:center;font-family:'JetBrains Mono',monospace;
  font-size:16px;font-weight:600;letter-spacing:.09em;line-height:1.8;color:var(--ink3)}
.boxfront .url{margin-top:12px;padding-top:12px;border-top:1px solid var(--cream3);
  text-align:center;font-family:'JetBrains Mono',monospace;font-size:17px;
  letter-spacing:.16em;color:var(--ink3)}

/* ---- box back: the cards themselves, on a display board -----------------
   The numbered set list used to print here AND on the About card back from the
   same set_list() call. The About card keeps it; this shows what is inside. */
.boxback .wm2{font-family:'Cinzel',serif;font-size:40px;font-weight:700;letter-spacing:.10em;
  text-align:center;line-height:1.05;
  background:linear-gradient(178deg,#f6dd9c 0%,var(--gold2) 30%,#a87a1e 66%,#6d4d0e 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.boxback .kick2{font-family:'JetBrains Mono',monospace;font-size:19px;font-weight:600;
  letter-spacing:.30em;text-indent:.30em;text-align:center;margin-top:12px;color:var(--ink2)}
.boxback .board{margin-top:24px;padding:14px 12px;border-radius:7px;
  background:linear-gradient(150deg,#e8c878,#b8902e,#8a6420);
  box-shadow:0 4px 15px rgba(90,61,28,.30),inset 0 1px 2px rgba(255,255,255,.45)}
.boxback .grid{display:flex;flex-wrap:wrap;justify-content:center;gap:9px;
  padding:12px 10px;border-radius:4px;background:#1a1005}
.boxback .grid img{width:96px;height:131px;object-fit:cover;border-radius:3px;
  box-shadow:0 2px 6px rgba(0,0,0,.55)}
.boxback .finding{margin-top:auto;padding-top:22px;text-align:center;
  font-size:19px;line-height:1.52;color:var(--ink2)}
.boxback .fine{margin-top:16px;padding-top:13px;border-top:1.5px solid var(--gold2);
  display:flex;justify-content:space-between;align-items:baseline;
  font-family:'JetBrains Mono',monospace;font-size:16px;letter-spacing:.07em;color:var(--ink3)}

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


def _sips(src: Path, dest: Path, px: int) -> None:
    if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
        subprocess.run(["sips", "-Z", str(px), str(src), "--out", str(dest)],
                       check=True, capture_output=True)


def make_thumbs(slugs: list[str], dest: Path) -> list[tuple[str, str]]:
    """Downscale each rendered card FRONT for the box back.

    Reads print/<slug>_front.jpg, so the box has to be built after the deck.
    sips ships with macOS, same as build_print.py already assumes a macOS
    Chrome. Output is build artefact, gitignored alongside print/.
    """
    tdir = dest / "thumbs"
    tdir.mkdir(parents=True, exist_ok=True)
    got, missing = [], []
    for slug in slugs:
        src = ROOT / "print" / f"{slug}_front.jpg"
        if not src.exists():
            missing.append(slug)
            continue
        _sips(src, tdir / f"{slug}.jpg", 220)
        got.append((slug, f"thumbs/{slug}.jpg"))
    if missing:
        print(f"  ! no render yet, missing from the box back: {', '.join(missing)}")
    return got


FEATURE = "le-chaton-fat"   # the 2x2 tile; James asked for the fat cat


def make_mosaic(slugs: list[str], dest: Path) -> list[tuple[str, str]]:
    """The REAL card artwork for the box front.

    Not a render and not a repaint: the actual art/*.png each card points at.
    The old hero was generated from a text description of the creatures, so the
    eagle, whale and cat on the box were images that appear on no card.

    Returns (slug, relpath) with the feature first so the grid can place it.
    """
    import sync_roster
    mdir = dest / "mosaic"
    mdir.mkdir(parents=True, exist_ok=True)
    dirs = sync_roster.card_dirs()
    rows, missing = [], []
    for slug in slugs:
        c = json.loads((dirs[slug] / "card.json").read_text())
        art = dirs[slug] / "art" / (c.get("art") or f"{slug}.png")
        if not art.exists():
            missing.append(slug)
            continue
        _sips(art, mdir / f"{slug}.jpg", 320)
        rows.append((slug, f"mosaic/{slug}.jpg"))
    if missing:
        print(f"  ! no art file, not on the box front: {', '.join(missing)}")
    rows.sort(key=lambda r: r[0] != FEATURE)     # feature first
    return rows


def build_tuckbox() -> Path:
    """The pack's outer box, as two full-bleed panels on parchment.

    Front: the set's real artwork in a mosaic, on the same cream and gold the
    cards use. Back: the actual card fronts on a display board.

    Both are 816x1110 so they still ride build_print.py and check_bleed.py, and
    build_dieline.py places them into the folded box.
    """
    import sync_roster
    from build_card_html import LAB_NAME

    dest = CARDS / "_pack" / "free-systems-tuckbox"
    dest.mkdir(parents=True, exist_ok=True)

    dirs = sync_roster.card_dirs()
    slugs = sync_roster.read_roster()
    seen, labs = set(), []
    for s_ in slugs:                       # first-appearance order, deck order
        lab = json.loads((dirs[s_] / "card.json").read_text())["lab"]
        if lab not in seen:
            seen.add(lab)
            labs.append(LAB_NAME.get(lab, lab).upper().replace(" ", "\u00a0"))
    labline = " \u00b7 ".join(labs)
    _h = (len(labs) + 1) // 2
    labs_html = (html_escape(" \u00b7 ".join(labs[:_h])) + " \u00b7<br>"
                 + html_escape(" \u00b7 ".join(labs[_h:])))

    style = re.search(r"<style>(.*?)</style>", STYLE_SRC.read_text(), re.S).group(1)
    links = "".join(re.findall(r'<link[^>]+href="https://fonts[^"]+"[^>]*>', STYLE_SRC.read_text()))

    mosaic = make_mosaic(slugs, dest)
    tiles = "".join(
        f'<img class="feat" src="{rel}" alt="">' if slug == FEATURE
        else f'<img src="{rel}" alt="">'
        for slug, rel in mosaic)

    face = (
        '<div class="face front"><div class="boxpanel boxfront"><div class="pad">'
        '<div class="top"><div class="mark">FREE SYSTEMS LAB</div>'
        f'<div class="badge"><span class="n">{len(slugs)}</span>'
        '<span class="w">CARDS</span></div></div>'
        f'<div class="art"><div class="mosaic">{tiles}</div></div>'
        '<div class="lockup"><div class="wm">FREE SYSTEMS</div>'
        '<div class="hair"></div><div class="kick">MODEL CARDS</div></div>'
        f'<div class="labs">{labs_html}</div>'
        '<div class="url">SET 01 \u00b7 freesystems.net</div>'
        '</div><div class="grain"></div></div></div>'
    )

    lo, hi, spread = spread_figures()
    thumbs = make_thumbs(slugs, dest)
    cards_html = "".join(f'<img src="{rel}" alt="">' for _, rel in thumbs)
    back = (
        '<div class="face back"><div class="boxpanel boxback"><div class="pad">'
        '<div class="wm2">FREE SYSTEMS</div>'
        f'<div class="kick2">SET 01 \u00b7 {len(slugs)} CARDS</div>'
        f'<div class="board"><div class="grid">{cards_html}</div></div>'
        f'<div class="finding">One card per model, every figure read out of the '
        f'lab\'s own published document. The longest runs {hi:,} words and the '
        f'shortest {lo:,}. What a lab chose not to measure is printed here too.</div>'
        '<div class="fine"><span>FREE SYSTEMS LAB \u00b7 STANFORD GSB</span>'
        '<span>freesystems.net</span></div>'
        '</div><div class="grain"></div></div></div>'
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
    print(f"  box front mosaic: {len(mosaic)} real artworks, feature = {FEATURE}")
    print(f"  box back shows {len(thumbs)}/{len(slugs)} card fronts")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    p = build(n)
    build_tuckbox()
    print(f"  wrote {p}")
    print(f"  hero art: {'present' if (DEST/'art'/'hero.png').exists() else 'PENDING — placeholder shown'}")

