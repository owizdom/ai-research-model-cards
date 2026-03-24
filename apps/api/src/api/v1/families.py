from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.deps import get_db
from src.schemas.eval import FamilyRead, FamilyDetail, GenerationRead
from packages.db.models import ModelFamily, ModelGeneration, EvalResult, Lab

router = APIRouter()


@router.get("/", response_model=list[FamilyRead])
async def list_families(db: AsyncSession = Depends(get_db)):
    q = (
        select(
            ModelFamily.id,
            ModelFamily.slug,
            ModelFamily.name,
            Lab.slug.label("lab_slug"),
            func.count(ModelGeneration.id).label("generation_count"),
        )
        .join(Lab, ModelFamily.lab_id == Lab.id)
        .outerjoin(ModelGeneration, ModelGeneration.family_id == ModelFamily.id)
        .group_by(ModelFamily.id, Lab.slug)
        .order_by(ModelFamily.name)
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        FamilyRead(
            id=r.id, slug=r.slug, name=r.name,
            lab_slug=r.lab_slug, generation_count=r.generation_count,
        )
        for r in rows
    ]


@router.get("/{family_slug}", response_model=FamilyDetail)
async def get_family(family_slug: str, db: AsyncSession = Depends(get_db)):
    family_q = (
        select(ModelFamily)
        .options(selectinload(ModelFamily.generations))
        .where(ModelFamily.slug == family_slug)
    )
    family_result = await db.execute(family_q)
    family = family_result.scalar_one_or_none()
    if not family:
        return FamilyDetail(
            id=0, slug=family_slug, name="", lab_slug="",
            generation_count=0, generations=[],
        )

    lab = await db.get(Lab, family.lab_id)

    # Get eval counts per generation
    gen_evals = {}
    for gen in family.generations:
        count_q = select(func.count(EvalResult.id)).where(EvalResult.generation_id == gen.id)
        count_result = await db.execute(count_q)
        gen_evals[gen.id] = count_result.scalar() or 0

    generations = [
        GenerationRead(
            id=g.id, slug=g.slug, name=g.name,
            version_label=g.version_label,
            release_date=g.release_date,
            parameter_count=g.parameter_count,
            eval_count=gen_evals.get(g.id, 0),
            document_id=g.document_id,
        )
        for g in family.generations
    ]

    return FamilyDetail(
        id=family.id, slug=family.slug, name=family.name,
        lab_slug=lab.slug if lab else "",
        generation_count=len(generations),
        generations=generations,
    )
