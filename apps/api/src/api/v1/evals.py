from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.deps import get_db
from src.schemas.eval import (
    BenchmarkRead, EvalResultRead, ComparisonResult, TimelinePoint, PerCardEvalPoint,
    CategoryTimelinePoint, FragmentationResponse, FragmentationBucket, LabUniqueness,
    FragmentationView, EvalsByDocumentResponse, ExtractionTriggerResponse,
    DivergentReport, DivergentGroup, DivergenceSummary, DivergenceResponse,
)
from packages.db.models import (
    BenchmarkDefinition, EvalResult, ExtractionRun,
    ModelFamily, ModelGeneration, DocumentVersion, Document, Lab,
)

import json
import redis
import os


# Heuristic category classifier. The DB category column is mostly "other"
# (277/319) because seeding never caught up with extraction. This gives us
# usable buckets for the homepage view. Rules are ordered — first match wins.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("safety", (
        "safety", "harm", "refusal", "bias", "toxic", "jailbreak", "guard",
        "misuse", "sandbag", "deception", "scheming", "alignment", "apollo",
        "child ", "cbrn", "bio ", "biolp", "chem ", "cyber", "violation",
        "violative", "evasion", "unjustified", "wildchat", "xstest", "bbq",
        "protocolqa", "agentharm", "strongreject", "stereotype", "hate",
        "benign request", "prompt injection", "virology", "sequence design",
        "protocol design", "lab_bench", "lab-bench", "lab bench",
        "creative biology", "evaluation awareness", "dual-use", "dual use",
        "malicious", "refuse",
        "red team", "red-team", "redteam", "biorisk", "biological risk",
        "bioweapon", "pairwise bio", "cyscenario", "network attack",
        "sabotage", "disallowed content", "reasoning monitor",
        "autonomous replication", "adaptation (ara)", " ara ",
        "ungrounded inference", "sensitive trait", "speaker identif",
        "person identif", "personqa", "model mistake", "voice output classif",
        "topical classif", "confirmation recall", "confirmations recall",
        "vulnerability research", "exploitation", "facts grounding",
        "troubleshootingbench", "troubleshooting bench",
        "cloning", "input filter", "makemesay", "make me say",
        "sycophancy", "mask",
    )),
    ("coding", (
        "code", "swe", "humaneval", "mbpp", "apps", "livecodebench",
        "programming", "bugfix", "lcb", "spreadsheet", "aider",
        "bird-sql", "bird sql", "paperbench", "openai prs",
        "interview coding", "ml interview", "re-bench", "re bench",
        "production benchmark", "interview", "open-rewrite",
    )),
    ("math", (
        "math", "aime", "gsm", "amc", "olympiad", "arithmetic",
        "usamo", "putnam", "imo 202", "physicsfinals",
    )),
    ("multimodal", (
        "vision", "mmmu", "chart", "diagram", "visual", "ai2d", "docvqa",
        "mathvista", "figqa", "image", "ocr", "video", "charxiv",
        "egoschema", "vibe-eval",
    )),
    ("multilingual", (
        "multilingual", "mgsm", "mmmlu", "tydiqa", "xlingual", "translation",
        "xcopa", "xnli", "xquad", "wmt", "wikilingua", "xlsum",
        "covost", "hausa", "uhura",
    )),
    ("reasoning", (
        "gpqa", "arc_challenge", "arc-agi", "arc-c", "hellaswag", "winogrande",
        "drop", "bbh", "big_bench", "boolq", "piqa", "siqa", "commonsense",
        "graphwalk", "time series", "forecast", "agi eval", "agieval",
    )),
    ("knowledge", (
        "mmlu", "simpleqa", "browsecomp", "triviaqa", "naturalquestions",
        "trivia", "quality", "gre ", "lsat", "mbe", "race-h", "race_h",
        "hle", "humanity", "deepsearch", "opqa", "medmcqa",
        "world knowledge", "reading comprehension", "quac", "squad",
    )),
    ("agentic", (
        "agent", "tool", "browser", "computer", "osworld", "metr",
        "webarena", "autonomy", "operator", "mle", "task completion",
        "terminal", "tau-bench", "tau bench", "tau2", "τ²", "mcp",
        "kernel optimization", "training optimization", "text-based rl",
        "internal ai research", "gdpval",
    )),
    ("instruction_following", (
        "ifeval", "instruction",
    )),
    ("long_context", (
        "long_context", "longcontext", "long context", "needle", "haystack",
        "ruler", "mrcr", "infinitebench", "key-value retrieval",
    )),
    ("arena", (
        "arena", "mt-bench", "mt bench", "wildbench", "human preference",
        "human evaluation", "human feedback",
    )),
]


