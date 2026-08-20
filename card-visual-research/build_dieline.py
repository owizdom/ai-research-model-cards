#!/usr/bin/env python3
"""Compose the two printed box panels into a flat tuck box dieline.

The cards and the box panels are card-shaped files that ride build_print.py. A
box is not a card: to actually make one, a printer needs the flat shape, with
every panel, flap and glue tab in place and the fold lines marked. This builds
that from the same two rendered panels, so the box and its artwork cannot drift
apart.

Straight tuck end. Both tuck flaps hinge off the back panel, which leaves the
front face unbroken; that is the usual choice for retail.

Panel strip, left to right:

    +--------+------+--------+------+-----+
    |  BACK  | SIDE | FRONT  | SIDE | TAB |
    +--------+------+--------+------+-----+

with tuck flaps above and below BACK, dust flaps above and below both SIDEs,
and nothing above or below FRONT (those two edges are die cut, so the front
panel artwork bleeds there).

    python3 build_dieline.py                  # artwork + guides + pdf + spec
    python3 build_dieline.py --stock-mm 0.40  # thicker stock, deeper box
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import build_print

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "print" / "dieline"
CHROME = build_print.CHROME
DPI = 300

# The panel files this places. Both are 816x1110 with a 744x1038 trim, so each
# already carries 36px = 3.05mm of bleed on every side, which is exactly what
# the die-cut edges need.
PANEL_W_PX, PANEL_H_PX = build_print.BLEED_W, build_print.BLEED_H
TRIM_W_PX, TRIM_H_PX = build_print.CUT_W, build_print.CUT_H
TRIM_OFF_X = (PANEL_W_PX - TRIM_W_PX) / 2
TRIM_OFF_Y = (PANEL_H_PX - TRIM_H_PX) / 2


def px(mm: float) -> float:
    return mm / 25.4 * DPI


class Geometry:
    """Every dimension derived, so changing the stock changes the box."""

    def __init__(self, cards: int, stock_mm: float, slack_mm: float,
                 fit_mm: float, tab_mm: float, bleed_mm: float):
        self.cards, self.stock_mm, self.slack_mm = cards, stock_mm, slack_mm
        # The card trim is the print pipeline's, not a guess.
        self.card_w = TRIM_W_PX / DPI * 25.4
        self.card_h = TRIM_H_PX / DPI * 25.4
        self.W = round(self.card_w + fit_mm, 1)          # panel width
        self.H = round(self.card_h + fit_mm, 1)          # panel height
        self.D = round(cards * stock_mm + slack_mm, 1)   # depth = the deck
        self.TAB = tab_mm
        self.TUCK = round(self.D + 3, 1)                 # tuck flap + nose
        self.DUST = round(self.D - 2, 1)                 # dust flaps sit shorter
        # Euro hang tab: an extension of the top tuck flap, creased at its base,
        # so it stands above the closed box on a peg. Every reference pack has
        # one. Narrower than the panel so it clears the box mouth.
        self.HANG = 16.0
        self.TAB_W = round(self.W * 0.96, 1)
        self.B = bleed_mm

        # x edges of the five panels
        self.x_back = 0.0
        self.x_side1 = self.W
        self.x_front = self.W + self.D
        self.x_side2 = self.W + self.D + self.W
        self.x_tab = self.W + self.D + self.W + self.D
        self.strip_w = self.x_tab + self.TAB
        self.strip_h = self.HANG + self.TUCK + self.H + self.TUCK
        self.y_hinge = self.HANG                        # tab folds here
        self.y_top = self.HANG + self.TUCK              # top crease
        self.y_bot = self.HANG + self.TUCK + self.H     # bottom crease

        self.canvas_w = self.strip_w + 2 * self.B
        self.canvas_h = self.strip_h + 2 * self.B

    # die outline, clockwise, in strip coordinates (mm)
    def outline(self) -> list[tuple[float, float]]:
        W, D, TAB, T, H = self.W, self.D, self.TAB, self.TUCK, self.H
        yt, yb = self.y_top, self.y_bot
        dust_t, dust_b = yt - self.DUST, yb + self.DUST
        x1, x2, x3, x4 = self.x_side1, self.x_front, self.x_side2, self.x_tab
        c = 3.0                      # chamfer on the free corners
        ti = 1.5                     # glue tab sits shorter than the panel
        tl = (W - self.TAB_W) / 2    # hang tab, centred on the back panel
        tr = W - tl
        return [
            (0, yt), (1, yt), (1, self.HANG),
            (tl, self.HANG), (tl, c), (tl + c, 0), (tr - c, 0), (tr, c), (tr, self.HANG),
            (W - 1, self.HANG), (W - 1, yt),
            (x1, yt), (x1, dust_t), (x2, dust_t), (x2, yt),
            (x3, yt), (x3, dust_t), (x4, dust_t), (x4, yt),
            (x4, yt + ti), (self.strip_w - c, yt + ti),
            (self.strip_w, yt + ti + c), (self.strip_w, yb - ti - c),
            (self.strip_w - c, yb - ti), (x4, yb - ti),
            (x4, yb), (x4, dust_b), (x3, dust_b), (x3, yb),
            (x2, yb), (x2, dust_b), (x1, dust_b), (x1, yb),
            (W - 1, yb), (W - 1, self.strip_h - c), (W - 1 - c, self.strip_h),
            (1 + c, self.strip_h), (1, self.strip_h - c), (1, yb), (0, yb),
        ]

    def creases(self) -> list[tuple[float, float, float, float]]:
        yt, yb = self.y_top, self.y_bot
        v = [(x, yt, x, yb) for x in (self.x_side1, self.x_front, self.x_side2, self.x_tab)]
        h = [(1, yt, self.x_tab, yt), (1, yb, self.x_tab, yb),
             ((self.W - self.TAB_W) / 2, self.HANG,
              (self.W + self.TAB_W) / 2, self.HANG)]
        return v + h


CSS = """
/* Parchment, not black: the panels match the cards now, so the spines, flaps
   and tab have to as well. Light board also does not crack white along the six
   creases the way a solid dark box does. */
