#!/usr/bin/env python3
"""One-shot: apply Alembic migration 0010 (eval_results.split + metric_path).

Workaround for local Python 3.11 / Homebrew expat conflict making the
standard `alembic upgrade head` unrunnable from this machine. Mirrors
what alembic would do: ALTER TABLE + CREATE INDEX + bump alembic_version.

Idempotent. Safe to re-run — if the column already exists, the script
detects it and no-ops. Matches the migration file at
packages/db/migrations/versions/0010_eval_results_split_and_metric_path.py.

Usage:
  python3 scripts/apply_migration_0010.py        # dry-run (default)
  python3 scripts/apply_migration_0010.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


def main(apply_changes: bool) -> None:
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version")
            current = cur.fetchone()[0]
            print(f"current alembic revision: {current}")

            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='eval_results' AND column_name IN ('split', 'metric_path')
            """)
            existing = {r[0] for r in cur.fetchall()}
            print(f"target columns already present: {sorted(existing) or '(none)'}")

            if current == "0010" and existing == {"split", "metric_path"}:
                print("nothing to do — already at 0010")
                return

            print()
            print("would apply:")
            if "split" not in existing:
                print("  ALTER TABLE eval_results ADD COLUMN split VARCHAR")
                print("  CREATE INDEX ix_eval_results_split ON eval_results (split)")
            if "metric_path" not in existing:
                print("  ALTER TABLE eval_results ADD COLUMN metric_path VARCHAR")
                print("  CREATE INDEX ix_eval_results_metric_path ON eval_results (metric_path)")
            if current != "0010":
                print("  UPDATE alembic_version SET version_num='0010'")

            if not apply_changes:
                print("\n[dry-run] No changes written. Re-run with --apply to commit.")
                return

            print("\napplying...")
            if "split" not in existing:
                cur.execute("ALTER TABLE eval_results ADD COLUMN split VARCHAR")
                cur.execute("CREATE INDEX ix_eval_results_split ON eval_results (split)")
            if "metric_path" not in existing:
                cur.execute("ALTER TABLE eval_results ADD COLUMN metric_path VARCHAR")
                cur.execute("CREATE INDEX ix_eval_results_metric_path ON eval_results (metric_path)")
            if current != "0010":
                cur.execute("UPDATE alembic_version SET version_num='0010' WHERE version_num=%s", (current,))
        conn.commit()
        print("done")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--apply", action="store_true",
                   help="Commit writes. Without this flag the script reports what would change.")
    args = p.parse_args()
    main(apply_changes=args.apply)