def _classify(slug: str, name: str, db_category: str | None) -> str:
    """Pick a display category. Prefer DB category if not 'other'."""
    if db_category and db_category not in ("other", "general_knowledge"):
        # Map some DB categories to shared display buckets
        return {"multimodal": "multimodal", "agent": "agentic"}.get(db_category, db_category)
    hay = f"{slug} {name}".lower()
    for cat, keywords in _CATEGORY_RULES:
        if any(k in hay for k in keywords):
            return cat
    return "other"


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


@router.get("/results/by-document/{document_id}", response_model=EvalsByDocumentResponse)
async def evals_by_document(document_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, document_id)
    if not doc:
        return EvalsByDocumentResponse(document_id=document_id)

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
        return EvalsByDocumentResponse(document_id=document_id, title=doc.title)

    evals_q = (
        select(EvalResult)
        .options(selectinload(EvalResult.benchmark), selectinload(EvalResult.generation))
        .where(EvalResult.document_version_id == version.id)
        .order_by(EvalResult.score.desc())
    )
    evals_result = await db.execute(evals_q)
    evals = evals_result.scalars().all()

    lab = await db.get(Lab, doc.lab_id) if doc.lab_id else None

    return EvalsByDocumentResponse(
        document_id=document_id,
        title=doc.title,
        lab_name=lab.name if lab else None,
        version_id=version.id,
        evals=[EvalResultRead.model_validate(e) for e in evals],
    )


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


@router.get("/depth", response_model=dict[str, dict[str, int]])
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
            bd.category AS category,
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
    raw_categories: dict[str, str] = {}
    for r in rows:
        raw_benchmark_labs.setdefault(r.slug, set()).add(r.lab_slug)
        raw_names[r.slug] = r.name
        raw_categories[r.slug] = _classify(r.slug, r.name, r.category)

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
            only_them=[
                {"slug": s, "name": raw_names.get(s, s), "category": raw_categories.get(s, "other")}
                for s in uniques
            ],
        ))
    by_lab.sort(key=lambda x: x.total_reported, reverse=True)

    return FragmentationResponse(
        labs=sorted(lab_totals.keys()),
        raw=raw_view,
        families=family_view,
        by_lab=by_lab,
    )


@router.post(
    "/extract/{document_version_id}",
    status_code=202,
    response_model=ExtractionTriggerResponse,
)
async def trigger_extraction(document_version_id: int, db: AsyncSession = Depends(get_db)):
    version = await db.get(DocumentVersion, document_version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"Document version {document_version_id} not found")

    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    r.rpush("extract_jobs", json.dumps({"version_id": document_version_id}))
    return ExtractionTriggerResponse(version_id=document_version_id, status="queued")


# Per-group caveat documenting the metric-path limitation. Until we land the
# 5-level rollout hierarchy (paper Section 3.2), groups may include rows that
# actually report different scoring rules on the same benchmark name — e.g.
# MMLU-Pro / accuracy vs MMLU-Pro / CoT-correct. Surfaced in-band so consumers
# don't read these as confirmed measurement disagreement.
_METRIC_PATH_CAVEAT = (
    "Score spread may reflect different scoring rules on the same benchmark "
    "name (metric-path differentiation not yet implemented). Treat as a "
    "possible-conflict signal rather than confirmed disagreement."
)


