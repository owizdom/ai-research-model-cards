#!/usr/bin/env python3
"""Single source of truth for card order and card numbers.

The deck carried three numbering schemes at once: 48 cards stamped /052, eight
stamped /056, and two (Opus 4.7, Sonnet 4.6) with a number in their HTML but
none in card.json at all. Nothing reconciled them, so the printed number, the
export folder and the cover count could all disagree and none of them was wrong
on its own terms.

cards/_roster.yaml fixes that: position in the roster IS the card number, and
the roster length IS the set size. Edit the roster, run this, and card.json,
every HTML face and the cover count move together.

    python3 sync_roster.py --init     # write the roster from the current deck
    python3 sync_roster.py --check    # report what would change
    python3 sync_roster.py            # apply

Numbers live in four places per card and this rewrites all four by position,
never by matching the old value -- the two legacy cards write theirs as
"011 / 052" with spaces, so value-matching silently skipped them before.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "cards"
ROSTER = CARDS / "_roster.yaml"
DECK_LIST = Path.home() / "Desktop/docs/stanford/model-cards-deck/deck-list.txt"

# Cards that come after the historical 47-card print order, in set sequence.
TAIL = [
    "claude-fable-5", "claude-sonnet-5", "claude-opus-5",
    "gpt-5-5", "gpt-5-6-sol",
    "inkling", "inkling-small", "kimi-k3",
]

# On disk but deliberately not in the set. --init will not place these, and
# leaving them out of the roster is what keeps them off the deck, the cover and
# the gallery. The card folders stay in cards/ so the work is not lost.
DROPPED = {
    "claude-2", "claude-3-5-haiku", "claude-3-5-sonnet", "claude-3-7-sonnet",
    "claude-3-haiku", "claude-3-opus", "claude-3-sonnet", "claude-4-1",
    "claude-4-5", "claude-4-6", "claude-4-opus", "claude-4-sonnet",
    "claude-sonnet-4-6", "gemini-1-0-pro", "gemini-1-5-flash", "gemini-1-5-pro",
    "gemini-2-0-flash", "gemini-2-5-deep-think", "gemini-2-5-pro", "gemini-3-flash",
    "gemini-3-pro", "gpt-4", "gpt-4-5", "gpt-4o",
    "llama-2", "llama-3", "llama-3-1", "llama-3-2",
    "llama-3-3", "llama-4", "mistral-3-1", "mistral-7b",
    "mistral-large", "mistral-large-2", "mixtral-8-7b", "o1",
    "o1-mini", "o3-mini",
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("×", "x"))


def card_dirs() -> dict[str, Path]:
    out = {}
    for cj in sorted(CARDS.glob("*/*/card.json")):
        if cj.parent.parent.name == "_pack":
            continue
        out[cj.parent.name] = cj.parent
    return out


def card_name(d: Path) -> str:
    c = json.loads((d / "card.json").read_text())
    return c.get("name") or d.name


# ---------------------------------------------------------------- roster i/o

def read_roster() -> list[str]:
    if not ROSTER.exists():
        sys.exit("no cards/_roster.yaml -- run with --init first")
    slugs = []
    for line in ROSTER.read_text().splitlines():
        line = line.split("#", 1)[0].rstrip()
        m = re.match(r"\s*-\s*(\S+)\s*$", line)
        if m:
            slugs.append(m.group(1))
    return slugs


def write_roster(slugs: list[str], dirs: dict[str, Path]) -> None:
    lines = [
        "# Model Cards -- SET 01 print order.",
        "#",
        "# Position in this list IS the card number; the length IS the set size.",
        "# Reorder, add or delete a line, then run:  python3 sync_roster.py",
        "#",
        f"# {len(slugs)} cards.",
        "",
        "cards:",
    ]
    for i, s in enumerate(slugs, 1):
        nm = card_name(dirs[s]) if s in dirs else "?"
        lines.append(f"  - {s:<24}# {i:03d}  {nm}")
    ROSTER.write_text("\n".join(lines) + "\n")


def init() -> list[str]:
    """Seed the roster from the exported deck order, then the tail."""
    dirs = card_dirs()
    by_name = {norm(card_name(d)): s for s, d in dirs.items()}
    order: list[str] = []

    if DECK_LIST.exists():
        for line in DECK_LIST.read_text().splitlines():
            m = re.match(r"\s*(\d{2})\s+(.+?)\s*$", line)
            if not m:
                continue
            slug = by_name.get(norm(m.group(2)))
            if slug and slug not in order:
                order.append(slug)
    order = [s for s in order if s not in DROPPED]
    for s in TAIL:
        if s in dirs and s not in order:
            order.append(s)
    missing = [s for s in dirs if s not in order and s not in DROPPED]
    if missing:
        print(f"  ! not placed by --init, appended: {', '.join(sorted(missing))}")
        order += sorted(missing)
    return order


# ------------------------------------------------------------- html patching

def patch_html(path: Path, num: str) -> bool:
    """Rewrite the four places a card prints its number. Position, not value."""
    s = orig = path.read_text()
    n3 = num.split("/")[0]
    s = re.sub(r'(<div class="dex">NO\.\s*)\d+', rf"\g<1>{n3}", s)
    s = re.sub(r'(<span class="no">)\s*\d+\s*/\s*\d+', rf"\g<1>{num}", s)
    s = re.sub(r'(<span class="s">)\s*\d+\s*/\s*\d+', rf"\g<1>{num}", s)
    s = re.sub(r'(SET 01</div><div>)\s*\d+\s*/\s*\d+', rf"\g<1>{num}", s)
    if s != orig:
        path.write_text(s)
        return True
    return False


def main(argv: list[str]) -> int:
    dirs = card_dirs()

    if "--init" in argv:
        slugs = init()
        write_roster(slugs, dirs)
        print(f"wrote {ROSTER.relative_to(ROOT)} with {len(slugs)} cards")
        return 0

    check = "--check" in argv
    slugs = read_roster()

    unknown = [s for s in slugs if s not in dirs]
    if unknown:
        sys.exit(f"roster names cards that do not exist: {', '.join(unknown)}")
    dropped = sorted(s for s in dirs if s not in slugs and s in DROPPED)
    if dropped:
        print(f"  deliberately not in the set: {', '.join(dropped)}")
    absent = sorted(s for s in dirs if s not in slugs and s not in DROPPED)
    if absent:
        print(f"  ! on disk but not in the roster (will keep its old number): "
              f"{', '.join(absent)}")

    total = len(slugs)
    changed, rebuilt = [], []
    for i, slug in enumerate(slugs, 1):
        d = dirs[slug]
        cj = d / "card.json"
        c = json.loads(cj.read_text())
        num = f"{i:03d}/{total:03d}"
        if c.get("num") == num:
            continue
        changed.append((slug, c.get("num"), num))
        if check:
            continue
        c["num"] = num
        cj.write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
        if c.get("generated"):
            rebuilt.append(slug)
        else:
            html = d / (c.get("html") or f"{slug}.html")
            if not html.exists():
                cand = [p for p in d.glob("*.html") if not p.name.startswith("print_")]
                html = cand[0] if cand else None
            if html and not patch_html(html, num):
                print(f"  ! {slug}: card.json updated but no number found in {html.name}")

    for slug, was, now in changed:
        print(f"  {slug:<24} {was or '(none)':>9} -> {now}")

    if check:
        print(f"\nDRY RUN: {len(changed)} card(s) would change; set size {total}")
        return 0

    if rebuilt:
        subprocess.run([sys.executable, "build_card_html.py", *rebuilt],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        print(f"  rebuilt {len(rebuilt)} generated card(s)")

    write_roster(slugs, dirs)
    print(f"\n{len(changed)} card(s) renumbered; set size {total}")
    print(f"next: python3 build_cover.py {total} && python3 build_print.py --jobs=2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
