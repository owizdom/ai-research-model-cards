#!/usr/bin/env python3
"""Render the assembled tuck box in 3D, the way retail packs are photographed.

build_dieline.py produces the flat shape a printer cuts. That is the right file
to send, and the wrong thing to look at: nobody can tell from a dieline whether
the box works. This folds the same two rendered panels into a box in CSS 3D and
photographs it front and back, so the design can be judged as an object.

Same geometry as build_dieline.py, read from the same Geometry class, so the
mockup cannot drift from the thing being printed.

    python3 build_mockup.py              # front, back and a paired shot
    python3 build_mockup.py --scale 14   # bigger render
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import build_dieline as D

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "print" / "mockup"
CHROME = D.CHROME

# The panels are bleed files; the box shows the trim.
TRIM_W, TRIM_H = D.TRIM_W_PX, D.TRIM_H_PX
OFF_X, OFF_Y = D.TRIM_OFF_X, D.TRIM_OFF_Y

CSS = """
html,body{margin:0;padding:0;background:#f4f4f6;
  font-family:'Jost',system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.stage{display:flex;align-items:center;justify-content:center;gap:VAR_GAPpx;
  width:100%;height:100%}
.slot{position:relative;perspective:2900px;perspective-origin:50% 42%}
.box{position:relative;transform-style:preserve-3d}
.f{position:absolute;left:50%;top:50%;overflow:hidden;backface-visibility:hidden}
.f img{position:absolute;display:block}
.edge{background:linear-gradient(158deg,#f3ebd6,#e2d2a8)}
.spine{display:flex;align-items:center;justify-content:center}
.spine span{white-space:nowrap;font-family:'JetBrains Mono',monospace;font-weight:600;
  color:#5a3d1c;transform:rotate(90deg)}
/* the hang tab, coplanar with the back panel and standing above the box */
.tab{position:absolute;left:50%;top:50%;border-radius:VAR_TABRpx VAR_TABRpx 3px 3px;
  background:linear-gradient(180deg,#f6efdc,#e9dcbb);
  box-shadow:inset 0 0 0 1px rgba(184,144,46,.35)}
.tab .slot-hole{position:absolute;left:50%;top:VAR_HOLETpx;transform:translateX(-50%);
  width:VAR_HOLEWpx;height:VAR_HOLEHpx;border-radius:VAR_HOLEHpx;background:#f4f4f6;
  box-shadow:inset 0 1px 3px rgba(90,61,28,.35)}
.shadow{position:absolute;left:50%;bottom:6%;transform:translateX(-50%) scaleY(.15);
  width:78%;height:26%;border-radius:50%;
  background:radial-gradient(ellipse at 50% 50%,rgba(52,38,16,.42),rgba(52,38,16,0) 68%);
  filter:blur(10px)}
.cap{position:absolute;left:0;right:0;bottom:10px;text-align:center;
  font-family:'JetBrains Mono',monospace;font-size:15px;letter-spacing:.2em;color:#8a7a5c}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&'
         'family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">')


def face_img(img: Path, w: float, h: float) -> str:
    """A panel placed so its TRIM fills the face, the bleed cropped away."""
    sx, sy = w / TRIM_W, h / TRIM_H
    return (f'<img src="{img.as_uri()}" style="left:{-OFF_X * sx:.2f}px;'
            f'top:{-OFF_Y * sy:.2f}px;width:{D.PANEL_W_PX * sx:.2f}px;'
            f'height:{D.PANEL_H_PX * sy:.2f}px">')


def box_html(g: D.Geometry, front: Path, back: Path, s: float,
             ry: float, caption: str) -> str:
    """One box at scale s px/mm, yawed ry degrees."""
    W, H, Dp = g.W * s, g.H * s, g.D * s
    spine_txt = f"FREE SYSTEMS &middot; MODEL CARDS &middot; SET 01 &middot; {g.cards} CARDS"
    fs = max(9, min(19, Dp * 0.24))

    def f(cls, w, h, tf, inner="", extra=""):
        return (f'<div class="f {cls}" style="width:{w:.1f}px;height:{h:.1f}px;'
                f'margin:{-h / 2:.1f}px 0 0 {-w / 2:.1f}px;transform:{tf};{extra}">'
                f'{inner}</div>')

    faces = [
        f("front", W, H, f"translateZ({Dp / 2:.1f}px)", face_img(front, W, H)),
        f("back", W, H, f"rotateY(180deg) translateZ({Dp / 2:.1f}px)", face_img(back, W, H)),
        # side panels: lit slightly differently so the form reads as a solid
        f("edge spine", Dp, H, f"rotateY(90deg) translateZ({W / 2:.1f}px)",
          f'<span style="font-size:{fs:.1f}px;letter-spacing:.12em">{spine_txt}</span>',
          "filter:brightness(.90)"),
        f("edge spine", Dp, H, f"rotateY(-90deg) translateZ({W / 2:.1f}px)",
          f'<span style="font-size:{fs:.1f}px;letter-spacing:.12em">{spine_txt}</span>',
          "filter:brightness(.82)"),
        f("edge", W, Dp, f"rotateX(90deg) translateZ({H / 2:.1f}px)", "",
          "filter:brightness(1.06)"),
        f("edge", W, Dp, f"rotateX(-90deg) translateZ({H / 2:.1f}px)", "",
          "filter:brightness(.86)"),
    ]

    tab_w, tab_h = W * 0.98, g.HANG * s
    tab = (f'<div class="tab" style="width:{tab_w:.1f}px;height:{tab_h:.1f}px;'
           f'margin:{-H / 2 - tab_h:.1f}px 0 0 {-tab_w / 2:.1f}px;'
           f'transform:translateZ({-Dp / 2:.1f}px)">'
           f'<div class="slot-hole"></div></div>')

    slot_h = H + tab_h * 1.18 + H * 0.24
    return (f'<div class="slot" style="width:{W * 1.5:.0f}px;height:{slot_h:.0f}px">'
            f'<div class="shadow"></div>'
            f'<div class="box" style="width:{W:.1f}px;height:{H:.1f}px;'
            f'margin:{tab_h * 1.18:.0f}px auto 0;'
            f'transform:rotateX(-7deg) rotateY({ry}deg)">'
            f'{tab}{"".join(faces)}</div>'
            f'<div class="cap">{caption}</div></div>')


def page(g: D.Geometry, front: Path, back: Path, s: float, views: list) -> str:
    W, H = g.W * s, g.H * s
    tab_h = g.HANG * s
    css = (CSS.replace("VAR_GAP", f"{W * 0.34:.0f}")
              .replace("VAR_TABR", f"{min(26, tab_h * 0.42):.0f}")
              .replace("VAR_HOLEW", f"{W * 0.30:.0f}")
              .replace("VAR_HOLEH", f"{max(8, tab_h * 0.22):.0f}")
              .replace("VAR_HOLET", f"{tab_h * 0.30:.0f}"))
    boxes = "".join(box_html(g, front, back, s, ry, cap) for ry, cap in views)
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8">' + FONTS
            + "<style>" + css + "</style></head><body>"
            + f'<div class="stage">{boxes}</div></body></html>')


def shoot(html: Path, out: Path, w: int, h: int) -> bool:
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--allow-file-access-from-files",
                    f"--window-size={w},{h}", "--virtual-time-budget=14000",
                    "--default-background-color=fff4f4f6",
                    f"--screenshot={out}", html.as_uri()],
                   capture_output=True, text=True, timeout=300)
    return out.exists()


def main(argv: list[str]) -> int:
    import sync_roster

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scale", type=float, default=11.0, help="px per mm")
    ap.add_argument("--stock-mm", type=float, default=0.33)
    ap.add_argument("--slack-mm", type=float, default=1.5)
    a = ap.parse_args(argv)

    cards = len(sync_roster.read_roster())
    g = D.Geometry(cards, a.stock_mm, a.slack_mm, 1.0, 12.0, 3.0)

    front = ROOT / "print" / "free-systems-tuckbox_front.jpg"
    back = ROOT / "print" / "free-systems-tuckbox_back.jpg"
    for f in (front, back):
        if not f.exists():
            sys.exit(f"missing {f.name} — run build_print.py free-systems-tuckbox first")

    OUT.mkdir(parents=True, exist_ok=True)
    s = a.scale
    W, H, tab = g.W * s, g.H * s, g.HANG * s

    jobs = [
        ("mockup-front", [(-32, "FRONT")], 1),
        ("mockup-back", [(-148, "BACK")], 1),
        ("mockup-pair", [(-30, "FRONT"), (-150, "BACK")], 2),
    ]
    written = []
    for name, views, n in jobs:
        html = OUT / f"_{name}.html"
        html.write_text(page(g, front, back, s, views))
        w = int(W * 1.5 * n + W * 0.34 * (n - 1) + 120)
        h = int(H + tab * 1.18 + H * 0.24 + 110)
        out = OUT / f"{name}.png"
        if not shoot(html, out, w, h):
            sys.exit(f"chrome produced no {out.name}")
        written.append(out)

    print(f"box  : {g.W} x {g.H} x {g.D} mm, hang tab {g.HANG} mm, at {s:g} px/mm")
    for f in written:
        print(f"  wrote {f.relative_to(ROOT)}  ({f.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
