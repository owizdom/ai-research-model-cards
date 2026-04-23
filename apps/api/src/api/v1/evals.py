from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.deps import get_db
from src.schemas.eval import (
    BenchmarkRead, EvalResultRead, ComparisonResult, TimelinePoint, PerCardEvalPoint,
    CategoryTimelinePoint, FragmentationResponse, FragmentationBucket, LabUniqueness,
    FragmentationView,
)
from packages.db.models import (
    BenchmarkDefinition, EvalResult, ExtractionRun,
    ModelFamily, ModelGeneration, DocumentVersion, Document, Lab,
)

import json
import redis
import os


# Benchmark family canonicalization.
# Collapses variant names (mmlu_pro, gpqa_diamond, swe_bench_verified) onto a
# shared family so the fragmentation stat isn't inflated by naming variants.
# Rule is SQL-side to keep the histogram query a single round trip.
FAMILY_SQL_EXPR = """
  CASE
    WHEN bd.slug = 'mmlu' OR bd.slug LIKE 'mmlu\\_%' OR bd.slug = 'mmmlu' THEN 'mmlu'
    WHEN bd.slug LIKE 'humaneval%' THEN 'humaneval'
    WHEN bd.slug LIKE 'gpqa%' THEN 'gpqa'
    WHEN bd.slug LIKE 'swe\\_bench%' THEN 'swe_bench'
    WHEN bd.slug = 'math' OR bd.slug LIKE 'math\\_%' THEN 'math'
    WHEN bd.slug = 'gsm8k' OR bd.slug LIKE 'gsm\\_%' THEN 'gsm'
    WHEN bd.slug LIKE 'big\\_bench%' THEN 'big_bench'
    WHEN bd.slug LIKE 'livecodebench%' THEN 'livecodebench'
    WHEN bd.slug LIKE 'arc\\_%' THEN 'arc'
    WHEN bd.slug LIKE 'aime%' THEN 'aime'
    ELSE bd.slug
  END
"""

router = APIRouter()


@router.get("/benchmarks", response_model=list[BenchmarkRead])
async def list_benchmarks(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(BenchmarkDefinition).order_by(BenchmarkDefinition.category, BenchmarkDefinition.name)
    if category:
        q = q.where(BenchmarkDefinition.category == category)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/results/by-document/{document_id}")
async def evals_by_document(document_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, document_id)
    if not doc:
        return {"document_id": document_id, "title": None, "lab_name": None, "evals": []}

    # Get latest version
    version_q = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_date.desc())
        .limit(1)
    )
    version_result = await db.execute(version_q)
    version = version_result.scalar_one_or_none()
    if not version:
        return {"document_id": document_id, "title": doc.title, "lab_name": None, "evals": []}

    evals_q = (
        select(EvalResult)
        .options(selectinload(EvalResult.benchmark), selectinload(EvalResult.generation))
        .where(EvalResult.document_version_id == version.id)
        .order_by(EvalResult.score.desc())
    )
    evals_result = await db.execute(evals_q)
    evals = evals_result.scalars().all()

    lab = await db.get(Lab, doc.lab_id) if doc.lab_id else None

    return {
        "document_id": document_id,
        "title": doc.title,
        "lab_name": lab.name if lab else None,
        "version_id": version.id,
        "evals": [EvalResultRead.model_validate(e) for e in evals],
    }


