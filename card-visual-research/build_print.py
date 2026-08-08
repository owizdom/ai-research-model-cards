#!/usr/bin/env python3
"""Render every TCG card to a print-ready 816x1110 file with full bleed.

MPC American poker size @300DPI, per their template:

    bleed (full file)   816 x 1110   design must fill to here
    cut  (finished)     744 x 1038   where the blade lands, +/- drift
    safe (keep text in) 684 x  981

The earlier renders scaled the card frame to *exactly* the bleed box, so the
rounded frame corners left 192 border pixels of flat backdrop and the frame
itself sat on the cut line. Here the backgrounds are the bleed layers — the
parchment fills the whole canvas and the dark illustration panel runs off the
top and both sides — and the gold frame floats inside, clear of any drift.

Source of truth is each card's committed <slug>.html; this only re-wraps it.

    python3 build_print.py                 # all cards -> png + jpg + deck
    python3 build_print.py claude-4-6      # one card
    python3 build_print.py --guides claude-4-6   # proof with trim/safe overlay
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "cards"
PRINT_DIR = ROOT / "print"
DECK_DIR = Path.home() / "Desktop/docs/stanford/model-cards-deck"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# ---------------------------------------------------------------- geometry --
BLEED_W, BLEED_H = 816, 1110
CUT_W, CUT_H = 744, 1038
SAFE_W, SAFE_H = 684, 981

# Outer edge of the gold frame, in canvas px from the file edge. The cut line
# is at 36px and MPC drift runs about +/-1mm (12px @300DPI), so 54px keeps the
# frame 1.5mm inside the blade even when it drifts *inward* — the direction
# that would otherwise shave the frame instead of just widening the margin.
FRAME_INSET = 54

# Kept at the previous value on purpose: the card is authored in CSS px and
# scaled by this, so holding it fixed keeps every type size at the physical
# size the approved proofs already had. The card is authored narrower instead.
ZOOM = 1.581

FACE_W = round((BLEED_W - 2 * FRAME_INSET) / ZOOM, 2)
FACE_H = round((BLEED_H - 2 * FRAME_INSET) / ZOOM, 2)

TCG_PAD = 12  # authored px; was 20 — trimmed to buy back content width
GOLD_PAD = 5  # authored px; was 7
INNER_PAD = "14px 15px"

# Dark illustration panel: runs off the top and both side edges of the file.
ART_BLEED_H = 520
ART_FADE = 150  # px of fade from illustration into parchment

PRINT_CSS = f"""
/* ---- print / bleed layout (build_print.py) ------------------------------ */
@page{{size:{BLEED_W}px {BLEED_H}px;margin:0}}
html,body{{margin:0;padding:0;background:#000}}
body{{width:{BLEED_W}px;height:{BLEED_H}px;overflow:hidden;display:block;padding:0}}

.pcard{{position:relative;width:{BLEED_W}px;height:{BLEED_H}px;overflow:hidden;
  /* BLEED LAYER 1 — parchment, fills all four edges of the file */
  background:linear-gradient(160deg,var(--cream) 0%,var(--cream2) 52%,var(--cream3) 100%);}}
.pcard::after{{content:'';position:absolute;inset:0;z-index:3;pointer-events:none;opacity:.05;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E");}}

/* BLEED LAYER 2 — dark illustration panel, off the top and both sides */
.pbleed{{position:absolute;left:0;right:0;top:0;height:{ART_BLEED_H}px;z-index:0;overflow:hidden;
  background:linear-gradient(180deg,#160d04,#241605);}}
.pbleed img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 30%;
  transform:scale(1.06);filter:saturate(.92) brightness(.72) blur(2px);}}
.pbleed::after{{content:'';position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(10,6,2,.45) 0%,rgba(10,6,2,.20) {ART_BLEED_H - ART_FADE - 120}px,
    rgba(0,0,0,0) {ART_BLEED_H - ART_FADE}px,var(--cream2) 100%);}}

/* LAYER 3 — the frame assembly, floating inside the cut line */
.pframe{{position:absolute;left:{FRAME_INSET}px;top:{FRAME_INSET}px;
  width:{BLEED_W - 2 * FRAME_INSET}px;height:{BLEED_H - 2 * FRAME_INSET}px;z-index:2;}}
.pframe .face{{position:static!important;top:auto!important;left:auto!important;
  transform:none!important;-webkit-backface-visibility:visible!important;backface-visibility:visible!important;
  width:{FACE_W}px!important;zoom:{ZOOM};}}
.pframe .tcg{{height:{FACE_H}px!important;border-radius:16px!important;padding:{TCG_PAD}px!important;
  display:flex!important;flex-direction:column!important;
  box-shadow:0 10px 26px rgba(30,14,0,.45),inset 0 2px 0 rgba(255,235,180,.4),inset 0 -3px 6px rgba(0,0,0,.3)!important;}}
/* the old renders left a dead band of frame at the bottom because .gold/.inner
   never stretched to the fixed .tcg height — make the whole stack fill it */
.pframe .gold{{padding:{GOLD_PAD}px!important;border-radius:10px!important;
  flex:1 1 auto!important;display:flex!important;flex-direction:column!important;min-height:0}}
.pframe .inner{{display:flex!important;flex-direction:column!important;flex:1 1 auto!important;
  height:auto!important;min-height:0;padding:{INNER_PAD}!important;border-radius:6px!important}}
.pframe .face.front .art{{flex:1 1 auto!important;display:flex!important}}
.pframe .face.front .art-win{{flex:1 1 auto!important;height:auto!important;min-height:170px}}
.pframe .face.front .flavor{{flex:0 0 auto}}
.pframe .face.back .inner.bk{{justify-content:flex-start}}
.pframe .face.back .bk-val{{margin-top:auto!important}}

/* The redaction bars on the Mythos card are runs of U+2588 with no break
   opportunity, so the flex item's min-content width is the whole string and the
   Resistance box overflowed the card and lost its right border. Pre-existing;
   visible in the deck as already sent. Let the run wrap inside its box. */
.pframe .wr2{{min-width:0}}
.pframe .wr2 .box{{min-width:0;overflow:hidden}}
.pframe .wr2 .x{{overflow-wrap:anywhere}}

/* proof overlay only — never rendered into a print file */
.pguides{{position:absolute;inset:0;pointer-events:none;z-index:9}}
.pguides i{{position:absolute;border:2px solid;display:block}}
.pguides .trim{{left:{(BLEED_W - CUT_W) // 2}px;top:{(BLEED_H - CUT_H) // 2}px;
  right:{(BLEED_W - CUT_W) // 2}px;bottom:{(BLEED_H - CUT_H) // 2}px;border-color:#ff3b3b}}
.pguides .safe{{left:{(BLEED_W - SAFE_W) // 2}px;top:{(BLEED_H - SAFE_H) // 2}px;
  right:{(BLEED_W - SAFE_W) // 2}px;bottom:{(BLEED_H - SAFE_H) // 2}px;border-color:#39ff66}}
"""

# Floating the frame inside the cut line costs 108px of height, which is enough
# to push the densest backs (GPT-5 carries five benchmark rows) past the bottom
# of the card, clipping the validation footer. Tighten the vertical rhythm in
# steps until the content fits, and only scale type as a last resort.
FIT_LEVELS = [
    "",
    # back: vertical rhythm. front: the art window is the natural slack, so let
    # it give ground before anything with words in it does.
    """.pframe .bk-sec{margin-top:8px!important}.pframe .bk-lbl{margin-bottom:5px!important}
       .pframe .brow{padding:5px 2px!important}.pframe .atk{padding:6px 2px!important}
       .pframe .face.front .art-win{min-height:150px!important}""",
    """.pframe .bk-sec{margin-top:6px!important}.pframe .bk-lbl{margin-bottom:4px!important}
       .pframe .brow{padding:4px 2px!important}.pframe .atk{padding:5px 2px!important}
       .pframe .wr2 .box{padding:5px 6px!important}.pframe .lims li{margin-bottom:2px!important}
       .pframe .bk-val{padding-top:6px!important;margin-top:auto!important}
       .pframe .face.front .art-win{min-height:130px!important}
       .pframe .ability{padding:5px 7px!important;margin-top:5px!important}
       .pframe .dex{padding:4px 0 5px!important}""",
    """.pframe .bk-sec{margin-top:4px!important}.pframe .bk-lbl{margin-bottom:3px!important}
       .pframe .brow{padding:3px 2px!important}.pframe .atk{padding:4px 2px!important}
       .pframe .wr2 .box{padding:4px 6px!important}.pframe .lims li{margin-bottom:1px!important}
       .pframe .bk-val{padding-top:5px!important;margin-top:auto!important}
       .pframe .flavor,.pframe .bk-flavor{margin-top:5px!important;padding-top:5px!important}
       .pframe .face.front .art-win{min-height:110px!important}
       .pframe .ability{padding:4px 7px!important;margin-top:4px!important}
       .pframe .ability .ds{line-height:1.24!important}
       .pframe .dex{padding:3px 0 4px!important}
       .pframe .wrr{margin-top:5px!important;padding:4px 0 3px!important}""",
]

FIT_SCRIPT = """
<script>
window.__fitLevel = 0;
function fitCard(){
  var levels = %s;
  var inner = document.querySelector('.pframe .inner');
  var tag = document.getElementById('fitstyle');
  if(!inner) return;
  for(var i=0;i<levels.length;i++){
    tag.textContent = levels[i];
    window.__fitLevel = i;
    if(inner.scrollHeight <= inner.clientHeight + 1) return;
  }
  // Still over. Shrink type only: drop the zoom 2%% at a time but grow the
  // authored width/height by the same factor, so the rendered frame stays
  // exactly 720x1002 and keeps filling its box instead of floating small.
  var face = document.querySelector('.pframe .face');
  var tcg = face.querySelector('.tcg');
  var z = %s, W = %s, H = %s;
  for(var k=1;k<=6;k++){
    var f = 1 - 0.02*k;
    face.style.zoom = (z*f).toFixed(4);
    face.style.width = (W/f).toFixed(2) + 'px';
    if(tcg) tcg.style.height = (H/f).toFixed(2) + 'px';
    window.__fitLevel = levels.length - 1 + k/100;
    if(inner.scrollHeight <= inner.clientHeight + 1) return;
  }
}
</script>
"""

# Runs on every render: fit first, then measure the tightest box containing all
# text and park it in document.title, so --dump-dom reads back a real safe-zone
# check and the fit level each card needed.
RUN_SCRIPT = """
<script>
function afterFonts(fn){
  if(document.fonts && document.fonts.ready){document.fonts.ready.then(function(){setTimeout(fn,250)});}
  else{setTimeout(fn,600);}
}
window.addEventListener('load',function(){
  afterFonts(function(){
    fitCard();
    var lo=1e9,to=1e9,ro=-1e9,bo=-1e9,n=0;
    document.querySelectorAll('.pframe *').forEach(function(el){
      if(el.children.length) return;
      var t=(el.textContent||'').trim();
      if(!t) return;
      var r=el.getBoundingClientRect();
      if(r.width<=0||r.height<=0) return;
      lo=Math.min(lo,r.left);to=Math.min(to,r.top);
      ro=Math.max(ro,r.right);bo=Math.max(bo,r.bottom);n++;
    });
    var inner=document.querySelector('.pframe .inner');
    var over=inner?Math.max(0,inner.scrollHeight-inner.clientHeight):-1;
    document.title='TEXTBOX '+[Math.round(lo),Math.round(to),Math.round(ro),Math.round(bo),n,
      window.__fitLevel,over].join(',');
  });
});
</script>
"""


def extract_div(html: str, start: int) -> str:
    """Return the balanced <div ...>...</div> beginning at `start`."""
    depth, i = 0, start
    for m in re.finditer(r"<div\b|</div>", html[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return html[start : start + m.end()]
        i = m.end()
    raise ValueError(f"unbalanced div from offset {start} (depth {depth} at {i})")


def parse_card(html_path: Path):
    html = html_path.read_text()
    style = re.search(r"<style>(.*?)</style>", html, re.S)
    if not style:
        raise ValueError(f"no <style> in {html_path}")
    head_links = re.findall(r'<link[^>]+href="https://fonts[^"]+"[^>]*>', html)
    faces = {}
    for side in ("front", "back"):
        m = re.search(rf'<div class="face {side}">', html)
        if not m:
            raise ValueError(f"no .face.{side} in {html_path}")
        faces[side] = extract_div(html, m.start())
    art = re.search(r'<img src="(art/[^"]+)"', faces["front"])
    return style.group(1), "".join(head_links), faces, (art.group(1) if art else None)


def build_html(style, links, face, lab, art, guides: bool) -> str:
    is_front = 'class="face front"' in face
    bleed = ""
    if is_front:
        inner = f'<img src="{art}" alt="">' if art else ""
        bleed = f'<div class="pbleed">{inner}</div>'
    overlay = '<div class="pguides"><i class="trim"></i><i class="safe"></i></div>' if guides else ""
    fit = FIT_SCRIPT % (json.dumps(FIT_LEVELS), ZOOM, FACE_W, FACE_H)
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        + links
        + "<style>"
        + style
        + PRINT_CSS
        + "</style><style id=\"fitstyle\"></style>"
        + fit
        + RUN_SCRIPT
        + f'</head><body><div class="pcard lab-{lab}">'
        + bleed
        + f'<div class="pframe">{face}</div>'
        + overlay
        + "</div></body></html>"
    )


def chrome_shot(html_file: Path, out_png: Path, dump_dom: bool = False, attempts: int = 3) -> str:
    """Render one page, retrying a timeout rather than losing the whole batch.

    Chrome competes with whatever else is on the machine. On a loaded box a
    render that normally takes 30s can blow past the timeout, and a single
    raised TimeoutExpired used to propagate out of the thread pool and abort a
    50-card run four cards in. Retry with a longer leash, then give up on just
    this card.
    """
    cmd = [
        CHROME,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={BLEED_W},{BLEED_H}",
        "--virtual-time-budget=9000",
        f"--screenshot={out_png}",
        html_file.as_uri(),
    ]
    if dump_dom:
        cmd.insert(-1, "--dump-dom")

    last = ""
    for i in range(attempts):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180 * (i + 1))
            if out_png.exists():
                return res.stdout
            last = f"no screenshot produced; stderr: {res.stderr[-400:]}"
        except subprocess.TimeoutExpired:
            last = f"chrome timed out after {180 * (i + 1)}s"
        if i + 1 < attempts:
            print(f"    retry {i + 1}/{attempts - 1} for {html_file.parent.name}: {last}", flush=True)
    raise RuntimeError(f"{html_file.parent.name}: {last}")


def to_jpg(png: Path, jpg: Path):
    jpg.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", str(png), "--out", str(jpg)],
        capture_output=True,
        check=True,
    )


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("×", "x"))


def deck_folder(card: dict) -> Path | None:
    """Map a card to its folder in the exported deck, if it has one.

    Match on NAME, never on card.json's `num`. This is a convenience copy only:
    it can fill a folder that already exists but it cannot create one, so a card
    added to the roster lands nowhere until build_export.py runs. build_export.py
    writes the whole deck from cards/_roster.yaml and is the one to use.

    (Historically num and the folder numbers were two different sequences that
    drifted apart from 013 on. sync_roster.py made them the same sequence.)
    """
    if not DECK_DIR.exists():
        return None
    want = _norm(card.get("name") or "")
    if not want:
        return None
    for d in sorted(DECK_DIR.iterdir()):
        if not d.is_dir():
            continue
        label = d.name.split(" ", 1)[1] if " " in d.name else d.name
        if _norm(label) == want:
            return d
    return None


def main(argv):
    guides = "--guides" in argv
    no_deck = "--no-deck" in argv
    wanted = [a for a in argv if not a.startswith("--")]

    cards = sorted(CARDS.glob("*/*/card.json"))
    if wanted:
        cards = [c for c in cards if c.parent.name in wanted]
        if not cards:
            sys.exit(f"no card dir matched {wanted}")

    jobs = 1
    for a in argv:
        if a.startswith("--jobs="):
            jobs = max(1, int(a.split("=", 1)[1]))

    ok, failed, no_deck_folder, warnings = 0, [], [], []
    lock = threading.Lock()

    def render_card(cj):
        d = cj.parent
        card = json.loads(cj.read_text())
        slug, lab = d.name, card.get("lab") or d.parent.name
        html_path = d / (card.get("html") or f"{slug}.html")
        if not html_path.exists():
            cand = [p for p in d.glob("*.html") if not p.name.startswith("print_")]
            if not cand:
                with lock:
                    failed.append((slug, "no source html"))
                return
            html_path = cand[0]
        try:
            style, links, faces, art = parse_card(html_path)
        except ValueError as e:
            with lock:
                failed.append((slug, str(e)))
            return

        notes = []
        for side in ("front", "back"):
            suffix = "_proof" if guides else ""
            hf = d / f"print_{side}{suffix}.html"
            pf = d / f"print_{side}{suffix}.png"
            hf.write_text(build_html(style, links, faces[side], lab, art, guides))
            dom = chrome_shot(hf, pf, dump_dom=True)
            m = re.search(r"TEXTBOX ([\d,.,-]+)", dom)
            if m:
                parts = m.group(1).split(",")
                l, t, r, b, n = (int(float(x)) for x in parts[:5])
                fit, over = float(parts[5]), int(float(parts[6]))
                sx, sy = (BLEED_W - SAFE_W) // 2, (BLEED_H - SAFE_H) // 2
                with lock:
                    if not (l >= sx and t >= sy and r <= BLEED_W - sx and b <= BLEED_H - sy):
                        warnings.append(f"{slug} {side}: text box {l},{t}-{r},{b} breaks the safe zone")
                    if over > 0:
                        warnings.append(f"{slug} {side}: content still overflows by {over}px after fit")
                if fit:
                    notes.append(f"{side} fit L{fit:g}")
            else:
                with lock:
                    warnings.append(f"{slug} {side}: no measurement returned")
            if not guides:
                jpg = PRINT_DIR / f"{slug}_{side}.jpg"
                to_jpg(pf, jpg)
                if not no_deck:
                    folder = deck_folder(card)
                    if folder:
                        shutil.copy2(jpg, folder / f"{side}.jpg")
                    elif side == "front":
                        with lock:
                            no_deck_folder.append(slug)
        tail = f"  [{', '.join(notes)}]" if notes else ""
        with lock:
            nonlocal_ok[0] += 1
            print(f"  ok {slug}{' (proof)' if guides else ''}{tail}", flush=True)

    nonlocal_ok = [0]

    def guarded(cj):
        """One card blowing up must not take the rest of the batch with it."""
        try:
            render_card(cj)
        except Exception as e:  # noqa: BLE001 - report and carry on
            with lock:
                failed.append((cj.parent.name, str(e)[:200]))
                print(f"  FAILED {cj.parent.name}: {str(e)[:120]}", flush=True)

    if jobs > 1:
        with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
            list(pool.map(guarded, cards))
    else:
        for cj in cards:
            guarded(cj)
    ok = nonlocal_ok[0]

    print(f"\n{ok} card(s) rendered, {len(failed)} failed")
    for slug, why in failed:
        print(f"  FAILED {slug}: {why}")
    for w in warnings:
        print(f"  WARN {w}")
    if no_deck_folder:
        print(f"  no deck folder yet, run build_export.py: {', '.join(no_deck_folder)}")


if __name__ == "__main__":
    main(sys.argv[1:])
