"""Consume probe_runs queue, call LLMs, score slant, persist results."""
import asyncio
import json
import os
import traceback

import litellm
from sqlalchemy import select

from packages.db.models import ProbeRun, ProbeResponse, SlantScore, ProbeDefinition, AIModel
from ..analyzer.slant import score_text


async def _run_probe(run_id: int, probe_ids: list[int], model_slugs: list[str], SessionLocal=None) -> None:
    if SessionLocal is None:
        from packages.db.session import AsyncSessionLocal
        SessionLocal = AsyncSessionLocal

    async with SessionLocal() as db:
        run = await db.get(ProbeRun, run_id)
        if not run:
            print(f"[worker] probe run {run_id} not found", flush=True)
            return

        probes_result = await db.execute(
            select(ProbeDefinition).where(ProbeDefinition.id.in_(probe_ids))
        )
        probes = probes_result.scalars().all()

        if model_slugs:
            models_result = await db.execute(
                select(AIModel).where(AIModel.slug.in_(model_slugs), AIModel.is_active == True)  # noqa
            )
        else:
            models_result = await db.execute(
                select(AIModel).where(AIModel.is_active == True)  # noqa
            )
        models = models_result.scalars().all()

        total = len(probes) * len(models)
        done = 0
        errors = 0
        print(f"[worker] probe run {run_id}: {len(probes)} probes × {len(models)} models = {total} calls", flush=True)

        for probe in probes:
            for model in models:
                max_retries = 3
                for attempt in range(max_retries):
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
                            prompt_tokens=getattr(response.usage, 'prompt_tokens', 0) or 0,
                            completion_tokens=getattr(response.usage, 'completion_tokens', 0) or 0,
                        )
                        db.add(pr)
                        await db.flush()

                        scores = score_text(response_text)
                        db.add(SlantScore(
                            response_id=pr.id,
                            model_slug=model.slug,
                            probe_id=probe.id,
                            **scores,
                        ))
                        done += 1
                        print(f"[worker] {probe.probe_key} × {model.slug}: done ({done}/{total})", flush=True)
                        break  # success — exit retry loop
                    except Exception as e:
                        err_str = str(e)
                        if ("429" in err_str or "rate" in err_str.lower()) and attempt < max_retries - 1:
                            wait = 30 * (attempt + 1)
                            print(f"[worker] rate limited on {model.slug}, retry {attempt+1}/{max_retries} in {wait}s...", flush=True)
                            await asyncio.sleep(wait)
                            continue
                        errors += 1
                        done += 1
                        print(f"[worker] {probe.probe_key} × {model.slug}: {err_str[:100]}", flush=True)
                        break
                # Rate limit delay (Gemini free = 10 RPM, Groq free = 30 RPM)
                if "gemini" in model.litellm_id:
                    await asyncio.sleep(12)
                else:
                    await asyncio.sleep(2.5)

        run.status = "completed"
        db.add(run)
        await db.commit()
    print(f"[worker] Probe run {run_id} complete: {done - errors}/{total} ok, {errors} errors", flush=True)
