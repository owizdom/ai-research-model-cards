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

/* ---- tuck box panels: retail pack layout on parchment -------------------
   Built to the idiom of the Yu-Gi-Oh packs used as reference: a publisher bar
   across the top, an ornate frame, an angled burst calling the contents, the
   set's artwork scattered like a spill of cards, the logo locked up over the
   lower third, and a contents strip in fine print at the foot.

   Parchment and gold rather than black, because the deck is cream and gold and
   the only dark in it is the art window's #1a1005. Solid dark also cracks white
   along a scored crease and a tuck box has six of them.

   Authored at 816x1110, the print size, shown at .588 in the gallery.
   build_print.py's full-bleed mode sets zoom:1, and these px ARE print px at
   300dpi where 1pt = 4.167px, so fine print is 15-20px. */
.boxpanel{position:relative;width:816px;height:1110px;overflow:hidden;color:var(--ink);
  background:linear-gradient(158deg,var(--cream) 0%,var(--cream2) 54%,var(--cream3) 100%);
  font-family:'Jost',sans-serif;zoom:.588}
.boxpanel .pad{position:absolute;inset:0;padding:66px 44px 64px;display:flex;flex-direction:column}
.boxpanel .grain{position:absolute;inset:0;opacity:.05;pointer-events:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E")}

/* publisher bar: the KONAMI / 1st Edition row */
.boxpanel .bar{display:flex;justify-content:space-between;align-items:center;
  padding:0 26px 12px;font-family:'JetBrains Mono',monospace}
.boxpanel .bar .lab{font-size:17px;font-weight:600;letter-spacing:.22em;color:var(--t3)}
.boxpanel .bar .ed{font-size:13px;font-weight:600;letter-spacing:.16em;color:#fff;
  background:var(--red);border-radius:2px;padding:5px 9px}

/* the ornate frame */
.boxpanel .frame{position:relative;flex:1 1 auto;min-height:0;
  border:2.5px solid var(--gold2);border-radius:4px;padding:7px;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.5),0 3px 14px rgba(90,61,28,.22)}
.boxpanel .frame::before{content:'';position:absolute;inset:5px;border:1px solid rgba(184,144,46,.45);
  border-radius:2px;pointer-events:none}
.boxpanel .cnr{position:absolute;width:13px;height:13px;border:2px solid var(--gold2);
  background:var(--cream);transform:rotate(45deg)}
.boxpanel .cnr.tl{left:-8px;top:-8px}.boxpanel .cnr.tr{right:-8px;top:-8px}
.boxpanel .cnr.bl{left:-8px;bottom:-8px}.boxpanel .cnr.br{right:-8px;bottom:-8px}