@router.get("/divergence", response_model=DivergenceResponse)
async def divergence(
    threshold: float = Query(
        5.0, ge=0.0,
        description="Minimum score spread to flag as divergent. Score units "
                    "(percentage-points for the dominant '%' metric_unit benchmarks).",
    ),
    benchmark_slug: str | None = Query(None, description="Filter to one benchmark."),
    model_name: str | None = Query(None, description="Filter to one model_name."),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Cross-source comparability signal (EvalCards paper Section 4.2).

    Groups eval results by (benchmark_slug, model_name) tuples that have
    at least 2 reports, then flags groups whose max-min score spread
    exceeds `threshold`. For each flagged group, returns the contributing
    reports plus which setup fields (variant/shot_count/method/language/
    training_state) differ across them, and whether the disagreement
    crosses the self-reported / third-party boundary.

    Limitations:
      - Without metric-path differentiation, groups may include rows
        scored under different rules on the same benchmark name. Each
        group carries `caveat` explaining this.
      - Rows without `model_name` cannot be grouped and are ignored.
    """
    # Divergence requires ≥2 distinct *documents* — without that filter, a single
    # card reporting sub-task scores under the same benchmark name (e.g. GPT-4.5
    # on long_form_biological_risk_questions × Magnification/Acquisition/...) flags
    # as "divergent" even though it's a within-document variance, not multi-source
    # disagreement. Paper Section 4.2 explicitly scopes the signal to cross-source.
    summary_sql = text("""
        WITH g AS (
            SELECT er.benchmark_id, er.model_name,
                   MAX(er.score) - MIN(er.score) AS spread,
                   COUNT(*) AS cnt,
                   COUNT(DISTINCT dv.document_id) AS doc_count,
                   COUNT(DISTINCT er.is_self_reported) AS party_count
            FROM eval_results er
            JOIN document_versions dv ON er.document_version_id = dv.id
            WHERE er.score IS NOT NULL AND er.model_name IS NOT NULL
            GROUP BY er.benchmark_id, er.model_name
            HAVING COUNT(DISTINCT dv.document_id) >= 2
        )
        SELECT
            COUNT(*) AS total_pairs,
            COUNT(*) FILTER (WHERE spread > :threshold) AS divergent,
            COUNT(*) FILTER (WHERE spread > :threshold AND party_count > 1) AS cross_party_divergent,
            COALESCE(AVG(spread) FILTER (WHERE spread > :threshold), 0)::float AS avg_spread
        FROM g
    """)
    summary_row = (await db.execute(summary_sql, {"threshold": threshold})).first()

    detail_sql = text("""
        WITH group_stats AS (
            SELECT er.benchmark_id, er.model_name,
                   MAX(er.score) - MIN(er.score) AS spread,
                   COUNT(DISTINCT dv.document_id) AS doc_count
            FROM eval_results er
            JOIN benchmark_definitions bd ON er.benchmark_id = bd.id
            JOIN document_versions dv ON er.document_version_id = dv.id
            WHERE er.score IS NOT NULL AND er.model_name IS NOT NULL
              AND (CAST(:benchmark_slug AS text) IS NULL OR bd.slug = :benchmark_slug)
              AND (CAST(:model_name AS text) IS NULL OR er.model_name = :model_name)
            GROUP BY er.benchmark_id, er.model_name
            HAVING COUNT(DISTINCT dv.document_id) >= 2
              AND MAX(er.score) - MIN(er.score) > :threshold
        )
        SELECT
            er.id AS eval_id,
            bd.slug AS benchmark_slug,
            bd.name AS benchmark_name,
            er.model_name,
            er.score,
            er.variant,
            er.shot_count,
            er.method,
            er.language,
            er.training_state,
            er.is_self_reported,
            dv.document_id,
            d.title AS document_title,
            l.slug AS lab_slug,
            gs.spread AS group_spread,
            gs.doc_count AS group_doc_count
        FROM eval_results er
        JOIN benchmark_definitions bd ON er.benchmark_id = bd.id
        JOIN document_versions dv ON er.document_version_id = dv.id
        JOIN documents d ON dv.document_id = d.id
        LEFT JOIN labs l ON d.lab_id = l.id
        JOIN group_stats gs ON gs.benchmark_id = er.benchmark_id
                            AND gs.model_name = er.model_name
        WHERE er.score IS NOT NULL AND er.model_name IS NOT NULL
        ORDER BY gs.spread DESC, bd.slug, er.model_name, er.score DESC
    """)
    rows = (await db.execute(detail_sql, {
        "threshold": threshold,
        "benchmark_slug": benchmark_slug,
        "model_name": model_name,
    })).fetchall()

    # Bucket rows by (benchmark_slug, model_name) preserving insertion order.
    buckets: dict[tuple[str, str], list] = {}
    for row in rows:
        buckets.setdefault((row.benchmark_slug, row.model_name), []).append(row)

    groups: list[DivergentGroup] = []
    for (slug, model), group_rows in buckets.items():
        reports = [
            DivergentReport(
                eval_id=r.eval_id,
                document_id=r.document_id,
                document_title=r.document_title,
                lab_slug=r.lab_slug,
                score=float(r.score),
                variant=r.variant,
                shot_count=r.shot_count,
                method=r.method,
                language=r.language,
                training_state=r.training_state,
                is_self_reported=r.is_self_reported,
            )
            for r in group_rows
        ]
        differing = [
            f for f in ("variant", "shot_count", "method", "language", "training_state")
            if len({getattr(r, f) for r in reports}) > 1
        ]
        cross_party = len({r.is_self_reported for r in reports}) > 1
        scores = [r.score for r in reports]
        groups.append(DivergentGroup(
            benchmark_slug=slug,
            benchmark_name=group_rows[0].benchmark_name,
            model_name=model,
            report_count=len(reports),
            score_min=min(scores),
            score_max=max(scores),
            score_spread=float(group_rows[0].group_spread),
            cross_party=cross_party,
            differing_fields=differing,
            reports=reports,
            caveat=_METRIC_PATH_CAVEAT,
        ))

    # Apply limit after grouping (groups are already sorted by spread desc).
    returned_groups = groups[:limit]

    summary = DivergenceSummary(
        threshold=threshold,
        total_pairs_scanned=summary_row.total_pairs if summary_row else 0,
        divergent_pairs=summary_row.divergent if summary_row else 0,
        cross_party_divergent_pairs=summary_row.cross_party_divergent if summary_row else 0,
        avg_spread_among_divergent=float(summary_row.avg_spread) if summary_row else 0.0,
    )

    return DivergenceResponse(
        summary=summary,
        groups=returned_groups,
        returned=len(returned_groups),
    )
