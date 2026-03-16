from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.core.deps import get_db
from src.schemas.document import DocumentSummary, DocumentDetail, DocumentVersionDetail, DiffResult
from packages.db.models import Document, DocumentVersion, Lab, DocumentTaxonomyMapping

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


@router.get("/{document_id}/versions/{version_id}", response_model=DocumentVersionDetail)
async def get_version(document_id: int, version_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DocumentVersion)
        .options(
            selectinload(DocumentVersion.taxonomy_mappings)
            .selectinload(DocumentTaxonomyMapping.category)
        )
        .where(DocumentVersion.id == version_id, DocumentVersion.document_id == document_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "Version not found")
    return version


@router.get("/{document_id}/diff", response_model=DiffResult)
async def diff_versions(
    document_id: int,
    version_a: int = Query(...),
    version_b: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    import difflib
    ra = await db.execute(select(DocumentVersion).where(DocumentVersion.id == version_a, DocumentVersion.document_id == document_id))
    rb = await db.execute(select(DocumentVersion).where(DocumentVersion.id == version_b, DocumentVersion.document_id == document_id))
    va, vb = ra.scalar_one_or_none(), rb.scalar_one_or_none()
    if not va or not vb:
        raise HTTPException(404, "Version not found")
    old_lines = va.content_md.splitlines(keepends=True)
    new_lines = vb.content_md.splitlines(keepends=True)
    unified = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    lines_added = sum(1 for l in unified if l.startswith("+") and not l.startswith("+++"))
    lines_removed = sum(1 for l in unified if l.startswith("-") and not l.startswith("---"))
    old_words, new_words = set(va.content_md.split()), set(vb.content_md.split())
    total = max(len(old_lines), 1)
    return DiffResult(
        version_a_id=version_a, version_b_id=version_b,
        unified_diff="\n".join(unified),
        lines_added=lines_added, lines_removed=lines_removed,
        words_added=len(new_words - old_words), words_removed=len(old_words - new_words),
        change_percent=round((lines_added + lines_removed) / (2 * total) * 100, 2),
    )
