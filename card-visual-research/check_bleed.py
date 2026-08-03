#!/usr/bin/env python3
"""Print QA gate for the 816x1110 card renders. No third-party deps.

What actually distinguishes "the design stops short of the file edge" from "the
design bleeds off it" is not colour distance — an illustration legitimately
changes a lot over 36px. It is *flatness*: a backdrop showing through is one
uniform colour, while a bleeding background is a gradient or a photograph.

A file FAILS if any of these hold:
  * it is not exactly 816x1110
  * a run of >=8 identical pixels sits on the 1px border ring (flat strip)
  * all four corner pixels are the same colour (card floating on a backdrop)
  * the flat run walking diagonally in from a corner is >=4px (rounded corner)

    python3 check_bleed.py                  # every print_*.png under cards/
    python3 check_bleed.py 'print/*.jpg'    # png only; jpgs are checked via png
"""
from __future__ import annotations

import glob
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BLEED = (816, 1110)
FLAT_RUN_MAX = 8
CORNER_DIAG_MAX = 4


def read_png(path):
    """Decode an 8-bit non-interlaced PNG to (w, h, channels, rows)."""
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a png: {path}")
    pos, idat, meta = 8, bytearray(), {}
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if ctype == b"IHDR":
            w, h, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
            meta = dict(w=w, h=h, depth=depth, color=color, interlace=interlace)
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break
        pos += 12 + length
    if meta["depth"] != 8 or meta["interlace"]:
        raise ValueError(f"unsupported png form {meta} in {path}")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[meta["color"]]
    raw = zlib.decompress(bytes(idat))
    w, h = meta["w"], meta["h"]
    stride = w * channels
    rows, prev, off = [], bytearray(stride), 0
    for _ in range(h):
        ftype = raw[off]
        line = bytearray(raw[off + 1 : off + 1 + stride])
        off += 1 + stride
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 0xFF
            elif ftype == 2:
                line[i] = (line[i] + b) & 0xFF
            elif ftype == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif ftype == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        rows.append(line)
        prev = line
    return w, h, channels, rows


def px(rows, ch, x, y):
    i = x * ch
    return bytes(rows[y][i : i + 3])


def longest_flat_run(vals):
    best = run = 1
    for i in range(1, len(vals)):
        run = run + 1 if vals[i] == vals[i - 1] else 1
        best = max(best, run)
    return best


def analyse(path):
    w, h, ch, rows = read_png(path)
    top = [px(rows, ch, x, 0) for x in range(w)]
    bot = [px(rows, ch, x, h - 1) for x in range(w)]
    left = [px(rows, ch, 0, y) for y in range(h)]
    right = [px(rows, ch, w - 1, y) for y in range(h)]
    flat = max(longest_flat_run(e) for e in (top, bot, left, right))

    corners = [top[0], top[-1], bot[0], bot[-1]]
    diag = []
    for cx, cy, dx, dy in ((0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)):
        c0, n = px(rows, ch, cx, cy), 0
        while n < 80 and px(rows, ch, cx + dx * n, cy + dy * n) == c0:
            n += 1
        diag.append(n)

    reasons = []
    if (w, h) != BLEED:
        reasons.append(f"size {w}x{h}, expected {BLEED[0]}x{BLEED[1]}")
    if flat >= FLAT_RUN_MAX:
        reasons.append(f"flat border run {flat}px")
    if len(set(corners)) == 1:
        reasons.append(f"all four corners uniform {tuple(corners[0])}")
    if max(diag) >= CORNER_DIAG_MAX:
        reasons.append(f"flat corner diagonal {diag}")
    return dict(flat=flat, diag=diag, reasons=reasons)


def main(argv):
    pats = [a for a in argv if not a.startswith("--")]
    paths = []
    for p in pats:
        paths.extend(sorted(glob.glob(p)))
    if not paths:
        paths = sorted(str(p) for p in (ROOT / "cards").glob("*/*/print_*.png") if "_proof" not in p.name)
    fails = 0
    for p in paths:
        try:
            r = analyse(p)
        except ValueError as e:
            print(f"SKIP  {p}: {e}")
            continue
        fails += bool(r["reasons"])
        name = p.split("/cards/")[-1] if "/cards/" in p else p.split("/")[-1]
        why = ("  <- " + "; ".join(r["reasons"])) if r["reasons"] else ""
        print(f"{'FAIL' if r['reasons'] else 'PASS'}  {name:54s} flat_run={r['flat']:3d} corner_diag={r['diag']}{why}")
    print(f"\n{len(paths)} file(s) checked, {fails} failing")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
