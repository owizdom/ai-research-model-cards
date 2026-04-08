from typing import Optional
from itertools import combinations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.deps import get_db
from src.schemas.analysis import IntersectionResult, TemporalPoint

router = APIRouter()


@router.get("", response_model=IntersectionResult)
async def get_intersection(
    lab_slugs: Optional[str] = Query(None, description="Comma-separated lab slugs"),
    doc_types: Optional[str] = Query(None),
    threshold: float = Query(0.25, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    lab_list = lab_slugs.split(",") if lab_slugs else None
    if not lab_list:
        r = await db.execute(text("SELECT DISTINCT slug FROM labs ORDER BY slug"))
        lab_list = [row[0] for row in r.fetchall()]
    if not lab_list:
        return IntersectionResult(matrix={}, covered_by_all=[], covered_by_none=[], unique_to={}, intersection_sets=[], lab_slugs=[], category_names={})

    doc_filter = ""
    if doc_types:
        types = ", ".join(f"'{t}'" for t in doc_types.split(","))
        doc_filter = f"AND d.doc_type IN ({types})"

    lab_filter = ", ".join(f"'{l}'" for l in lab_list)
    score_cols = ", ".join(
        f"MAX(dtm.similarity_score) FILTER (WHERE l.slug = '{lab}') as s_{i}"
        for i, lab in enumerate(lab_list)
    )

    sql = text(f"""
        SELECT tc.slug as cat_slug, tc.name as cat_name, {score_cols}
        FROM taxonomy_categories tc
        LEFT JOIN document_taxonomy_mappings dtm ON dtm.taxonomy_category_id = tc.id
        LEFT JOIN document_versions dv ON dv.id = dtm.document_version_id
        LEFT JOIN documents d ON d.id = dv.document_id {doc_filter}
        LEFT JOIN labs l ON l.id = d.lab_id AND l.slug IN ({lab_filter})
        WHERE tc.parent_id IS NULL
        GROUP BY tc.id, tc.slug, tc.name
        ORDER BY tc.name
    """)
    result = await db.execute(sql)
    rows = result.fetchall()

    matrix, category_names = {}, {}
    for row in rows:
        cat = row.cat_slug
        category_names[cat] = row.cat_name
        matrix[cat] = {lab: round(float(getattr(row, f"s_{i}") or 0), 4) for i, lab in enumerate(lab_list)}

    covered_by_all = [c for c, s in matrix.items() if all(s.get(l, 0) >= threshold for l in lab_list)]
    covered_by_none = [c for c, s in matrix.items() if all(s.get(l, 0) < threshold for l in lab_list)]
    unique_to = {lab: [] for lab in lab_list}
    for cat, scores in matrix.items():
        covered = [l for l in lab_list if scores.get(l, 0) >= threshold]
        if len(covered) == 1:
            unique_to[covered[0]].append(cat)

    sets = []
    for r in range(1, len(lab_list) + 1):
        for combo in combinations(lab_list, r):
            combo_set = set(combo)
            matching = [c for c, s in matrix.items() if {l for l in lab_list if s.get(l, 0) >= threshold} == combo_set]
            if matching:
                sets.append({"labs": list(combo), "categories": matching, "count": len(matching)})
    sets.sort(key=lambda x: x["count"], reverse=True)

    return IntersectionResult(
        matrix=matrix, covered_by_all=covered_by_all, covered_by_none=covered_by_none,
        unique_to=unique_to, intersection_sets=sets, lab_slugs=lab_list, category_names=category_names,
    )


@router.get("/temporal", response_model=list[TemporalPoint])
async def get_temporal(db: AsyncSession = Depends(get_db)):
    r = await db.execute(text("SELECT MIN(version_date), MAX(version_date) FROM document_versions"))
    row = r.fetchone()
    if not row or not row[0]:
        return []
    result = await get_intersection(db=db)
    total = len(result.matrix)
    covered = len(result.covered_by_all)
    return [TemporalPoint(
        period_start=row[0].isoformat(), period_end=row[1].isoformat(),
        covered_by_all_count=covered, total_categories=total,
        convergence_score=round(covered / total, 4) if total > 0 else 0.0,
    )]
