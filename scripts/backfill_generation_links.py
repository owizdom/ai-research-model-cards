#!/usr/bin/env python3
"""Link eval_results rows to their model_generation.

Why this exists: the API counts a generation's evals via
`eval_results.generation_id` (apps/api/src/api/v1/families.py:59), and the
worker's extractor sets it by looking up the generation that owns the document
(apps/worker/src/extractor/eval_extractor.py:338-343). Two paths miss it:

  * `scripts/extract_local.py` never sets generation_id at all
  * the worker sets it at extraction time, so a card extracted BEFORE its
    generation row is seeded keeps NULL forever

The result is a silent under-count on the site: as of 2026-08-03, 1,171 rows
across 34 generations were orphaned, and Claude Opus 4.8 / Mythos Preview
displayed 0 evals despite having 40 / 37 extracted rows.

This applies the extractor's own rule to rows that missed it. It only ever
fills NULLs, never re-points a row that already has a generation.

    python3 scripts/backfill_generation_links.py                    # dry run, whole corpus
    python3 scripts/backfill_generation_links.py --gen claude-opus-5 --apply
    python3 scripts/backfill_generation_links.py --all --apply      # whole corpus
    python3 scripts/backfill_generation_links.py --revert out.csv   # undo using the audit file
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

REPO = Path(__file__).resolve().parent.parent
for line in (REPO / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Rows that would be linked, plus the generation they belong to.
CANDIDATES = """
SELECT er.id AS eval_id, mg.id AS gen_id, mg.slug AS gen_slug, d.id AS doc_id, d.slug AS doc_slug
  FROM eval_results er
  JOIN document_versions dv ON er.document_version_id = dv.id
  JOIN documents d          ON d.id  = dv.document_id
  JOIN model_generations mg ON mg.document_id = d.id
 WHERE er.generation_id IS NULL
"""

# A row is unsafe to link if an identical row already carries that generation,
# which would violate uq_eval_result on update.
COLLISION = """
   AND NOT EXISTS (
        SELECT 1 FROM eval_results e2
         WHERE e2.document_version_id = er.document_version_id
           AND e2.generation_id       = mg.id
           AND e2.benchmark_id        = er.benchmark_id
           AND e2.variant   IS NOT DISTINCT FROM er.variant
           AND e2.model_name IS NOT DISTINCT FROM er.model_name)
"""


def connect():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL not set (expected in .env)")
    return psycopg2.connect(dsn.replace("postgresql+asyncpg://", "postgresql://"))


def revert(path: str) -> int:
    rows = list(csv.DictReader(open(path)))
    if not rows:
        print("audit file is empty, nothing to revert")
        return 0
    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE eval_results SET generation_id = NULL WHERE id = ANY(%s)",
            ([int(r["eval_id"]) for r in rows],),
        )
        n = cur.rowcount
    conn.close()
    print(f"reverted {n} rows to generation_id = NULL")
    return n


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--gen", action="append", help="Only this generation slug (repeatable)")
    p.add_argument("--all", action="store_true", help="Every orphaned row in the corpus")
    p.add_argument("--apply", action="store_true", help="Commit (default is a dry run)")
    p.add_argument("--audit", default="generation_link_backfill.csv",
                   help="Where to write the list of changed rows, for --revert")
    p.add_argument("--revert", help="Undo a previous run using its audit CSV")
    a = p.parse_args()

    if a.revert:
        return 0 if revert(a.revert) >= 0 else 1
    if not a.gen and not a.all:
        print("note: no --gen and no --all, showing the whole corpus as a dry run\n")

    sql = CANDIDATES + COLLISION
    params: list = []
    if a.gen:
        sql += " AND mg.slug = ANY(%s)"
        params.append(a.gen)
    sql += " ORDER BY mg.slug, er.id"

    conn = connect()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

        by_gen: dict[str, int] = {}
        for r in rows:
            by_gen[r["gen_slug"]] = by_gen.get(r["gen_slug"], 0) + 1
        for slug, n in sorted(by_gen.items(), key=lambda x: -x[1]):
            print(f"  {slug:22s} {n:5d} rows")
        print(f"\n  {len(rows)} rows across {len(by_gen)} generations")

        if not a.apply:
            print("\n  dry run. re-run with --apply to write.")
            conn.close()
            return 0
        if not rows:
            conn.close()
            return 0

        with open(a.audit, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["eval_id", "gen_id", "gen_slug", "doc_id", "doc_slug"])
            for r in rows:
                w.writerow([r["eval_id"], r["gen_id"], r["gen_slug"], r["doc_id"], r["doc_slug"]])
        print(f"  wrote audit file {a.audit} ({len(rows)} rows) — revert with --revert {a.audit}")

        cur.executemany(
            "UPDATE eval_results SET generation_id = %s WHERE id = %s AND generation_id IS NULL",
            [(r["gen_id"], r["eval_id"]) for r in rows],
        )
        conn.commit()
        print(f"  linked {len(rows)} rows")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
