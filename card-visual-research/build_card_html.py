#!/usr/bin/env python3
"""Generate a card's two-face HTML from its card.json.

This is the generator the repo never had. All 50 existing cards were authored by
hand, which is why adding a model meant hand-editing HTML and why every card
face carries its own hand-typed numbers. New cards go through here instead.

The shared stylesheet is lifted from an existing card at build time, so a
generated card cannot drift from the set's styling.

    python3 build_card_html.py kimi-k3            # write cards/*/kimi-k3/kimi-k3.html
    python3 build_card_html.py --all              # regenerate every card marked generated:true
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "cards"
STYLE_SRC = CARDS / "anthropic" / "claude-2" / "claude-2.html"

LAB_NAME = {
    "anthropic": "Anthropic", "openai": "OpenAI", "google": "Google DeepMind",
    "meta": "Meta AI", "mistral": "Mistral AI", "xai": "xAI",
    "thinkingmachines": "Thinking Machines", "moonshot": "Moonshot AI",
}


def e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=False)


def sparks(n: int) -> str:
    return "".join('<span class="e"></span>' for _ in range(max(1, min(int(n or 1), 4))))


def dex_text(c: dict) -> str:
    """The strip under the art.

    Hand-read cards have no corpus figures, and printing "— words · — evals"
    reads as broken rather than as honest. Say what is actually true of them.
    """
    num = (c.get("num") or "").split("/")[0]
    if c.get("source") == "manual-cardread":
        return f"NO. {num} · hand-read card · not yet in the corpus"
    parts = [f"NO. {num}"]
    if c.get("words"):
        parts.append(f"{c['words']} words")
    if c.get("evals"):
        parts.append(f"{c['evals']} evals")
    if c.get("unique"):
        parts.append(f"{c['unique']} lab-unique")
    return " · ".join(parts)


def front(c: dict) -> str:
    art = c.get("art") or f"{c['slug']}.png"
    art_path = ROOT / "cards" / c["lab"] / c["slug"] / "art" / art
    # Two copies: a blurred `cover` backdrop that fills the window, and the
    # real art `contain`ed over it so no card loses artwork to the crop.
    art_html = ((f'<img class="artbg" src="art/{e(art)}" alt="" aria-hidden="true">'
                 f'<img src="art/{e(art)}" alt="">') if art_path.exists()
                else '<div class="art-ph">ART GOES HERE</div>')
    tags = "·".join(f"<span>{e(t)}</span>" for t in c.get("tags", []))
    atks = ""
    for i, b in enumerate(c.get("benches", [])):
        score = b.get("s")
        dmg = e(score) if score not in (None, "", "—") else "—"
        atks += (
            f'<div class="atk"><div class="cost">{sparks(b.get("cost", 3 - i))}</div>'
            f'<div class="mid"><div class="nm">{e(b.get("n"))}</div>'
            f'<div class=ds>{e(b.get("d"))}</div></div>'
            f'<div class="dmg">{dmg}</div></div>'
        )
    ability = ""
    if c.get("ability"):
        ability = ('<div class="ability"><div class="head"><span class="tag">Ability</span>'
                   f'<span class="nm">{e(c["ability"]["name"])}</span></div>'
                   f'<div class="ds">{e(c["ability"]["text"])}</div></div>')
    weak, res = c.get("weak") or {}, c.get("res") or {}
    return (
        f'<div class="face front"><div class="tcg lab-{e(c["lab"])}"><div class="gold"><div class="inner">'
        f'<div class="topbar"><div class="stagewrap">'
        f'<span class="stagebadge">{e(c.get("stage", "BASIC"))}</span>'
        f'<div class="evofrom">{e(c.get("meta"))}</div>'
        f'<div class="name">{e(c.get("name"))}</div></div>'
        f'<div class="hp"><span class="lbl">{e(c.get("capL", "CAP"))}</span>'
        f'<span class="val">{e(c.get("capN"))}</span><span class="e"></span></div></div>'
        f'<div class="art"><div class="art-win">{art_html}'
        f'<div class="art-tags">{tags}</div></div></div>'
        f'<div class="dex">{e(dex_text(c))}</div>'
        f"{ability}{atks}"
        f'<div class="wrr"><div class="col"><div class="l">weakness</div>'
        f'<div class="v"><span class="e warn sm"></span>{e(weak.get("t"))}</div></div>'
        f'<div class="col"><div class="l">standout</div>'
        f'<div class="v">{e(res.get("t"))}</div></div></div>'
        f'<div class="foot"><span>freesystems.net · Free Systems Lab</span>'
        f'<span class="no">{e(c.get("num"))} <span class="holo">{e((c.get("tier") or "").upper())}</span></span></div>'
        "</div></div></div></div>"
    )


def back(c: dict) -> str:
    nodes = ""
    for g in c.get("lineage", []):
        on = " on" if g.get("a") else " "
        nodes += (f'<div class="node{on}"><div class="dot"></div>'
                  f'<div class="v">{e(g.get("v"))}</div><div class="d">{e(g.get("d"))}</div></div>')
    rows = "".join(
        f'<div class="brow"><div style="flex:1;min-width:0"><span class="bn" style="display:block">{e(b.get("n"))}</span>'
        f'<span style="display:block;font-size:10px;color:var(--ink3);margin-top:1px">{e(b.get("d"))}</span></div>'
        f'<span class="bs">{e(b.get("s"))}</span><span class="bl">{e(b.get("l"))}</span></div>'
        for b in c.get("btbl", [])
    )
    weak, res, val = c.get("weak") or {}, c.get("res") or {}, c.get("val") or {}
    lims = "".join(f"<li>{x}</li>" for x in c.get("lims", []))
    return (
        f'<div class="face back"><div class="tcg lab-{e(c["lab"])}"><div class="gold"><div class="inner bk">'
        f'<div class="bk-head"><span class="t">{e(LAB_NAME.get(c["lab"], c["lab"]).upper())} · '
        f'{e((c.get("name") or "").upper())}</span><span class="s">{e(c.get("num"))}</span></div>'
        f'<div class="bk-sec"><div class="bk-lbl">Generation Lineage</div>'
        f'<div class="line">{nodes}</div></div>'
        f'<div class="bk-sec"><div class="bk-lbl">Benchmark Record</div>{rows}</div>'
        f'<div class="bk-sec"><div class="bk-lbl">Performance Summary</div>'
        f'<div class="bk-flavor">{e(c.get("blurb"))}</div></div>'
        f'<div class="bk-sec"><div class="bk-lbl">Acknowledged Limitations</div>'
        f'<ul class="lims">{lims}</ul></div>'
        f'<div class="bk-val"><div><div class="vt">INDEPENDENT VALIDATION</div>'
        f'<div class="vx">{e(val.get("b"))}</div></div>'
        f'<div class="vr"><div>SET 01</div><div>{e(c.get("num"))}</div></div></div>'
        "</div></div></div></div>"
    )


SIZER = ('<script>function sizeCard(){var s=document.querySelector(".stage"),'
         'f=document.querySelector(".face.front"),b=document.querySelector(".face.back");'
         'if(!s||!f||!b)return;var m=getComputedStyle(s).transform.match(/matrix\\(([^,]+)/);'
         'var sc=m?parseFloat(m[1]):1;var fH=f.offsetHeight;'
         's.style.marginBottom=Math.round(sc*Math.max(fH,b.offsetHeight)-fH)+"px";}'
         'sizeCard();window.addEventListener("load",sizeCard);'
         'if(document.fonts&&document.fonts.ready)document.fonts.ready.then(sizeCard);</script>')


def build(card_json: Path) -> Path:
    c = json.loads(card_json.read_text())
    src = STYLE_SRC.read_text()
    style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    links = "".join(re.findall(r'<link[^>]+href="https://fonts[^"]+"[^>]*>', src))
    extra = c.get("lab_css", "")
    doc = ('<!DOCTYPE html><html><head><meta charset="UTF-8">' + links
           + "<style>" + style + extra + "</style></head><body>"
           + '<div class="stage"><div class="cardwrap"><div class="flipper">'
           + front(c) + back(c) + "</div></div></div>" + SIZER + "</body></html>")
    out = card_json.parent / (c.get("html") or f"{card_json.parent.name}.html")
    out.write_text(doc)
    return out


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("slugs", nargs="*")
    p.add_argument("--all", action="store_true", help="every card with generated:true")
    a = p.parse_args(argv)

    targets = []
    for cj in sorted(CARDS.glob("*/*/card.json")):
        c = json.loads(cj.read_text())
        if a.slugs and cj.parent.name in a.slugs:
            targets.append(cj)
        elif a.all and c.get("generated"):
            targets.append(cj)
    if not targets:
        sys.exit("nothing to build (pass a slug, or --all for generated:true cards)")
    for cj in targets:
        print(f"  wrote {build(cj).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
