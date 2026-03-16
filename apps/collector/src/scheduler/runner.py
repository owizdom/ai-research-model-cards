"""Collector service entry point."""
import asyncio
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .jobs import collect_current, collect_history


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: asyncio.create_task(collect_current()),
        CronTrigger(hour=2, minute=0),
        id="nightly_collection",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        lambda: asyncio.create_task(collect_history()),
        CronTrigger(day_of_week="sun", hour=4, minute=0),
        id="weekly_history",
        replace_existing=True,
        misfire_grace_time=7200,
    )
    return scheduler


async def main():
    print("[collector] Starting")
    scheduler = create_scheduler()
    scheduler.start()

    if os.getenv("RUN_ON_START", "false").lower() == "true":
        print("[collector] RUN_ON_START — running now")
        await collect_current()

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
