#!/usr/bin/env python3
"""Backfill EvalResult.shot_count / method / language / training_state from
variant strings using the parser in apps/worker/src/extractor/variant_parser.py.

Idempotent: only fills columns that are currently NULL. Never overwrites
existing structured data — so if the extractor or a future operator has
already populated a field, the backfill respects that.

Why a one-shot script instead of a migration: the parser logic may evolve
as we observe more variant patterns. Migrations are for schema changes;
this is data cleanup, repeatable on demand.

Usage:
  # Dry run (default) — counts what *would* change without writing.
  python3 scripts/backfill_variant_fields.py

  # Commit changes.
  python3 scripts/backfill_variant_fields.py --apply

Requires DATABASE_URL in .env (or env) — same connection used by alembic.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "worker" / "src"))
from extractor.variant_parser import parse_variant  # noqa: E402

load_dotenv(ROOT / ".env")

# psycopg2 doesn't speak asyncpg's URL prefix.
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


def main(apply_changes: bool) -> None:
    fills = Counter()  # per-field count of rows we'd populate
    rows_touched = 0
    parsed_zero_fields = 0  # parser ran but produced nothing
    already_complete = 0  # all 4 columns already populated

    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # Select rows whose variant might contain extractable info.
            cur.execute("""
                SELECT id, variant, shot_count, method, language, training_state
                FROM eval_results
                WHERE variant IS NOT NULL AND variant != 'default'
                  AND (shot_count IS NULL OR method IS NULL
                       OR language IS NULL OR training_state IS NULL)
            """)
            rows = cur.fetchall()
            candidates = len(rows)
            print(f"candidate rows (variant set + at least one NULL): {candidates}")

            updates: list[tuple] = []
            for row_id, variant, shot, method, lang, ts in rows:
                parsed = parse_variant(variant)
                if not parsed:
                    parsed_zero_fields += 1
                    continue

                # Build a partial UPDATE — only fill columns that are NULL now AND
                # that the parser actually identified.
                to_set = {}
                if shot is None and "shot_count" in parsed:
                    to_set["shot_count"] = parsed["shot_count"]
                if method is None and "method" in parsed:
                    to_set["method"] = parsed["method"]
                if lang is None and "language" in parsed:
                    to_set["language"] = parsed["language"]
                if ts is None and "training_state" in parsed:
                    to_set["training_state"] = parsed["training_state"]

                if not to_set:
                    # Parser found something but every relevant column was already populated.
                    already_complete += 1
                    continue

                for k in to_set:
                    fills[k] += 1
                rows_touched += 1
                updates.append((row_id, to_set))

            print()
            print("=== parser results ===")
            print(f"  rows that would be updated: {rows_touched}")
            print(f"  rows where parser returned nothing: {parsed_zero_fields}")
            print(f"  rows where parser ran but every relevant column was already set: {already_complete}")
            print()
            print("=== fields that would be filled ===")
            for field, count in fills.most_common():
                print(f"  {field:18s} +{count}")

            if not apply_changes:
                print()
                print("[dry-run] No changes written. Re-run with --apply to commit.")
                return

            # Apply
            print()
            print(f"applying {len(updates)} row updates ...")
            applied = 0
            for row_id, to_set in updates:
                set_clauses = ", ".join(f"{k} = %s" for k in to_set)
                params = list(to_set.values()) + [row_id]
                cur.execute(
                    f"UPDATE eval_results SET {set_clauses} WHERE id = %s",
                    params,
                )
                applied += cur.rowcount
            conn.commit()
            print(f"applied {applied} updates ✓")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--apply", action="store_true",
                   help="Commit writes. Without this flag the script reports what would change but writes nothing.")
    args = p.parse_args()
    main(apply_changes=args.apply)
