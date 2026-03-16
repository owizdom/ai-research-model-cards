"""Consume probe_runs queue, call LLMs, score slant, persist results."""
import asyncio
import json
import os
import traceback

import redis
import litellm
from sqlalchemy import select

from packages.db.session import AsyncSessionLocal
from packages.db.models import ProbeRun, ProbeResponse, SlantScore, ProbeDefinition, AIModel
from ..analyzer.slant import score_text


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


async def _run_probe(run_id: int, probe_ids: list[int], model_slugs: list[str]) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(ProbeRun, run_id)
        if not run:
            print(f"[worker] probe run {run_id} not found")
            return

        probes_result = await db.execute(
            select(ProbeDefinition).where(ProbeDefinition.id.in_(probe_ids))
        )
        probes = probes_result.scalars().all()

        models_result = await db.execute(
            select(AIModel).where(AIModel.slug.in_(model_slugs))
        )
        models = models_result.scalars().all()

        total = len(probes) * len(models)
        done = 0
        for probe in probes:
            for model in models:
                try:
                    response = await litellm.acompletion(
                        model=model.litellm_id,
                        messages=[{"role": "user", "content": probe.prompt}],
                        max_tokens=512,
                        temperature=0.0,
                    )
                    response_text = response.choices[0].message.content or ""

                    pr = ProbeResponse(
                        run_id=run_id,
                        probe_id=probe.id,
                        model_slug=model.slug,
                        model_id=model.litellm_id,
                        prompt_text=probe.prompt,
                        response_text=response_text,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                    )
                    db.add(pr)
                    await db.flush()

                    scores = await asyncio.to_thread(score_text, response_text)
                    db.add(SlantScore(
                        response_id=pr.id,
                        model_slug=model.slug,
                        probe_id=probe.id,
                        **scores,
                    ))
                    done += 1
                    print(f"[worker] probe {probe.probe_key} × {model.slug}: done ({done}/{total})")
                except Exception as e:
                    print(f"[worker] probe {probe.probe_key} × {model.slug}: {e}")
                    done += 1

        run.status = "completed"
        db.add(run)
        await db.commit()
    print(f"[worker] Probe run {run_id} complete ({done}/{total})")


async def run_probe_loop() -> None:
    r = get_redis()
    print("[worker] probe loop started")
    while True:
        # Run blocking redis call in a thread so we don't block the event loop
        item = await asyncio.to_thread(r.blpop, "probe_runs", 5)
        if item is None:
            continue
        try:
            payload = json.loads(item[1])
            await _run_probe(
                payload["run_id"],
                payload["probe_ids"],
                payload["model_slugs"],
            )
        except Exception as e:
            print(f"[worker] probe runner error: {e}")
            traceback.print_exc()
