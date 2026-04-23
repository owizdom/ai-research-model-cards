import re
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from src.core.deps import get_db
from src.schemas.document import (
    DocumentSummary, DocumentDetail, WordCountTimelinePoint,
    DocumentContent, DocumentOutlineItem,
)
from packages.db.models import Document, DocumentVersion, Lab

router = APIRouter()


# --- Content cleanup helpers ---

_MD_HEADER_RE = re.compile(r"^(#{1,6})\s+(.{1,200})$", re.MULTILINE)
_NOISE_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_MULTI_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def _clean_content(md: str) -> str:
    """Normalize PDF-extracted markdown for display.

    PDF→text extraction from these model cards commonly produces
    one-word-per-line output with blank lines between every word.
    Heuristic: if most non-empty lines are shorter than a sentence,
    treat the whole blob as flowing prose and re-paragraph it on
    sentence boundaries. Otherwise keep the native paragraph structure.
    """
    if not md:
        return ""
    md = _NOISE_CHARS_RE.sub("", md)
    lines = [l.strip() for l in md.split("\n")]
    substantive = [l for l in lines if l]
    if not substantive:
        return ""

    short_ratio = sum(1 for l in substantive if len(l) < 30) / len(substantive)
    if short_ratio > 0.6:
        # Broken PDF extraction — rejoin as flowing prose and chunk on sentences.
        blob = _MULTI_WHITESPACE_RE.sub(" ", " ".join(substantive)).strip()
        # Split on sentence enders; re-assemble 3-5 sentences per paragraph.
        sentences = re.split(r"(?<=[\.!?])\s+(?=[A-Z0-9•\-])", blob)
        paragraphs: list[str] = []
        buf: list[str] = []
        chars = 0
        for s in sentences:
            buf.append(s)
            chars += len(s)
            if chars > 600 and s.endswith((".", "!", "?")):
                paragraphs.append(" ".join(buf))
                buf = []
                chars = 0
        if buf:
            paragraphs.append(" ".join(buf))
        return "\n\n".join(paragraphs).strip()

    # Native prose — preserve paragraph breaks (blank-line-separated).
    paragraphs: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            joined = _MULTI_WHITESPACE_RE.sub(" ", " ".join(buf)).strip()
            if joined:
                paragraphs.append(joined)
            buf.clear()

    for line in lines:
        if _MD_HEADER_RE.match(line) or line.startswith(("- ", "* ", "> ")):
            flush()
            paragraphs.append(line)
        elif not line:
            flush()
        else:
            buf.append(line)
    flush()

    out = "\n\n".join(paragraphs)
    return _MULTI_NEWLINE_RE.sub("\n\n", out).strip()


def _extract_outline(md: str) -> list[DocumentOutlineItem]:
    """Extract H1-H6 headers as a flat list with anchor slugs."""
    items: list[DocumentOutlineItem] = []
    seen: set[str] = set()
    for i, m in enumerate(_MD_HEADER_RE.finditer(md)):
        level = len(m.group(1))
        title = m.group(2).strip()
        # Skip headers that are obviously garbage (non-ASCII printable density)
        printable_ratio = sum(1 for c in title if c.isascii() and c.isprintable()) / max(len(title), 1)
        if printable_ratio < 0.7:
            continue
        slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:64] or f"sec-{i}"
        slug = slug_base
        k = 2
        while slug in seen:
            slug = f"{slug_base}-{k}"
            k += 1
        seen.add(slug)
        items.append(DocumentOutlineItem(level=level, title=title, anchor=slug))
    return items


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


@router.get("/{document_id}/content", response_model=DocumentContent)
async def get_document_content(
    document_id: int,
    version_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return cleaned markdown body + extracted outline for the latest version
    (or a specific version when `version_id` is provided)."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    q = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_date.desc())
    )
    if version_id is not None:
        q = q.where(DocumentVersion.id == version_id)
    res = await db.execute(q.limit(1))
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "No version available")

    cleaned = _clean_content(version.content_md or "")
    outline = _extract_outline(cleaned)
    word_count = len(cleaned.split()) if cleaned else 0
    # Reading speed ~230 wpm for dense research prose
    read_minutes = max(1, round(word_count / 230)) if word_count else 0

    return DocumentContent(
        document_id=document_id,
        version_id=version.id,
        version_date=version.version_date,
        word_count=word_count,
        read_minutes=read_minutes,
        has_headers=len(outline) >= 3,
        outline=outline,
        content_md=cleaned,
    )


