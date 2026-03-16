from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.core.deps import get_db
from src.schemas.probe import ProbeResponseRead
from packages.db.models import ProbeResponse, SlantScore

router = APIRouter()


@router.get("", response_model=list[ProbeResponseRead])
async def list_responses(
    model_slug: Optional[str] = None,
    probe_id: Optional[int] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(ProbeResponse)
        .options(
            selectinload(ProbeResponse.probe),
            selectinload(ProbeResponse.slant_score),
        )
        .order_by(ProbeResponse.recorded_at.desc())
    )
    if model_slug:
        q = q.where(ProbeResponse.model_slug == model_slug)
    if probe_id:
        q = q.where(ProbeResponse.probe_id == probe_id)
    result = await db.execute(q.limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/{response_id}", response_model=ProbeResponseRead)
async def get_response(response_id: int, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    result = await db.execute(
        select(ProbeResponse)
        .options(selectinload(ProbeResponse.probe), selectinload(ProbeResponse.slant_score))
        .where(ProbeResponse.id == response_id)
    )
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(404, "Response not found")
    return resp
