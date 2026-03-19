#!/usr/bin/env python3
"""Trigger a probe run — enqueue all active probes × all active models."""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

import redis
from sqlalchemy import select
from packages.db.session import AsyncSessionLocal, init_db
from packages.db.models import ProbeDefinition, AIModel, ProbeRun


async def main():
    await init_db()

    async with AsyncSessionLocal() as db:
        probes = (await db.execute(
            select(ProbeDefinition).where(ProbeDefinition.is_active == True)
        )).scalars().all()
        models = (await db.execute(
            select(AIModel).where(AIModel.is_active == True)
        )).scalars().all()

        if not probes:
            print("No active probes found. Run seed first.")
            return
        if not models:
            print("No active models found. Run seed first.")
            return

        probe_ids = [p.id for p in probes]
        model_slugs = [m.slug for m in models]

        run = ProbeRun(
            triggered_by="user",
            status="queued",
            probe_count=len(probe_ids),
            model_count=len(model_slugs),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        r.rpush("probe_runs", json.dumps({
            "run_id": run.id,
            "probe_ids": probe_ids,
            "model_slugs": model_slugs,
        }))

        total = len(probe_ids) * len(model_slugs)
        print(f"Queued probe run #{run.id}: {len(probe_ids)} probes × {len(model_slugs)} models = {total} calls")
        print(f"Models: {', '.join(model_slugs)}")
        print(f"Estimated time: ~{total * 3}s ({total * 3 // 60}min) at 2.5s/call")
        print(f"\nWatch progress: docker logs -f compose-worker-1")


if __name__ == "__main__":
    asyncio.run(main())
