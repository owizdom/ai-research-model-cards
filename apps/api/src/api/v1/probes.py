import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.core.deps import get_db
from src.core.config import settings
from src.schemas.probe import ProbeRead, ProbeRunSummary, ProbeRunDetail, RunProbesRequest
from packages.db.models import ProbeDefinition, ProbeRun, ProbeResponse

router = APIRouter()


@router.get("", response_model=list[ProbeRead])
async def list_probes(
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    q = select(ProbeDefinition)
    if active_only:
        q = q.where(ProbeDefinition.is_active == True)  # noqa
    if category:
        q = q.where(ProbeDefinition.category == category)
    result = await db.execute(q.order_by(ProbeDefinition.category, ProbeDefinition.probe_key))
    return result.scalars().all()


@router.get("/runs", response_model=list[ProbeRunSummary])
async def list_runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProbeRun).order_by(ProbeRun.started_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/runs/{run_id}", response_model=ProbeRunDetail)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProbeRun)
        .options(selectinload(ProbeRun.responses).selectinload(ProbeResponse.probe))
        .where(ProbeRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/runs", status_code=202)
async def trigger_run(body: RunProbesRequest, db: AsyncSession = Depends(get_db)):
    import redis
    run = ProbeRun(
        triggered_by="user",
        probe_count=len(body.probe_ids) if body.probe_ids else None,
        model_count=len(body.model_slugs) if body.model_slugs else None,
        status="queued",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    r = redis.Redis.from_url(settings.REDIS_URL)
    r.rpush("probe_runs", json.dumps({
        "run_id": run.id,
        "probe_ids": body.probe_ids,
        "model_slugs": body.model_slugs,
    }))
    return {"run_id": run.id, "status": "queued"}
