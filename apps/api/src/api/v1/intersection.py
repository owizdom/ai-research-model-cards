from typing import Optional
from itertools import combinations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import bindparam, text
from packages.pipeline_config import COVERAGE_ANALYSIS_THRESHOLD
from src.core.deps import get_db
from src.schemas.analysis import IntersectionResult

router = APIRouter()


@router.get("", response_model=IntersectionResult)
async def get_intersection(
    lab_slugs: Optional[str] = Query(None, description="Comma-separated lab slugs"),
    doc_types: Optional[str] = Query(None),
    threshold: float = Query(COVERAGE_ANALYSIS_THRESHOLD, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    lab_list = [s.strip() for s in lab_slugs.split(",") if s.strip()] if lab_slugs else None
    if not lab_list:
        r = await db.execute(text("SELECT DISTINCT slug FROM labs ORDER BY slug"))
        lab_list = [row[0] for row in r.fetchall()]
    if not lab_list:
        return IntersectionResult(matrix={}, covered_by_all=[], covered_by_none=[], unique_to={}, intersection_sets=[], lab_slugs=[], category_names={})

    doc_type_list = [s.strip() for s in doc_types.split(",") if s.strip()] if doc_types else None

    # Score columns are structural — one per lab — so we can't push them through
    # a single expanding bind. Bind each lab value by index instead; the only
    # thing in the SQL string is the bind-param name and the integer alias.
    # Lab IN-list and doc_type IN-list both go through expanding bindparams.
    score_col_parts: list[str] = []
    binds: dict = {}
    for i, lab in enumerate(lab_list):
        binds[f"lab_{i}"] = lab
        score_col_parts.append(
            f"MAX(dtm.similarity_score) FILTER (WHERE l.slug = :lab_{i}) AS s_{i}"
        )
    score_cols = ", ".join(score_col_parts)

    doc_filter = "AND d.doc_type IN :doc_types" if doc_type_list else ""

    sql = text(f"""
        SELECT tc.slug AS cat_slug, tc.name AS cat_name, {score_cols}
        FROM taxonomy_categories tc
        LEFT JOIN document_taxonomy_mappings dtm ON dtm.taxonomy_category_id = tc.id
        LEFT JOIN document_versions dv ON dv.id = dtm.document_version_id
        LEFT JOIN documents d ON d.id = dv.document_id {doc_filter}
        LEFT JOIN labs l ON l.id = d.lab_id AND l.slug IN :lab_slugs
        WHERE tc.parent_id IS NULL
        GROUP BY tc.id, tc.slug, tc.name
        ORDER BY tc.name
    """)
    bind_decls = [bindparam("lab_slugs", expanding=True)]
    if doc_type_list:
        bind_decls.append(bindparam("doc_types", expanding=True))
    sql = sql.bindparams(*bind_decls)

    binds["lab_slugs"] = lab_list
    if doc_type_list:
        binds["doc_types"] = doc_type_list

    result = await db.execute(sql, binds)
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
