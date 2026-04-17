from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from src.core.deps import get_db
from src.schemas.document import DocumentSummary, DocumentDetail, WordCountTimelinePoint
from packages.db.models import Document, DocumentVersion, Lab

router = APIRouter()


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    lab_slug: Optional[str] = None,
    doc_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Document).options(selectinload(Document.lab)).order_by(Document.updated_at.desc())
    if lab_slug:
        q = q.join(Lab).where(Lab.slug == lab_slug)
    if doc_type:
        q = q.where(Document.doc_type == doc_type)
    if search:
        q = q.where(Document.title.ilike(f"%{search}%"))
    result = await db.execute(q.limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/word-count-timeline", response_model=list[WordCountTimelinePoint])
async def word_count_timeline(db: AsyncSession = Depends(get_db)):
    """Word count per model card version over time — for trend charts."""
    q = text("""
        SELECT l.slug AS lab_slug, l.name AS lab_name,
               d.slug AS document_slug, d.title AS document_title,
               dv.version_date::text AS version_date, dv.word_count
        FROM document_versions dv
        JOIN documents d ON dv.document_id = d.id
        JOIN labs l ON d.lab_id = l.id
        WHERE d.doc_type = 'model_card'
          AND dv.word_count IS NOT NULL AND dv.word_count > 0
        ORDER BY dv.version_date ASC, l.slug, d.slug
    """)
    result = await db.execute(q)
    return [
        WordCountTimelinePoint(
            lab_slug=r.lab_slug, lab_name=r.lab_name,
            document_slug=r.document_slug, document_title=r.document_title,
            version_date=r.version_date, word_count=r.word_count,
        )
        for r in result.fetchall()
    ]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.lab), selectinload(Document.versions))
        .where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


