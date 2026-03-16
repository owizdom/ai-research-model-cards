"""Worker entry point — runs embed and probe loops concurrently."""
import asyncio
import os

from packages.db.session import init_db
from .embedder.pipeline import run_embed_loop
from .tasks.probe_runner import run_probe_loop


async def main():
    print("[worker] Starting")
    await init_db()

    await asyncio.gather(
        run_embed_loop(),
        run_probe_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
