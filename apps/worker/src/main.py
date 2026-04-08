"""Worker entry point — runs embed and extract loops as daemon threads."""
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

EXTRACT_WORKERS = int(os.getenv("EXTRACT_WORKERS", "3"))


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


def extract_thread():
    """Blocking thread that consumes extract_jobs."""
    try:
        from src.extractor.eval_extractor import extract_evals_from_version
        SessionLocal = _make_session_factory()
        print("[worker] extract thread ready", flush=True)
    except Exception as e:
        print(f"[worker] extract thread import error: {e}", flush=True)
        traceback.print_exc()
        return

    r = _redis()
    while True:
        item = r.blpop("extract_jobs", timeout=5)
        if item is None:
            continue
        try:
            payload = json.loads(item[1])
            count = asyncio.run(extract_evals_from_version(
                payload["version_id"], SessionLocal,
            ))
            print(f"[worker] extracted {count} evals from version {payload['version_id']}", flush=True)
        except Exception as e:
            print(f"[worker] extract error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(30)  # Longer delay on error


def main():
    print("[worker] Starting", flush=True)

    # Init DB (create tables) in main thread
    asyncio.run(_init())
    print("[worker] DB initialized", flush=True)

    t1 = threading.Thread(target=embed_thread, daemon=True, name="embed")
    t1.start()

    extract_threads = []
    for i in range(EXTRACT_WORKERS):
        t = threading.Thread(target=extract_thread, daemon=True, name=f"extract-{i}")
        t.start()
        extract_threads.append(t)

    print(f"[worker] embed + {EXTRACT_WORKERS} extract threads started", flush=True)

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