html,body{margin:0;padding:0;background:#efe4c8}
.sheet{position:relative;overflow:hidden;
  background:linear-gradient(158deg,#f5edd8 0%,#ece0c0 54%,#e2d2a8 100%)}
.panel{position:absolute;overflow:hidden}
.panel img{position:absolute;display:block}
.flat{position:absolute;background:linear-gradient(158deg,#f2e8cf,#e6d9b6)}
.spine{position:absolute;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(90deg,#e4d5ae,#f3ebd6 50%,#e4d5ae)}
.spine span{white-space:nowrap;font-family:'JetBrains Mono',monospace;font-weight:600;
  color:#5a3d1c;transform:rotate(90deg)}
.tuck{position:absolute;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(180deg,#f3ebd6,#e6d9b6)}
.tuck span{font-family:'Cinzel',serif;font-weight:700;color:#8a6414;white-space:nowrap}
.tuck.bottom{background:linear-gradient(0deg,#f3ebd6,#e6d9b6)}
.tuck.bottom span{font-family:'JetBrains Mono',monospace;font-weight:600;color:#8a6836}
svg.guides{position:absolute;left:0;top:0;pointer-events:none}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&'
         'family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">')


def panel_div(g: Geometry, img: Path, x_mm: float, y_mm: float,
              bleed_left=False, bleed_right=False,
              bleed_top=False, bleed_bottom=False) -> str:
    """Place a 816x1110 panel so its TRIM maps onto the panel rectangle.

    The clip box is the panel rectangle, grown only on the edges that are die
    cut. Growing every edge would overprint the neighbouring panel across an
    internal crease; growing none would leave the cut edges short of bleed.
    """
    sx = px(g.W) / TRIM_W_PX
    sy = px(g.H) / TRIM_H_PX
    L = px(g.B) if bleed_left else 0.0
    R = px(g.B) if bleed_right else 0.0
    T = px(g.B) if bleed_top else 0.0
    Bm = px(g.B) if bleed_bottom else 0.0
    cx, cy = px(g.B + x_mm) - L, px(g.B + y_mm) - T
    cw, ch = px(g.W) + L + R, px(g.H) + T + Bm
    return (
        f'<div class="panel" style="left:{cx:.2f}px;top:{cy:.2f}px;'
        f'width:{cw:.2f}px;height:{ch:.2f}px">'
        f'<img src="{img.as_uri()}" style="left:{L - TRIM_OFF_X * sx:.2f}px;'
        f'top:{T - TRIM_OFF_Y * sy:.2f}px;'
        f'width:{PANEL_W_PX * sx:.2f}px;height:{PANEL_H_PX * sy:.2f}px">'
        "</div>"
    )


def rect(cls: str, g: Geometry, x, y, w, h, inner: str = "", style: str = "") -> str:
    return (f'<div class="{cls}" style="left:{px(g.B + x):.2f}px;top:{px(g.B + y):.2f}px;'
            f'width:{px(w):.2f}px;height:{px(h):.2f}px;{style}">{inner}</div>')


def guides_svg(g: Geometry) -> str:
    o = px(g.B)
    pts = " ".join(f"{o + px(x):.2f},{o + px(y):.2f}" for x, y in g.outline())
    creases = "".join(
        f'<line x1="{o + px(a):.2f}" y1="{o + px(b):.2f}" '
        f'x2="{o + px(c):.2f}" y2="{o + px(d):.2f}" stroke="#2b6cff" '
        f'stroke-width="2" stroke-dasharray="12 8"/>'
        for a, b, c, d in g.creases())
    # Watermark every panel rather than labelling two of them above the crease,
    # where the label landed on the tuck flap's own wordmark.
    labels = ""
    panels = (("BACK", g.x_back, g.x_side1), ("SIDE", g.x_side1, g.x_front),
              ("FRONT", g.x_front, g.x_side2), ("SIDE", g.x_side2, g.x_tab),
              ("GLUE TAB", g.x_tab, g.strip_w))
    for name, x0, x1 in panels:
        cxm, cym = (x0 + x1) / 2, (g.y_top + g.y_bot) / 2
        narrow = (x1 - x0) < g.W / 2
        size = 34 if narrow else 62
        rot = f' transform="rotate(90 {o + px(cxm):.1f} {o + px(cym):.1f})"' if narrow else ""
        labels += (f'<text x="{o + px(cxm):.1f}" y="{o + px(cym):.1f}"{rot} '
                   f'fill="#2b6cff" font-family="monospace" font-size="{size}" '
                   f'text-anchor="middle" opacity=".30">{name}</text>')
    # the euro hole, punched in the hang tab
    hw, hh = g.W * 0.30, 5.0
    hx, hy = g.W / 2 - hw / 2, g.HANG * 0.30
    hole = (f'<rect x="{o + px(hx):.1f}" y="{o + px(hy):.1f}" '
            f'width="{px(hw):.1f}" height="{px(hh):.1f}" rx="{px(hh / 2):.1f}" '
            f'fill="none" stroke="#ff2d2d" stroke-width="2.5"/>')
    return (f'<svg class="guides" width="{px(g.canvas_w):.0f}" height="{px(g.canvas_h):.0f}">'
            f'<polygon points="{pts}" fill="none" stroke="#ff2d2d" stroke-width="2.5"/>'
            f"{creases}{hole}{labels}</svg>")


def build_html(g: Geometry, front: Path, back: Path, guides: bool) -> str:
    body = [f'<div class="sheet" style="width:{px(g.canvas_w):.2f}px;'
            f'height:{px(g.canvas_h):.2f}px">']

    # flaps and tab first, so panel artwork sits over them at the creases
    body.append(rect("flat", g, (g.W - g.TAB_W) / 2, 0, g.TAB_W, g.HANG))
    body.append(rect("flat", g, 1, g.y_hinge, g.W - 2, g.TUCK))
    body.append(rect("flat", g, 1, g.y_bot, g.W - 2, g.TUCK))
    for x in (g.x_side1, g.x_side2):
        body.append(rect("flat", g, x, g.y_top - g.DUST, g.D, g.DUST))
        body.append(rect("flat", g, x, g.y_bot, g.D, g.DUST))
    body.append(rect("flat", g, g.x_tab, g.y_top + 1.5, g.TAB, g.H - 3))

    # the two printed faces
    body.append(panel_div(g, back, g.x_back, g.y_top, bleed_left=True))
    body.append(panel_div(g, front, g.x_front, g.y_top, bleed_top=True, bleed_bottom=True))

    # spines: same copy on both, so the box reads whichever way it is shelved
    spine = "FREE SYSTEMS &middot; MODEL CARDS &middot; SET 01 &middot; %d CARDS" % g.cards
    fs = max(16, min(30, px(g.D) * 0.26))
    for x in (g.x_side1, g.x_side2):
        body.append(rect("spine", g, x, g.y_top, g.D, g.H,
                         f'<span style="font-size:{fs:.1f}px;letter-spacing:.14em">{spine}</span>'))

    # the top tuck is the visible top face once the box is closed
    body.append(rect("tuck", g, 1, g.y_hinge, g.W - 2, g.TUCK,
                     f'<span style="font-size:{px(g.TUCK) * 0.30:.1f}px;'
                     f'letter-spacing:.12em">FREE SYSTEMS</span>'))
    body.append(rect("tuck bottom", g, 1, g.y_bot, g.W - 2, g.TUCK,
                     f'<span style="font-size:{px(g.TUCK) * 0.20:.1f}px;'
                     f'letter-spacing:.16em">freesystems.net</span>'))

    if guides:
        body.append(guides_svg(g))
    body.append("</div>")

    page = (f"@page{{size:{g.canvas_w}mm {g.canvas_h}mm;margin:0}}"
            f"body{{width:{px(g.canvas_w):.2f}px;height:{px(g.canvas_h):.2f}px}}")
    return ('<!DOCTYPE html><html><head><meta charset="UTF-8">' + FONTS
            + "<style>" + CSS + page + "</style></head><body>"
            + "".join(body) + "</body></html>")


def shoot(html: Path, out: Path, g: Geometry, pdf: bool = False) -> bool:
    cmd = [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", "--allow-file-access-from-files",
           "--virtual-time-budget=12000"]
    if pdf:
        cmd += [f"--print-to-pdf={out}", "--no-pdf-header-footer"]
    else:
        cmd += [f"--window-size={round(px(g.canvas_w))},{round(px(g.canvas_h))}",
                f"--screenshot={out}"]
    cmd.append(html.as_uri())
    subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return out.exists()


def spec_text(g: Geometry, files: list[str]) -> str:
    return f"""FREE SYSTEMS · MODEL CARDS · SET 01
Tuck box dieline specification

STYLE            straight tuck end (both tuck flaps hinge off the back panel,
                 so the front face is unbroken)

CARD TRIM        {g.card_w:.2f} x {g.card_h:.2f} mm  ({TRIM_W_PX} x {TRIM_H_PX} px @ {DPI}dpi)
CARDS            {g.cards}

PANEL W x H      {g.W} x {g.H} mm      (card trim + {g.W - g.card_w:.1f}mm fit)
DEPTH            {g.D} mm              ({g.cards} x {g.stock_mm}mm stock + {g.slack_mm}mm slack)
GLUE TAB         {g.TAB} mm
TUCK FLAP        {g.TUCK} mm           (depth + 3mm nose)
HANG TAB         {g.HANG} mm x {g.TAB_W} mm  (euro hole, creased at its base off
                 the top tuck flap, so it stands above the closed box)
DUST FLAP        {g.DUST} mm           (depth - 2mm)

FLAT STRIP       {g.strip_w} x {g.strip_h} mm
BLEED            {g.B} mm all round
ARTWORK FILE     {g.canvas_w} x {g.canvas_h} mm = {round(px(g.canvas_w))} x {round(px(g.canvas_h))} px @ {DPI}dpi

PANEL ORDER      BACK | SIDE | FRONT | SIDE | TAB
                 x = 0 | {g.x_side1} | {g.x_front} | {g.x_side2} | {g.x_tab} mm from the strip's left edge
                 panels run y = {g.y_top} to {g.y_bot} mm from the strip's top edge

STOCK ASSUMPTION
  Depth is computed as cards x stock + slack. The default stock is
  {g.stock_mm}mm. If the printer's board differs, regenerate:
      python3 build_dieline.py --stock-mm <value>
  0.31mm gives {g.cards * 0.31 + g.slack_mm:.2f}mm, 0.35mm gives {g.cards * 0.35 + g.slack_mm:.2f}mm.

FILES
{chr(10).join('  ' + f for f in files)}

NOTES
  Red solid = cut. Blue dashed = crease. The guides file is for checking only;
  print from the artwork file.
  The front and back panels carry {TRIM_OFF_X:.0f}px of bleed each side already, placed on the
  die-cut edges only (back panel left, front panel top and bottom). Internal
  creases are butt joins so no artwork crosses them.
"""


def main(argv: list[str]) -> int:
    import sync_roster

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cards", type=int, default=None, help="default: the roster length")
    ap.add_argument("--stock-mm", type=float, default=0.33)
    ap.add_argument("--slack-mm", type=float, default=1.5)
    ap.add_argument("--fit-mm", type=float, default=1.0, help="panel over card trim")
    ap.add_argument("--tab-mm", type=float, default=12.0)
    ap.add_argument("--bleed-mm", type=float, default=3.0)
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args(argv)

    cards = a.cards if a.cards is not None else len(sync_roster.read_roster())
    g = Geometry(cards, a.stock_mm, a.slack_mm, a.fit_mm, a.tab_mm, a.bleed_mm)

    front = ROOT / "print" / "free-systems-tuckbox_front.jpg"
    back = ROOT / "print" / "free-systems-tuckbox_back.jpg"
    for f in (front, back):
        if not f.exists():
            sys.exit(f"missing {f.name} — run build_print.py free-systems-tuckbox first")

    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for label, guides in (("dieline", False), ("dieline-guides", True)):
        html = OUT / f"_{label}.html"
        html.write_text(build_html(g, front, back, guides))
        outp = OUT / f"{label}.png"
        if not shoot(html, outp, g):
            sys.exit(f"chrome produced no {outp.name}")
        written.append(outp)

    if not a.no_pdf:
        html = OUT / "_dieline.html"
        pdf = OUT / "dieline.pdf"
        if shoot(html, pdf, g, pdf=True):
            written.append(pdf)
        else:
            print("  ! chrome produced no pdf; png is still valid")

    names = [f.name for f in written] + ["BOX-SPEC.txt"]
    (OUT / "BOX-SPEC.txt").write_text(spec_text(g, names))

    print(f"box     : {g.W} x {g.H} x {g.D} mm  ({cards} cards @ {a.stock_mm}mm + {a.slack_mm}mm slack)")
    print(f"flat    : {g.strip_w} x {g.strip_h} mm, {g.B}mm bleed")
    print(f"artwork : {round(px(g.canvas_w))} x {round(px(g.canvas_h))} px @ {DPI}dpi")
    for f in written:
        print(f"  wrote {f.relative_to(ROOT)}  ({f.stat().st_size / 1e6:.2f} MB)")
    print(f"  wrote {(OUT / 'BOX-SPEC.txt').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