@router.get("/compare/generations", response_model=ComparisonResult)
async def compare_generations(
    family_slug: str,
    benchmark_slugs: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    family_q = select(ModelFamily).where(ModelFamily.slug == family_slug)
    family_result = await db.execute(family_q)
    family = family_result.scalar_one_or_none()
    if not family:
        return ComparisonResult(
            family_slug=family_slug, family_name="", benchmarks=[], generations=[], matrix={}
        )

    gens_q = select(ModelGeneration).where(ModelGeneration.family_id == family.id)
    gens_result = await db.execute(gens_q)
    generations = gens_result.scalars().all()

    # Get all eval results for these generations
    gen_ids = [g.id for g in generations]
    if not gen_ids:
        return ComparisonResult(
            family_slug=family_slug, family_name=family.name,
            benchmarks=[], generations=[], matrix={},
        )

    evals_q = (
        select(EvalResult)
        .options(selectinload(EvalResult.benchmark), selectinload(EvalResult.generation))
        .where(EvalResult.generation_id.in_(gen_ids))
    )
    if benchmark_slugs:
        slugs = [s.strip() for s in benchmark_slugs.split(",")]
        evals_q = evals_q.join(BenchmarkDefinition).where(BenchmarkDefinition.slug.in_(slugs))

    evals_result = await db.execute(evals_q)
    evals = evals_result.scalars().all()

    # Build matrix: {generation_slug: {benchmark_slug: score}}
    matrix: dict[str, dict[str, float | None]] = {}
    benchmark_set: set[str] = set()
    gen_slugs: list[str] = [g.slug for g in generations]

    for g in generations:
        matrix[g.slug] = {}

    for e in evals:
        if e.generation and e.benchmark:
            matrix.setdefault(e.generation.slug, {})[e.benchmark.slug] = e.score
            benchmark_set.add(e.benchmark.slug)

    return ComparisonResult(
        family_slug=family_slug,
        family_name=family.name,
        benchmarks=sorted(benchmark_set),
        generations=gen_slugs,
        matrix=matrix,
    )


@router.get("/timeline", response_model=list[TimelinePoint])
async def eval_timeline(
    lab_slug: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    base = """
        SELECT
            l.slug AS lab_slug,
            to_char(dv.version_date, 'YYYY-MM') AS period,
            COUNT(DISTINCT er.id) AS eval_count,
            COUNT(DISTINCT dv.document_id) AS document_count
        FROM eval_results er
        JOIN document_versions dv ON er.document_version_id = dv.id
        JOIN documents d ON dv.document_id = d.id
        JOIN labs l ON d.lab_id = l.id
    """
    suffix = " GROUP BY l.slug, to_char(dv.version_date, 'YYYY-MM') ORDER BY period, l.slug"
    if lab_slug:
        result = await db.execute(text(base + " WHERE l.slug = :lab_slug" + suffix), {"lab_slug": lab_slug})
    else:
        result = await db.execute(text(base + suffix))
    rows = result.fetchall()
    return [
        TimelinePoint(
            period=row.period, lab_slug=row.lab_slug,
            eval_count=row.eval_count, document_count=row.document_count,
        )
        for row in rows
    ]


@router.get("/per-card", response_model=list[PerCardEvalPoint])
async def eval_per_card(db: AsyncSession = Depends(get_db)):
    """Per-card eval counts with dates — for the over-time trend chart."""
    q = text("""
        SELECT d.id AS document_id, d.title AS document_title,
               l.slug AS lab_slug, dv.version_date::text AS version_date,
               COUNT(er.id) AS eval_count
        FROM eval_results er
        JOIN document_versions dv ON er.document_version_id = dv.id
        JOIN documents d ON dv.document_id = d.id
        JOIN labs l ON d.lab_id = l.id
        GROUP BY d.id, d.title, l.slug, dv.version_date
        ORDER BY dv.version_date
    """)
    result = await db.execute(q)
    return [
        PerCardEvalPoint(
            document_id=row.document_id, document_title=row.document_title,
            lab_slug=row.lab_slug, version_date=row.version_date,
            eval_count=row.eval_count,
        )
        for row in result.fetchall()
    ]


@router.get("/depth")
async def eval_depth(db: AsyncSession = Depends(get_db)):
    """Eval counts per benchmark category per lab — for the Eval Depth tab."""
    q = text("""
        SELECT
            l.slug AS lab_slug,
            bd.category AS benchmark_category,
            COUNT(DISTINCT er.id) AS eval_count
        FROM eval_results er
        JOIN document_versions dv ON er.document_version_id = dv.id
        JOIN documents d ON dv.document_id = d.id
        JOIN labs l ON d.lab_id = l.id
        JOIN benchmark_definitions bd ON er.benchmark_id = bd.id
        GROUP BY l.slug, bd.category
        ORDER BY bd.category, l.slug
    """)
    result = await db.execute(q)
    rows = result.fetchall()
    # Build {category: {lab: count}}
    depth: dict[str, dict[str, int]] = {}
    for row in rows:
        if row.benchmark_category not in depth:
            depth[row.benchmark_category] = {}
        depth[row.benchmark_category][row.lab_slug] = row.eval_count
    return depth


@router.get("/category-timeline", response_model=list[CategoryTimelinePoint])
async def category_timeline(db: AsyncSession = Depends(get_db)):
    """Eval counts per benchmark category per model card — for trend charts."""
    q = text("""
        SELECT d.slug AS document_slug, d.title AS document_title,
               l.slug AS lab_slug, l.name AS lab_name,
               bd.category AS benchmark_category,
               COUNT(DISTINCT er.id) AS eval_count
        FROM eval_results er
        JOIN document_versions dv ON er.document_version_id = dv.id
        JOIN documents d ON dv.document_id = d.id
        JOIN labs l ON d.lab_id = l.id
        JOIN benchmark_definitions bd ON er.benchmark_id = bd.id
        GROUP BY d.slug, d.title, l.slug, l.name, bd.category
        ORDER BY l.slug, d.slug, bd.category
    """)
    result = await db.execute(q)
    return [
        CategoryTimelinePoint(
            document_slug=r.document_slug, document_title=r.document_title,
            lab_slug=r.lab_slug, lab_name=r.lab_name,
            benchmark_category=r.benchmark_category,
            eval_count=r.eval_count,
        )
        for r in result.fetchall()
    ]


@router.get("/fragmentation", response_model=FragmentationResponse)
async def fragmentation(db: AsyncSession = Depends(get_db)):
    """
    How fragmented is benchmark reporting across frontier labs?

    Returns two views:
      - raw: one row per distinct benchmark slug
      - families: collapses naming variants (mmlu_pro→mmlu, gpqa_diamond→gpqa, etc.)

    Each view has a histogram (# benchmarks × # labs reporting) with the benchmark
    slugs per bucket, so the UI can render "click a column to see the benchmarks."
    """
    # One base query: (benchmark_slug, family_slug, lab_slug) distinct tuples.
    rows = (await db.execute(text(f"""
        SELECT DISTINCT
            bd.slug AS slug,
            bd.name AS name,
            {FAMILY_SQL_EXPR} AS family,
            l.slug AS lab_slug,
            l.name AS lab_name
        FROM eval_results er
        JOIN benchmark_definitions bd ON er.benchmark_id = bd.id
        JOIN document_versions dv ON er.document_version_id = dv.id
        JOIN documents d ON dv.document_id = d.id
        JOIN labs l ON d.lab_id = l.id
    """))).fetchall()

    # Build raw view: slug → set[lab]
    raw_benchmark_labs: dict[str, set[str]] = {}
    raw_names: dict[str, str] = {}
    for r in rows:
        raw_benchmark_labs.setdefault(r.slug, set()).add(r.lab_slug)
        raw_names[r.slug] = r.name

    # Build family view: family → set[lab], family → set[member_slugs]
    family_labs: dict[str, set[str]] = {}
    family_members: dict[str, set[str]] = {}
    for r in rows:
        family_labs.setdefault(r.family, set()).add(r.lab_slug)
        family_members.setdefault(r.family, set()).add(r.slug)

    def build_view(benchmark_labs: dict[str, set[str]], name_lookup) -> FragmentationView:
        bucket_slugs: dict[int, list[str]] = {}
        for slug, labs in benchmark_labs.items():
            bucket_slugs.setdefault(len(labs), []).append(slug)

        histogram = [
            FragmentationBucket(
                n_labs=n,
                count=len(sorted_slugs := sorted(bucket_slugs[n])),
                slugs=sorted_slugs,
                names={s: name_lookup(s) for s in sorted_slugs},
            )
            for n in sorted(bucket_slugs.keys())
        ]
        total = len(benchmark_labs)
        one_lab = len(bucket_slugs.get(1, []))
        return FragmentationView(
            total=total,
            one_lab_count=one_lab,
            pct_unique=round(one_lab / total * 100) if total else 0,
            histogram=histogram,
        )

    def family_name(fam: str) -> str:
        # If family == a real slug, use that benchmark's display name.
        # Otherwise it's already a canonical lowercase family id.
        return raw_names.get(fam, fam.replace("_", " ").upper())

    raw_view = build_view(raw_benchmark_labs, lambda s: raw_names.get(s, s))
    family_view = build_view(family_labs, family_name)

    # Per-lab uniqueness (raw view — clearer story for "what only Lab X reports")
    lab_totals: dict[str, set[str]] = {}
    lab_names: dict[str, str] = {}
    for r in rows:
        lab_totals.setdefault(r.lab_slug, set()).add(r.slug)
        lab_names[r.lab_slug] = r.lab_name

    unique_to: dict[str, list[str]] = {}
    for slug, labs in raw_benchmark_labs.items():
        if len(labs) == 1:
            unique_to.setdefault(next(iter(labs)), []).append(slug)

    by_lab = []
    for lab_slug in sorted(lab_totals.keys()):
        uniques = sorted(unique_to.get(lab_slug, []))
        total = len(lab_totals[lab_slug])
        by_lab.append(LabUniqueness(
            lab_slug=lab_slug,
            lab_name=lab_names[lab_slug],
            total_reported=total,
            only_them_count=len(uniques),
            only_them=[{"slug": s, "name": raw_names.get(s, s)} for s in uniques],
        ))
    by_lab.sort(key=lambda x: x.total_reported, reverse=True)

    return FragmentationResponse(
        labs=sorted(lab_totals.keys()),
        raw=raw_view,
        families=family_view,
        by_lab=by_lab,
    )


@router.post("/extract/{document_version_id}", status_code=202)
async def trigger_extraction(document_version_id: int, db: AsyncSession = Depends(get_db)):
    version = await db.get(DocumentVersion, document_version_id)
    if not version:
        return {"error": "Version not found"}

    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    r.rpush("extract_jobs", json.dumps({"version_id": document_version_id}))
    return {"version_id": document_version_id, "status": "queued"}
