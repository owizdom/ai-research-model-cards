#!/usr/bin/env python3
"""Export the printed deck from the roster.

build_print.py renders every card and drops JPGs in print/ as <slug>_<side>.jpg,
but it only copies a card into the deck folder if a numbered folder for it
already exists. That made the export a hand-maintained list: the three xAI cards
sat in an "_extras" folder and every new card silently landed nowhere.

This builds both export targets from cards/_roster.yaml instead, so a card that
is in the roster is in the deck, numbered the same way it is numbered on its own
face.

    python3 build_export.py --check   # report what would change
    python3 build_export.py           # write both targets and the zip
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import sync_roster

ROOT = Path(__file__).resolve().parent
PRINT_DIR = ROOT / "print"
DECK_DIR = Path.home() / "Desktop/docs/stanford/model-cards-deck"
SEND_DIR = Path.home() / "Desktop/model-cards-print-FIXED"
ZIP = Path.home() / "Desktop/model-cards-print-FIXED.zip"
COVER = "free-systems-cover"      # the About / card-list card, pack position 00
TUCKBOX = "free-systems-tuckbox"  # the outer box, printed separately from the deck


def entries() -> list[tuple[int, str, str]]:
    """(position, slug, name) for the whole roster."""
    dirs = sync_roster.card_dirs()
    out = []
    for i, slug in enumerate(sync_roster.read_roster(), 1):
        c = json.loads((dirs[slug] / "card.json").read_text())
        out.append((i, slug, c.get("name") or slug))
    return out


def jpgs(slug: str) -> tuple[Path, Path] | None:
    f, b = PRINT_DIR / f"{slug}_front.jpg", PRINT_DIR / f"{slug}_back.jpg"
    return (f, b) if f.exists() and b.exists() else None


def fill(folder: Path, slug: str, missing: list[str]) -> None:
    pair = jpgs(slug)
    if not pair:
        missing.append(slug)
        return
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pair[0], folder / "front.jpg")
    shutil.copy2(pair[1], folder / "back.jpg")


def prune(root: Path, keep: set[str]) -> list[str]:
    """Drop folders that are no longer in the set (e.g. the old _extras)."""
    gone = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and p.name not in keep:
            shutil.rmtree(p)
            gone.append(p.name)
    return gone


def strip_junk(root: Path) -> int:
    n = 0
    for p in root.rglob(".DS_Store"):
        p.unlink()
        n += 1
    return n


def main(argv: list[str]) -> int:
    rows = entries()
    total = len(rows)
    check = "--check" in argv

    have = [s for _, s, _ in rows if jpgs(s)]
    if check:
        print(f"roster: {total} cards; rendered JPGs present for {len(have)}")
        missing = [s for _, s, _ in rows if not jpgs(s)]
        if missing:
            print(f"  ! no render yet: {', '.join(missing)}")
        print(f"  cover: {'ok' if jpgs(COVER) else 'MISSING'}")
        print(f"  tuckbox: {'ok' if jpgs(TUCKBOX) else 'MISSING'}")
        print(f"\nwould write {DECK_DIR}")
        print(f"would write {SEND_DIR}  (cover + {total} cards)")
        return 0

    missing: list[str] = []

    # 1. the deck folder: numbered cards only, no cover
    DECK_DIR.mkdir(parents=True, exist_ok=True)
    keep = {f"{i:02d} {name}" for i, _, name in rows}
    for i, slug, name in rows:
        fill(DECK_DIR / f"{i:02d} {name}", slug, missing)
    gone = prune(DECK_DIR, keep)

    listing = [f"AI Model Cards — {total}-card deck "
               f"(816x1110 @ 300DPI · each folder = front.jpg + back.jpg)", ""]
    listing += [f"{i:02d}  {name}" for i, _, name in rows]
    (DECK_DIR / "deck-list.txt").write_text("\n".join(listing) + "\n")

    # 2. the folder that goes out: cover first, then the same numbered cards
    SEND_DIR.mkdir(parents=True, exist_ok=True)
    fill(SEND_DIR / "00 Free Systems Cover", COVER, missing)
    fill(SEND_DIR / "_tuckbox", TUCKBOX, missing)
    # The panels are the artwork; the dieline is what a printer can actually
    # cut and fold. Ship both, plus the spec sheet that states the stock the
    # depth was computed from.
    die_src = PRINT_DIR / "dieline"
    if die_src.is_dir():
        die_dst = SEND_DIR / "_tuckbox" / "dieline"
        die_dst.mkdir(parents=True, exist_ok=True)
        for f in sorted(die_src.iterdir()):
            if f.is_file() and not f.name.startswith("_"):
                shutil.copy2(f, die_dst / f.name)
    else:
        missing.append("dieline (run build_dieline.py)")
    for i, slug, name in rows:
        fill(SEND_DIR / f"{i:02d} {name}", slug, missing)
    gone += prune(SEND_DIR, keep | {"00 Free Systems Cover", "_tuckbox"})
    shutil.copy2(DECK_DIR / "deck-list.txt", SEND_DIR / "deck-list.txt")

    junk = strip_junk(SEND_DIR) + strip_junk(DECK_DIR)

    # 3. the zip, rebuilt from scratch so a dropped card cannot linger in it
    if ZIP.exists():
        ZIP.unlink()
    subprocess.run(["zip", "-r", "-X", "-q", str(ZIP), SEND_DIR.name,
                    "-x", ".DS_Store", "-x", "__MACOSX/*"],
                   cwd=SEND_DIR.parent, check=True)

    n_jpg = len(list(SEND_DIR.rglob("*.jpg")))
    print(f"deck   : {DECK_DIR}  ({total} cards)")
    print(f"send   : {SEND_DIR}  (cover + {total} cards, {n_jpg} jpgs)")
    print(f"zip    : {ZIP}  ({ZIP.stat().st_size / 1e6:.1f} MB)")
    if gone:
        print(f"removed: {', '.join(gone)}")
    if junk:
        print(f"stripped {junk} .DS_Store file(s)")
    if missing:
        print(f"\n  ! MISSING RENDERS, not exported: {', '.join(sorted(set(missing)))}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
