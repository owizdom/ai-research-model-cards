#!/usr/bin/env python3
"""One self-contained HTML of the whole pack, for sending to someone.

cards/index.html is the working gallery: it embeds each card's live HTML so the
faces flip and the CSS is the real CSS. That is the right tool for checking a
change and the wrong thing to send, because it needs the repo around it for art
and thumbnails.

This is the send-it version, built the way James's own gallery was: every face
as a base64 JPEG in a single file that opens anywhere with nothing alongside it.

    python3 build_share.py                  # ~/Desktop/free-systems-gallery.html
    python3 build_share.py --width 900      # larger images, larger file
    python3 build_share.py --out /tmp/g.html
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import sync_roster

ROOT = Path(__file__).resolve().parent
PRINT = ROOT / "print"
DEFAULT_OUT = Path.home() / "Desktop/free-systems-gallery.html"

CSS = """
:root{--cream:#f5edd8;--cream2:#ece0c0;--ink:#241606;--ink2:#5a3d1c;--ink3:#8a6836;
  --gold:#f2d275;--gold2:#dcab44}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#14100a;color:var(--cream);
  font-family:'Jost',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  padding:38px 26px 70px;-webkit-font-smoothing:antialiased}
h1{font-family:Georgia,'Times New Roman',serif;font-size:27px;font-weight:700;
  letter-spacing:.04em;text-align:center;color:var(--gold);margin-bottom:6px}
.sub{text-align:center;font-family:ui-monospace,Menlo,monospace;font-size:12px;
  letter-spacing:.18em;color:var(--ink3);margin-bottom:34px}
h2{font-family:ui-monospace,Menlo,monospace;font-size:13px;font-weight:600;
  letter-spacing:.22em;color:var(--gold2);margin:40px 0 16px;
  padding-bottom:8px;border-bottom:1px solid #33280f}
.grid{display:flex;flex-wrap:wrap;gap:26px;justify-content:center}
.card{background:#1c1710;border:1px solid #33280f;border-radius:10px;padding:12px}
.cap{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--cream2);
  display:flex;justify-content:space-between;gap:14px;padding:2px 2px 10px}
.cap .n{color:var(--ink3)}
.pair{display:flex;gap:10px}
.pair img{display:block;border-radius:5px;background:#0d0a06}
.solo{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.note{max-width:760px;margin:26px auto 0;font-size:14px;line-height:1.6;
  color:var(--ink3);text-align:center}
"""


def b64(path: Path, width: int) -> str | None:
    """JPEG at `width` px wide, base64. sips, same as the rest of the toolchain."""
    if not path.exists():
        return None
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "s.jpg"
        subprocess.run(["sips", "-Z", str(width), str(path), "--out", str(out)],
                       check=True, capture_output=True)
        return base64.b64encode(out.read_bytes()).decode()


def img(path: Path, width: int, show: int) -> str:
    d = b64(path, width)
    if not d:
        return f'<div style="color:#a55">missing {path.name}</div>'
    return f'<img src="data:image/jpeg;base64,{d}" style="width:{show}px">'


def pair(slug: str, width: int, show: int) -> str:
    return (f'<div class="pair">{img(PRINT / f"{slug}_front.jpg", width, show)}'
            f'{img(PRINT / f"{slug}_back.jpg", width, show)}</div>')


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--width", type=int, default=730, help="embedded image width")
    ap.add_argument("--show", type=int, default=300, help="displayed width")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args(argv)

    dirs = sync_roster.card_dirs()
    roster = sync_roster.read_roster()
    n = len(roster)

    body = [f"<h1>Free Systems &middot; Model Cards &middot; SET 01</h1>",
            f'<div class="sub">{n} CARDS &middot; FRONT AND BACK &middot; 816&times;1110 @ 300DPI</div>']

    # the box, first, the way a pack is seen
    body.append("<h2>THE PACK</h2><div class=\"grid\">")
    body.append('<div class="card"><div class="cap"><span>Tuck box</span>'
                '<span class="n">front / back</span></div>'
                + pair("free-systems-tuckbox", a.width, a.show) + "</div>")
    mock = PRINT / "mockup" / "mockup-pair.png"
    if mock.exists():
        body.append('<div class="card"><div class="cap"><span>Assembled box</span>'
                    '<span class="n">3D render</span></div>'
                    f'<div class="solo">{img(mock, a.width * 2, a.show * 2)}</div></div>')
    body.append("</div>")

    body.append("<h2>ABOUT CARD</h2><div class=\"grid\">")
    body.append('<div class="card"><div class="cap"><span>Free Systems</span>'
                '<span class="n">00 &middot; about / contents</span></div>'
                + pair("free-systems-cover", a.width, a.show) + "</div>")
    body.append("</div>")

    body.append(f"<h2>THE {n} CARDS</h2><div class=\"grid\">")
    for i, slug in enumerate(roster, 1):
        c = json.loads((dirs[slug] / "card.json").read_text())
        name = c.get("name") or slug
        body.append('<div class="card"><div class="cap">'
                    f'<span>{name}</span><span class="n">{i:03d}/{n:03d}</span></div>'
                    + pair(slug, a.width, a.show) + "</div>")
    body.append("</div>")

    body.append('<div class="note">Every figure is read from the model\'s own '
                'published document. What a lab chose not to measure is printed too.</div>')

    doc = ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           f"<title>Free Systems — Model Cards — SET 01 — {n} cards</title>"
           f"<style>{CSS}</style></head><body>" + "".join(body) + "</body></html>")

    a.out.write_text(doc)
    print(f"  wrote {a.out}  ({a.out.stat().st_size / 1e6:.1f} MB)")
    print(f"  {n} cards, front and back, plus the tuck box and the About card")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
