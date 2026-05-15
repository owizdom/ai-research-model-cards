"""Scheduled collection jobs."""
import asyncio
from ..collectors.fetch import fetch_all
from ..collectors.registry import SOURCES
from ..pipeline.store import store_document, store_historical


# Any extraction_runs row in 'running' state older than this is considered
# orphaned (worker died, OOM, deploy mid-flight, etc.) and gets reaped.
# 25 min covers our 1500s CLI ceiling + insert/commit time + slack.
STUCK_RUN_THRESHOLD_MIN = 25


async def collect_current() -> dict:
    print("[collector] Starting current document collection")
    docs = await fetch_all()
    ingested = skipped = failed = 0
    for doc in docs:
        try:
            is_new = await store_document(doc)
            if is_new:
                ingested += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"[collector] Store failed {doc.slug}: {e}")
            failed += 1
    stats = {"ingested": ingested, "skipped": skipped, "failed": failed}
    print(f"[collector] Done — {stats}")
    return stats


async def reap_stuck_runs() -> dict:
    """Flip extraction_runs rows stuck in 'running' for too long to 'failed'.

    A worker that crashed mid-extraction leaves a row in 'running' state with
    no completed_at. Without reaping, the UI shows them as in-flight forever
    and the doc never gets retried. Pairs with idle_in_transaction_session_timeout
    on the DB connection (which releases the advisory lock) — this job updates
    the user-visible status.
    """
    from sqlalchemy import text
    from packages.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(text(f"""
            UPDATE extraction_runs
            SET status = 'failed',
                error = COALESCE(error, '') || ' [reaped: exceeded {STUCK_RUN_THRESHOLD_MIN} min runtime]',
                completed_at = NOW()
            WHERE status = 'running'
              AND started_at < NOW() - INTERVAL '{STUCK_RUN_THRESHOLD_MIN} minutes'
            RETURNING id, document_version_id
        """))
        rows = result.fetchall()
        await db.commit()
    if rows:
        print(f"[reaper] reaped {len(rows)} stuck runs: {[r.id for r in rows]}", flush=True)
    return {"reaped": len(rows), "run_ids": [r.id for r in rows]}


async def collect_history(max_sources: int = 5) -> dict:
    import httpx
    from ..collectors.wayback import get_historical
    from sqlalchemy import select
    from packages.db.models import Document
    from packages.db.session import AsyncSessionLocal

    print("[collector] Starting history collection")
    tracked = [s for s in SOURCES if s.track_history][:max_sources]
    ingested = skipped = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with AsyncSessionLocal() as db:
            for source in tracked:
                result = await db.execute(select(Document).where(Document.slug == source.slug))
                doc = result.scalar_one_or_none()
                if not doc:
                    continue
                try:
                    versions = await get_historical(source, client)
                    for v in versions:
                        is_new = await store_historical(doc.id, v)
                        ingested += is_new
                        skipped += not is_new
                    print(f"[collector] {source.slug}: {len(versions)} snapshots processed")
                except Exception as e:
                    print(f"[collector] History failed {source.slug}: {e}")

    return {"ingested": ingested, "skipped": skipped}
