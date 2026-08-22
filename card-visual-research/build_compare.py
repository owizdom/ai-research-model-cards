#!/usr/bin/env python3
"""Side-by-side scratchpad: his card against ours, click to flip.

Every check so far has been mechanical or a screenshot I read once. This is the
one for eyes: his version and ours on the same row, same scale, and one click
flips both faces together so front and back stay in step.

Reads his images straight out of the gallery he sent, in document order, and
ours out of print/. Self-contained, so it opens anywhere.

    python3 build_compare.py
    python3 build_compare.py --gallery ~/Downloads/other.html --width 560
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import sync_roster

ROOT = Path(__file__).resolve().parent
PRINT = ROOT / "print"
GALLERY = Path.home() / "Downloads/complete-24-card-gallery.html"
OUT = Path.home() / "Desktop/compare-his-vs-ours.html"

# His gallery order, confirmed against the labels in the file itself:
# images 0,1 are the pack cover, then 18 existing cards as front/back pairs
# from index 2, then the 6 new cards. Index 20/21 is Mistral 3.1, which we
# parked, so it has no counterpart on our side.
ORDER = [
    ("claude-opus-4-7", "Claude Opus 4.7"), ("claude-opus-4-8", "Claude Opus 4.8"),
    ("claude-mythos-preview", "Claude Mythos Preview"), ("o3", "o3"),
    ("gpt-5", "GPT-5"), ("gpt-5-1", "GPT-5.1"), ("gpt-5-2", "GPT-5.2"),
    ("gpt-5-3", "GPT-5.3"), ("gemini-3-1-pro", "Gemini 3.1 Pro"),
    ("mistral-3-1", "Mistral 3.1"), ("claude-fable-5", "Claude Fable 5"),
    ("claude-sonnet-5", "Claude Sonnet 5"), ("claude-opus-5", "Claude Opus 5"),
    ("gpt-5-5", "GPT-5.5"), ("gpt-5-6-sol", "GPT-5.6 Sol"), ("inkling", "Inkling"),
    ("inkling-small", "Inkling-Small"), ("kimi-k3", "Kimi K3"),
    ("grok-4-6", "Grok 4.6"), ("gpt-5-4", "GPT-5.4"),
    ("muse-spark-1-2", "Muse Spark 1.2"), ("muse-glimmer", "Muse Glimmer"),
    ("mistral-large-3", "Mistral Large 3"), ("le-chaton-fat", "Le Chaton Fat"),
]

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#12100c;color:#e8e2d4;font:14px/1.5 -apple-system,BlinkMacSystemFont,
  'Segoe UI',sans-serif;padding:0 0 80px}
header{position:sticky;top:0;z-index:20;background:#12100cf2;backdrop-filter:blur(8px);
  border-bottom:1px solid #2f2718;padding:14px 22px;display:flex;align-items:center;gap:18px}
h1{font-size:16px;font-weight:650;letter-spacing:.02em;color:#e6c168}
.hint{font-size:12.5px;color:#918872}
button{background:#241d10;color:#e6c168;border:1px solid #4a3c1d;border-radius:6px;
  padding:6px 13px;font:inherit;font-size:12.5px;cursor:pointer}
button:hover{background:#31270f}
.row{display:flex;gap:14px;align-items:flex-start;justify-content:center;
  padding:18px 22px;border-bottom:1px solid #221c11;cursor:pointer}
.row:hover{background:#171309}
.meta{width:170px;flex:0 0 170px;padding-top:6px}
.meta .n{font-size:15px;font-weight:650}
.meta .i{font:11.5px ui-monospace,Menlo,monospace;color:#8a7f66;margin-top:3px}
.meta .s{font:11px ui-monospace,Menlo,monospace;margin-top:8px;color:#6f6653}
.side{position:relative}
.side .lbl{font:11px ui-monospace,Menlo,monospace;letter-spacing:.16em;color:#8a7f66;
  margin-bottom:6px}
.side.ours .lbl{color:#6ea36e}
img{display:block;border-radius:6px;border:1px solid #2f2718;background:#0b0906}
.b{display:none}
.row.flipped .f{display:none}
.row.flipped .b{display:block}
.gap{width:150px;flex:0 0 150px;display:flex;align-items:center;justify-content:center;
  color:#5c5443;font:11px ui-monospace,monospace;text-align:center;padding-top:60px}
"""

