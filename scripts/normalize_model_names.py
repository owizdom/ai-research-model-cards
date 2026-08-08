#!/usr/bin/env python3
"""Strip table artifacts out of eval_results.model_name.

Reading a benchmark table by column picks the model name off the header, and in
a real card the header cell is crowded: footnote markers sit tight against the
name and the shot-count column bleeds into it. The rebuild produced

    "5 Claude 3 Sonnet"   "7 Claude 3 Sonnet"   "15 Claude 3 Sonnet"
    "GPT-43"              "GPT-3.53"            "Gemini 1.0 Pro4"

The scores behind those labels are correct and in the right column. Only the
label is dirty, so this is a rename, not a re-extraction.

Trailing digits cannot be stripped blindly: "Claude 3", "GPT-4" and "o3" all end
in a real digit. A trailing digit is only a footnote if removing it lands on a
model name that already exists elsewhere in the corpus, so "GPT-43" collapses to
"GPT-4" while "GPT-4" itself is left alone.

    python3 scripts/normalize_model_names.py --check
    python3 scripts/normalize_model_names.py --apply
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter

import sqlalchemy as sa

DB = os.environ.get("DATABASE_URL")

LEADING = re.compile(r"^\s*\d+\s+(?=[A-Za-z])")   # "5 Claude 3 Sonnet"
TRAILING = re.compile(r"^(.*?[A-Za-z0-9])(\d)$")  # "GPT-43" -> ("GPT-4", "3")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def clean(name: str, known: set[str]) -> str:
    out = LEADING.sub("", name or "").strip()
    m = TRAILING.match(out)
    if m and norm(m.group(1)) in known and norm(out) not in known:
        out = m.group(1).strip()
    return re.sub(r"\s{2,}", " ", out).strip(" ,;:·")


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--apply", action="store_true")
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)
    if not DB:
        sys.exit("set DATABASE_URL (localhost, never the Railway url)")
    if "rlwy.net" in DB or "railway" in DB:
        sys.exit("refusing to run against Railway production")

    e = sa.create_engine(DB)
    with e.connect() as c:
        names = [r[0] for r in c.execute(sa.text(
            "select distinct model_name from eval_results where model_name is not null"))]

    # a name is "known" if it survives leading-digit cleanup somewhere
    known = {norm(LEADING.sub("", n).strip()) for n in names}
    changes = {n: clean(n, known) for n in names}
    changes = {k: v for k, v in changes.items() if v and v != k}

    print(f"distinct model_name values : {len(names)}")
    print(f"would rename               : {len(changes)}")
    for k, v in sorted(changes.items())[:20]:
        print(f"   {k!r:34} -> {v!r}")
    if len(changes) > 20:
        print(f"   ... and {len(changes)-20} more")

    if not a.apply:
        print("\ndry run — pass --apply to write")
        return 0

    with e.begin() as c:
        n = 0
        for old, new in changes.items():
            r = c.execute(sa.text(
                "update eval_results set model_name=:new where model_name=:old"),
                {"new": new, "old": old})
            n += r.rowcount
        after = c.execute(sa.text(
            "select count(distinct model_name) from eval_results")).scalar()
    print(f"\nrenamed {n:,} rows; distinct model names now {after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
