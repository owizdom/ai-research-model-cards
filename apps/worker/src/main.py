"""Worker entry point — runs embed and probe loops as separate threads."""
import asyncio
import json
import os
import sys
import threading
import traceback
import time

import redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool


def _redis():
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


def _make_session_factory():
    """Create a fresh engine + session factory. NullPool so each asyncio.run() gets clean connections."""
    from packages.db.config import settings
    engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def embed_thread():
    """Blocking thread that consumes embed_jobs."""
    try:
        from src.embedder.pipeline import process_embed_job
        SessionLocal = _make_session_factory()
        print("[worker] embed thread ready", flush=True)
    except Exception as e:
        print(f"[worker] embed thread import error: {e}", flush=True)
        traceback.print_exc()
        return

    r = _redis()
    while True:
        item = r.blpop("embed_jobs", timeout=5)
        if item is None:
            continue
        try:
            payload = json.loads(item[1])
            asyncio.run(process_embed_job(payload["version_id"], SessionLocal))
        except Exception as e:
            print(f"[worker] embed error: {e}", flush=True)
            traceback.print_exc()


def probe_thread():
    """Blocking thread that consumes probe_runs."""
    try:
        from src.tasks.probe_runner import _run_probe
        SessionLocal = _make_session_factory()
        print("[worker] probe thread ready", flush=True)
    except Exception as e:
        print(f"[worker] probe thread import error: {e}", flush=True)
        traceback.print_exc()
        return

    r = _redis()
    while True:
        item = r.blpop("probe_runs", timeout=5)
        if item is None:
            continue
        try:
            payload = json.loads(item[1])
            print(f"[worker] starting probe run {payload['run_id']}: {len(payload['probe_ids'])} probes × {len(payload['model_slugs'])} models", flush=True)
            asyncio.run(_run_probe(
                payload["run_id"],
                payload["probe_ids"],
                payload["model_slugs"],
                SessionLocal,
            ))
        except Exception as e:
            print(f"[worker] probe error: {e}", flush=True)
            traceback.print_exc()


def main():
    print("[worker] Starting", flush=True)

    # Init DB (create tables) in main thread
    asyncio.run(_init())
    print("[worker] DB initialized", flush=True)

    t1 = threading.Thread(target=embed_thread, daemon=True, name="embed")
    t2 = threading.Thread(target=probe_thread, daemon=True, name="probe")
    t1.start()
    t2.start()

    print("[worker] both threads started", flush=True)

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("[worker] shutting down", flush=True)


async def _init():
    from packages.db.session import init_db
    await init_db()


if __name__ == "__main__":
    main()