JS = """
function flip(el){el.classList.toggle('flipped')}
function all(state){document.querySelectorAll('.row').forEach(r=>
  r.classList.toggle('flipped', state))}
document.addEventListener('keydown', e=>{
  if(e.key==='f') all(true); if(e.key==='b') all(false);
});
"""


def b64(path: Path, width: int) -> str | None:
    if not path or not path.exists():
        return None
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "s.jpg"
        subprocess.run(["sips", "-Z", str(width), str(path), "--out", str(out)],
                       check=True, capture_output=True)
        return base64.b64encode(out.read_bytes()).decode()


def tag(data: str | None, cls: str, show: int, missing: str) -> str:
    if not data:
        return (f'<div class="{cls}" style="width:{show}px;height:{int(show*1.36)}px;'
                f'display:flex;align-items:center;justify-content:center;color:#7a6f58;'
                f'border:1px dashed #3a3020;border-radius:6px;font-size:12px">{missing}</div>')
    return f'<img class="{cls}" src="data:image/jpeg;base64,{data}" style="width:{show}px">'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gallery", type=Path, default=GALLERY)
    ap.add_argument("--width", type=int, default=620, help="embedded width")
    ap.add_argument("--show", type=int, default=330, help="displayed width")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)

    if not a.gallery.exists():
        sys.exit(f"no gallery at {a.gallery}")
    imgs = re.findall(r'data:image/\w+;base64,([A-Za-z0-9+/=]+)', a.gallery.read_text())
    print(f"  his gallery: {len(imgs)} images")

    roster = set(sync_roster.read_roster())
    dirs = sync_roster.card_dirs()
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for i, (slug, name) in enumerate(ORDER):
            hf, hb = 2 + i * 2, 3 + i * 2          # his front, his back
            his_f = imgs[hf] if hf < len(imgs) else None
            his_b = imgs[hb] if hb < len(imgs) else None

            ours_f = b64(PRINT / f"{slug}_front.jpg", a.width)
            ours_b = b64(PRINT / f"{slug}_back.jpg", a.width)

            status = "in the deck" if slug in roster else "PARKED, not in the 23"
            num = ""
            if slug in roster:
                num = f"{sync_roster.read_roster().index(slug) + 1:03d}/023"

            rows.append(
                f'<div class="row" onclick="flip(this)">'
                f'<div class="meta"><div class="n">{name}</div>'
                f'<div class="i">his {i+1:03d}/024{"  ·  ours " + num if num else ""}</div>'
                f'<div class="s">{status}</div></div>'
                f'<div class="side"><div class="lbl">HIS</div>'
                f'{tag(his_f, "f", a.show, "no image")}{tag(his_b, "b", a.show, "no image")}</div>'
                f'<div class="side ours"><div class="lbl">OURS</div>'
                f'{tag(ours_f, "f", a.show, "not in our deck")}'
                f'{tag(ours_b, "b", a.show, "not in our deck")}</div>'
                f"</div>")

    doc = ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           "<title>His vs ours — SET 01</title>"
           f"<style>{CSS}</style></head><body>"
           '<header><h1>His gallery vs our deck</h1>'
           '<span class="hint">click any row to flip that card front &harr; back</span>'
           '<button onclick="all(true)">all backs (f)</button>'
           '<button onclick="all(false)">all fronts (b)</button></header>'
           + "".join(rows)
           + f"<script>{JS}</script></body></html>")
    a.out.write_text(doc)
    print(f"  wrote {a.out}  ({a.out.stat().st_size / 1e6:.1f} MB)")
    print(f"  {len(ORDER)} rows, click to flip, f = all backs, b = all fronts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
