#!/usr/bin/env python3
"""Enqueue extract_jobs for all model_card document versions without completed extraction runs."""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

import redis
from sqlalchemy import select, text
from packages.db.session import AsyncSessionLocal, init_db
from packages.db.models import DocumentVersion, Document, ExtractionRun


async def main():
    await init_db()
    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

    async with AsyncSessionLocal() as db:
        # Find all model_card document versions without completed extraction runs
        q = text("""
            SELECT dv.id AS version_id, d.title
            FROM document_versions dv
            JOIN documents d ON dv.document_id = d.id
            WHERE d.doc_type = 'model_card'
            AND NOT EXISTS (
                SELECT 1 FROM extraction_runs er
                WHERE er.document_version_id = dv.id
                AND er.status = 'completed'
            )
            ORDER BY dv.version_date DESC
        """)
        result = await db.execute(q)
        rows = result.fetchall()

        if not rows:
            print("No model card versions need extraction.")
            return

        for row in rows:
            r.rpush("extract_jobs", json.dumps({"version_id": row.version_id}))
            print(f"  Queued version {row.version_id}: {row.title}")

        print(f"\nEnqueued {len(rows)} extraction jobs.")


if __name__ == "__main__":
    asyncio.run(main())
