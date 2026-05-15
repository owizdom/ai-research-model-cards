#!/usr/bin/env python3
"""Fetch ONE source by slug, store to DB, enqueue embed job.

Used to ingest a newly-registered source without waiting for the nightly cron.
Mirrors what apps/collector/src/scheduler/jobs.py::collect_current does for the
full registry, but for a single slug.

Reads credentials from .env (gitignored). Required:
  DATABASE_URL    Postgres URL (Railway public proxy)
  REDIS_URL       Redis URL (Railway public proxy)

Usage:
  python3 scripts/ingest_one.py anthropic_opus47_card
"""
import asyncio
import os
import sys
from pathlib import Path

# Load .env if present (no external dotenv dep — keep it simple)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Required env
if not os.environ.get("DATABASE_URL"):
    print("ERROR: DATABASE_URL not set (and not in .env)", file=sys.stderr)
    sys.exit(1)
if not os.environ.get("REDIS_URL"):
    print("ERROR: REDIS_URL not set (and not in .env)", file=sys.stderr)
    sys.exit(1)

# Path setup so imports resolve
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "apps" / "collector"))

import httpx
from src.collectors.fetch import fetch_source
from src.collectors.registry import SOURCES
from src.pipeline.store import store_document


async def run(slug: str) -> int:
    target = next((s for s in SOURCES if s.slug == slug), None)
    if not target:
        print(f"ERROR: no source with slug='{slug}' in registry", file=sys.stderr)
        print(f"Available: {[s.slug for s in SOURCES[:5]]}…", file=sys.stderr)
        return 2
    print(f"┃ fetching {target.slug}")
    print(f"  url:    {target.url}")
    print(f"  method: {target.method}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=300.0, headers=headers, follow_redirects=True) as c:
        doc = await fetch_source(target, c)

    if doc is None:
        print("FETCH FAILED — see stderr above", file=sys.stderr)
        return 3

    print(f"  parsed:       {doc.word_count:,} words / {len(doc.content_md):,} chars")
    print(f"  content_hash: {doc.content_hash[:16]}…")

    print(f"┃ storing to DB + enqueuing embed job")
    is_new = await store_document(doc)
    if is_new:
        print(f"  ✓ NEW version stored, embed_jobs queued")
    else:
        print(f"  · content already present (same hash) — no change")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: ingest_one.py <source_slug>", file=sys.stderr)
        sys.exit(1)
    sys.exit(asyncio.run(run(sys.argv[1])))