/* the scatter: the set's REAL artwork, spilled like a handful of cards */
.boxfront .well{position:absolute;inset:7px;border-radius:2px;overflow:hidden;
  background:radial-gradient(ellipse at 50% 36%,#2b1c0c 0%,#150d05 62%,#0d0703 100%)}
.boxfront .well img{position:absolute;object-fit:cover;border-radius:3px;
  box-shadow:0 6px 16px rgba(0,0,0,.62),0 0 0 1.5px rgba(226,210,168,.30)}
.boxfront .veil{position:absolute;left:0;right:0;bottom:0;height:52%;z-index:50;
  background:linear-gradient(0deg,rgba(7,4,2,.99) 0%,rgba(7,4,2,.96) 26%,
    rgba(7,4,2,.78) 52%,rgba(7,4,2,.34) 76%,rgba(7,4,2,0) 100%)}


.boxfront .lock{position:absolute;left:26px;right:26px;bottom:30px;text-align:center;z-index:60}
.boxfront .wm{font-family:'Cinzel',serif;font-size:64px;font-weight:700;letter-spacing:.09em;
  line-height:1.04;
  /* On the cards this gradient ends at #8a6414, which is right on parchment.
     Over the dark well it made the bottom half of every letter vanish, so the
     box keeps the same gold but never runs darker than the ground behind it. */
  background:linear-gradient(178deg,#fff8e4 0%,#f7dc98 38%,#eac36c 70%,#d8ac48 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 3px 9px rgba(0,0,0,.85))}
.boxfront .hair{width:46%;height:2px;margin:13px auto 11px;
  background:linear-gradient(90deg,transparent,var(--gold2),transparent)}
.boxfront .kick{font-family:'JetBrains Mono',monospace;font-size:21px;font-weight:600;
  letter-spacing:.34em;text-indent:.34em;color:#f0e4c2;text-shadow:0 2px 5px rgba(0,0,0,.8)}

/* contents strip under the frame, the "39 CARDS TOTAL" role */
.boxpanel .contents{padding:13px 26px 0;text-align:center;font-family:'JetBrains Mono',monospace}
.boxpanel .contents .cts{font-size:16px;font-weight:600;letter-spacing:.14em;color:var(--ink2)}
.boxpanel .contents .labs{margin-top:8px;font-size:14px;font-weight:600;letter-spacing:.07em;
  line-height:1.72;color:var(--ink3)}
.boxpanel .contents .url{margin-top:9px;font-size:15px;letter-spacing:.15em;color:var(--t3)}

/* ---- box back: the cards themselves, plus the contents copy -------------
   The numbered set list prints on the About card back from the same
   set_list() call, so it does not print again here. */
.boxback .well2{position:absolute;inset:7px;border-radius:2px;overflow:hidden;padding:20px 16px;
  background:radial-gradient(ellipse at 50% 12%,#2b1c0c 0%,#150d05 66%,#0d0703 100%);
  display:flex;flex-direction:column}
.boxback .blurb{text-align:center;font-family:'Cinzel',serif;font-size:20px;line-height:1.5;
  color:#f0dfae;letter-spacing:.02em}
.boxback .grid{margin-top:16px;display:flex;flex-wrap:wrap;justify-content:center;gap:7px}
.boxback .grid img{width:92px;height:125px;object-fit:cover;border-radius:3px;
  box-shadow:0 3px 8px rgba(0,0,0,.6),0 0 0 1px rgba(226,210,168,.22)}
.boxback .note{margin-top:auto;padding-top:14px;text-align:center;font-family:'Jost',sans-serif;
  font-size:16px;line-height:1.45;color:#cdbb90}
.boxback .legal{display:flex;align-items:flex-end;justify-content:space-between;
  padding:13px 26px 0;gap:16px}
.boxback .bc{width:150px;height:52px;border:1.5px dashed var(--ink3);border-radius:3px;
  display:flex;align-items:center;justify-content:center;
  font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.1em;color:var(--ink3)}
.boxback .lgl{flex:1;text-align:left;font-family:'JetBrains Mono',monospace;font-size:12px;
  line-height:1.6;color:var(--ink3)}
.boxback .lgl b{display:block;font-size:14px;letter-spacing:.12em;color:var(--ink2);font-weight:600}

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
        f'<div class="kicker">{len(entries)} CARDS</div>'
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


def card_art(d: Path, slug: str) -> Path | None:
    """The art file a card actually renders, not the one card.json claims.

    Two hand-authored cards had card.json out of step with their own HTML: one
    stored the path with an "art/" prefix the loader does not expect, the other
    named opus-4-7-dragon.png, which does not exist. Both dropped silently out
    of the box front. The HTML is what renders, so read that first.
    """
    for html in sorted(d.glob("*.html")):
        if html.name.startswith("print_"):
            continue
        m = re.search(r'<div class="art-win">\s*<img[^>]*src="art/([^"]+)"', html.read_text())
        if m and (d / "art" / m.group(1)).exists():
            return d / "art" / m.group(1)
    c = json.loads((d / "card.json").read_text())
    for cand in (c.get("art"), f"{slug}.png"):
        if not cand:
            continue
        p = d / "art" / cand.split("/")[-1]
        if p.exists():
            return p
    return None


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


FEATURE = "le-chaton-fat"   # the largest tile; James asked for the fat cat


def scatter(n: int, w: int, h: int) -> list[dict]:
    """Deterministic spill of n card-shaped tiles over a w x h well.

    A plain grid reads as a contact sheet. The reference packs spill their card
    art across the face at angles, so this lays tiles on a jittered grid: even
    coverage, no seams, and the same result on every build (seeded, so a
    rebuild does not reshuffle the box).
    """
    import random
    rnd = random.Random(11)
    cols, rows = 5, 5
    cw, ch = w / cols, h / rows
    tw, th = 176, 240                      # card-shaped tile
    slots = [(c, r) for r in range(rows) for c in range(cols)]
    out = []
    for i, (c, r) in enumerate(slots[:n]):
        sc = rnd.uniform(0.88, 1.14)
        # the feature tile is dealt last so it lands on top, and bigger
        big = i == n - 1
        if big:
            sc = 1.62
        twi, thi = tw * sc, th * sc
        cx = cw * (c + 0.5) + rnd.uniform(-16, 16)
        cy = ch * (r + 0.5) + rnd.uniform(-14, 14)
        if big:
            cx, cy = w * 0.5, h * 0.42
        out.append({
            "left": round(cx - twi / 2, 1), "top": round(cy - thi / 2, 1),
            "w": round(twi, 1), "h": round(thi, 1),
            "rot": 0 if big else round(rnd.uniform(-13, 13), 1),
            "z": 40 if big else i + 1,
        })
    return out


def _sips(src: Path, dest: Path, px: int) -> None:
    if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
        subprocess.run(["sips", "-Z", str(px), str(src), "--out", str(dest)],
                       check=True, capture_output=True)


def make_thumbs(slugs: list[str], dest: Path) -> list[tuple[str, str]]:
    """Downscale each rendered card FRONT for the box back.

    Reads print/<slug>_front.jpg, so the box must be built after the deck.
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


def make_mosaic(slugs: list[str], dest: Path) -> list[tuple[str, str]]:
    """The REAL card artwork for the box front.

    Not a render and not a repaint: the actual art/*.png each card points at.
    The hero this replaced was generated from a text description of the
    creatures, so its eagle, whale and cat appeared on no card in the set.

    Feature last, so it is dealt on top of the spill.
    """
    import sync_roster
    mdir = dest / "mosaic"
    mdir.mkdir(parents=True, exist_ok=True)
    dirs = sync_roster.card_dirs()
    rows, missing = [], []
    for slug in slugs:
        art = card_art(dirs[slug], slug)
        if art is None:
            missing.append(slug)
            continue
        _sips(art, mdir / f"{slug}.jpg", 420)
        rows.append((slug, f"mosaic/{slug}.jpg"))
    if missing:
        print(f"  ! no art file, not on the box front: {', '.join(missing)}")
    rows.sort(key=lambda r: r[0] == FEATURE)     # feature LAST = on top
    return rows


CORNERS = ('<i class="cnr tl"></i><i class="cnr tr"></i>'
           '<i class="cnr bl"></i><i class="cnr br"></i>')


def build_tuckbox() -> Path:
    """The pack's outer box, as two full-bleed panels laid out like a retail pack.

    Front: publisher bar, ornate frame, the set's real artwork spilled across a
    dark well, an angled contents burst, and the logo locked up over the foot.
    Back: the actual card fronts, contents copy and a legal strip.

    Both are 816x1110 so they still ride build_print.py and check_bleed.py;
    build_dieline.py places them into the folded box and build_mockup.py
    renders the assembled thing.
    """
    import sync_roster
    from build_card_html import LAB_NAME

    dest = CARDS / "_pack" / "free-systems-tuckbox"
    dest.mkdir(parents=True, exist_ok=True)

    dirs = sync_roster.card_dirs()
    slugs = sync_roster.read_roster()
    seen, labs = set(), []
    for s_ in slugs:
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

    # ---- front
    mosaic = make_mosaic(slugs, dest)
    WELL_W, WELL_H = 706, 800
    pos = scatter(len(mosaic), WELL_W, WELL_H)
    tiles = "".join(
        f'<img src="{rel}" alt="" style="left:{d["left"]}px;top:{d["top"]}px;'
        f'width:{d["w"]}px;height:{d["h"]}px;z-index:{d["z"]};'
        f'transform:rotate({d["rot"]}deg)">'
        for (slug, rel), d in zip(mosaic, pos))

    face = (
        '<div class="face front"><div class="boxpanel boxfront"><div class="pad">'
        '<div class="bar"><span class="lab">FREE SYSTEMS LAB</span>'
        '<span class="ed">FIRST EDITION</span></div>'
        f'<div class="frame">{CORNERS}<div class="well">{tiles}<div class="veil"></div>'
        '<div class="lock"><div class="wm">FREE SYSTEMS</div>'
        '<div class="hair"></div><div class="kick">MODEL CARDS</div></div>'
        '</div></div>'
        f'<div class="contents"><div class="cts">{len(slugs)} CARDS TOTAL '
        f'\u00b7 {len(labs)} LABS</div>'
        f'<div class="labs">{labs_html}</div>'
        '<div class="url">freesystems.net</div></div>'
        '</div><div class="grain"></div></div></div>'
    )

    # ---- back
    lo, hi, spread = spread_figures()
    thumbs = make_thumbs(slugs, dest)
    cards_html = "".join(f'<img src="{rel}" alt="">' for _, rel in thumbs)
    back = (
        '<div class="face back"><div class="boxpanel boxback"><div class="pad">'
        '<div class="bar"><span class="lab">FREE SYSTEMS LAB</span></div>'
        f'<div class="frame">{CORNERS}<div class="well2">'
        # Three blocks, three jobs: the hook, the finding, the small print.
        # They used to say "the lab's own document" three different ways, which
        # read as padding.
        '<div class="blurb">Every frontier model ships with a document<br>'
        'its own lab wrote about it.<br>Almost nobody reads them.</div>'
        f'<div class="grid">{cards_html}</div>'
        f'<div class="note">So we read all {len(slugs)}. They span {spread}\u00d7 in length, '
        f'the shortest {lo:,} words and the longest {hi:,}. '
        'What a lab chose not to measure is printed too.</div>'
        '</div></div>'
        '<div class="legal"><div class="bc">BARCODE / EAN-13</div>'
        f'<div class="lgl"><b>{len(slugs)} CARDS \u00b7 {len(labs)} LABS</b>'
        'Free Systems Lab \u00b7 Stanford GSB. Scores are self-reported and printed with '
        'the variant named. Not affiliated with any lab listed.<br>freesystems.net</div></div>'
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
    print(f"  box front: {len(mosaic)} real artworks scattered, feature = {FEATURE}")
    print(f"  box back : {len(thumbs)}/{len(slugs)} card fronts")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    p = build(n)
    build_tuckbox()
    print(f"  wrote {p}")
    print(f"  hero art: {'present' if (DEST/'art'/'hero.png').exists() else 'PENDING — placeholder shown'}")

