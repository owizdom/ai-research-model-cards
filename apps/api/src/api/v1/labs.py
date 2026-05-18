from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from src.core.deps import get_db
from src.schemas.document import LabRead
from src.schemas.labs import LabCoveragePoint, LabDetail, LabDocumentItem, LabSummary
from packages.db.models import Lab, Document

router = APIRouter()


@router.get("", response_model=list[LabSummary])
async def list_labs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Lab, func.count(Document.id).label("document_count"))
        .outerjoin(Document, Document.lab_id == Lab.id)
        .group_by(Lab.id)
        .order_by(Lab.name)
    )
    return [
        LabSummary(**LabRead.model_validate(lab).model_dump(), document_count=count)
        for lab, count in result.all()
    ]


@router.get("/{lab_slug}", response_model=LabDetail)
async def get_lab(lab_slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lab).where(Lab.slug == lab_slug))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(404, "Lab not found")
    docs = await db.execute(
        select(Document).where(Document.lab_id == lab.id).order_by(Document.doc_type)
    )
    documents = docs.scalars().all()
    return LabDetail(
        **LabRead.model_validate(lab).model_dump(),
        documents=[
            LabDocumentItem(id=d.id, slug=d.slug, title=d.title, doc_type=d.doc_type)
            for d in documents
        ],
    )


@router.get("/{lab_slug}/coverage", response_model=list[dict])
async def get_lab_coverage(lab_slug: str, db: AsyncSession = Depends(get_db)):
    sql = text("""
        SELECT tc.slug, tc.name,
               COALESCE(MAX(dtm.similarity_score), 0) as max_score,
               MAX(dtm.coverage_depth) as depth
        FROM taxonomy_categories tc
        LEFT JOIN document_taxonomy_mappings dtm ON dtm.taxonomy_category_id = tc.id
        LEFT JOIN document_versions dv ON dv.id = dtm.document_version_id
        LEFT JOIN documents d ON d.id = dv.document_id
        LEFT JOIN labs l ON l.id = d.lab_id AND l.slug = :lab_slug
        WHERE tc.parent_id IS NULL
        GROUP BY tc.id, tc.slug, tc.name
        ORDER BY max_score DESC
    """)
    result = await db.execute(sql, {"lab_slug": lab_slug})
    return [
        {"slug": r.slug, "name": r.name, "score": round(float(r.max_score), 4), "coverage_depth": r.depth or "none"}
        for r in result.fetchall()
    ]
