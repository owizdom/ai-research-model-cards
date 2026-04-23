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


_BULLET_RE = re.compile(r"^[•●○■□▪▸►]\s*")
_NUMBERED_LIST_RE = re.compile(r"^(\d+[\.\)]|[a-z][\.\)])\s")
_SHORT_HEADING_RE = re.compile(r"^[A-Z][A-Za-z0-9 ,/\-&()']{2,60}$")
_DATE_LINE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}$"
)
# Section heading like "1 Introduction", "2.1 Pretraining data", "1.2.3 Foo bar"
# May have a trailing page number: "2 Capabilities 17" → strip the " 17".
_SECTION_NUM_RE = re.compile(
    r"^(\d+(?:\.\d+){0,3})\s+([A-Z][A-Za-z][^\n]{0,80}?)(?:\s+\d+)?$"
)
# Common model-card top-level section names — always promote to H2
_KNOWN_SECTION_HEADINGS = {
    "abstract", "introduction", "contents", "changelog", "executive summary",
    "overview", "conclusion", "conclusions", "limitations", "references",
    "acknowledgments", "acknowledgements", "appendix", "bibliography",
    "methodology", "methods", "results", "discussion", "background",
    "related work", "capabilities", "evaluations", "safety", "deployment",
    "risks", "mitigations", "red teaming", "red-teaming",
}


def _clean_content(md: str) -> str:
    """Normalize content for display across three common input styles:

    1. Word-per-line PDF dumps (Opus 4.5 etc.) — avg line length ~5-10 chars,
       blank line between every word. Rejoin as flowing prose.
    2. Visual-line-per-item PDF dumps (Opus 4.6, GPT-5 etc.) — each visual
       line from the PDF is on its own line, ~30-80 chars, bullets preserved
       but no native paragraph structure. Join continuation lines; keep
       bullets and short headings as their own paragraphs.
    3. Native markdown / wrapped prose (Gemini reports etc.) — already has
       blank-line-separated paragraphs. Preserve structure, collapse
       intra-paragraph whitespace.
    """
    if not md:
        return ""
    md = _NOISE_CHARS_RE.sub("", md)
    raw_lines = [l.strip() for l in md.split("\n")]
    substantive = [l for l in raw_lines if l]
    if not substantive:
        return ""

    mean_line_len = sum(len(l) for l in substantive) / len(substantive)

    # ── Case 1: word-per-line broken. Very short mean line length.
    if mean_line_len < 15:
        blob = _MULTI_WHITESPACE_RE.sub(" ", " ".join(substantive)).strip()
        # Split on bullet markers so changelog-style lists keep structure.
        blob = re.sub(r"\s*[•●○■□▪▸]\s+", "\n\n- ", blob)
        # Insert section breaks before known top-level headings.
        for section in _KNOWN_SECTION_HEADINGS:
            # whole-word match, bounded to avoid mid-word collisions
            blob = re.sub(
                r"(?<![A-Za-z])" + re.escape(section.title()) + r"(?![A-Za-z])",
                f"\n\n## {section.title()}\n\n",
                blob,
                count=1,
                flags=re.IGNORECASE,
            )
        # Split into paragraphs.
        paragraphs: list[str] = []
        for block in blob.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            if block.startswith(("- ", "## ", "### ")):
                paragraphs.append(block)
                continue
            sentences = re.split(r"(?<=[\.!?])\s+(?=[A-Z0-9])", block)
            buf: list[str] = []
            chars = 0
            for s in sentences:
                buf.append(s)
                chars += len(s)
                if chars > 500 and s.endswith((".", "!", "?")):
                    paragraphs.append(" ".join(buf))
                    buf = []
                    chars = 0
            if buf:
                paragraphs.append(" ".join(buf))
        return "\n\n".join(paragraphs).strip()

    # ── Cases 2 & 3: line structure is meaningful. Walk lines, assembling
    # paragraphs by joining continuation lines and breaking on:
    #   • a blank line
    #   • a markdown header
    #   • a bullet/numbered list marker (starts a new item)
    #   • a short heading-like line (capitalized, no terminal punctuation)
    #   • a line ending in . ! ? (closes a sentence → start new block if next
    #     line starts with a capital or a bullet)

    paragraphs: list[str] = []
    buf: list[str] = []
    buf_is_bullet = False

    def flush():
        if buf:
            joined = _MULTI_WHITESPACE_RE.sub(" ", " ".join(buf)).strip()
            if joined:
                paragraphs.append(("- " if buf_is_bullet else "") + joined)
            buf.clear()

    for line in raw_lines:
        if not line:
            flush()
            buf_is_bullet = False
            continue

        if _MD_HEADER_RE.match(line):
            flush()
            buf_is_bullet = False
            paragraphs.append(line)
            continue

        # Skip table-of-contents entries (contain dot leader ". . ." or
        # end with a page number after lots of dots). These look identical
        # to section headings but appear in a TOC block we don't want to
        # render as real headers.
        if ". . ." in line or re.search(r"\.{3,}\s*\d+\s*$", line):
            # Keep as regular paragraph continuation; strip the noise.
            cleaned_toc = re.sub(r"\.{2,}", " ", line)
            buf.append(cleaned_toc)
            continue

        # Numbered section heading like "1 Introduction", "2.1 Pretraining"
        # → promote to markdown header (level = dots + 2, capped at 5).
        sec_match = _SECTION_NUM_RE.match(line)
        if sec_match and len(line) < 90:
            num, title = sec_match.group(1), sec_match.group(2).strip()
            # Reject if it's actually a figure label or axis caption like
            # "100 Depth (%)" — the first number should be a reasonable
            # section index (≤ 20) and the title should be substantive.
            first_num = int(num.split(".")[0]) if num.split(".")[0].isdigit() else 0
            if (
                title
                and title[0].isupper()
                and first_num <= 20
                and len(title) >= 4
            ):
                level = min(2 + num.count("."), 5)
                flush()
                buf_is_bullet = False
                paragraphs.append(f"{'#' * level} {num} {title}")
                continue

        # Known top-level section label standing alone ("Abstract", "Contents",
        # "Introduction") → promote to H2.
        lower_line = line.lower().strip()
        if lower_line in _KNOWN_SECTION_HEADINGS and len(line) < 40:
            flush()
            buf_is_bullet = False
            paragraphs.append(f"## {line}")
            continue

        # Bullet or numbered list item → new paragraph
        bullet_match = _BULLET_RE.match(line)
        numbered_match = _NUMBERED_LIST_RE.match(line)
        if bullet_match or numbered_match:
            flush()
            buf_is_bullet = bool(bullet_match)
            cleaned_line = _BULLET_RE.sub("", line).strip() if bullet_match else line
            buf.append(cleaned_line)
            continue

        # Short heading-like line → emit as own paragraph when it's
        # probably metadata rather than a prose continuation. Heading
        # pattern (all caps / dates / short capitalized label) AND the
        # previous line is either empty, another short heading, or ended
        # with terminal punctuation (so we're not cutting a sentence).
        is_heading_like = (
            len(line) < 60
            and (_SHORT_HEADING_RE.match(line) or _DATE_LINE_RE.match(line))
            and not line.endswith((".", ","))
        )
        if is_heading_like:
            prev = buf[-1].rstrip() if buf else ""
            prev_is_short = len(prev) < 60
            prev_closed = prev.endswith((".", "!", "?", ":"))
            if not prev or prev_is_short or prev_closed:
                flush()
                buf_is_bullet = False
                paragraphs.append(line)
                continue

        # Otherwise, append as a continuation of current paragraph.
        buf.append(line)

    flush()
    out = "\n\n".join(paragraphs)
    out = _MULTI_NEWLINE_RE.sub("\n\n", out).strip()

    # Post-pass: strip the table-of-contents block. When we see "## Contents"
    # followed by a dense cluster of short headings / numbered entries, most
    # of those entries will re-appear later in the body (duplicated). Replace
    # the TOC cluster with a single placeholder so the real body headings
    # stay authoritative.
    out = _strip_toc_block(out)
    return out


def _strip_toc_block(md: str) -> str:
    """If we detect a TOC block after '## Contents', walk past the cluster of
    short heading-only paragraphs and replace the TOC with a small stub.
    Body headings then remain authoritative.
    """
    m = re.search(r"^## Contents\s*$", md, re.MULTILINE)
    if not m:
        return md

    blocks = md[m.end():].split("\n\n")
    toc_end_offset = 0
    for i, b in enumerate(blocks):
        b_stripped = b.strip()
        if not b_stripped:
            toc_end_offset += len(b) + 2
            continue
        is_heading = b_stripped.startswith("#")
        has_dot_leader = bool(re.search(r"\.{2,}", b_stripped))
        # TOC entry fingerprint: either a heading, a dot-leader line, or a
        # short/medium sequence of "N.N Title ... N" patterns.
        looks_like_toc_section_heading = bool(
            re.match(r"^(?:## |### |#### )?\d+(?:\.\d+)*\s+[A-Z]", b_stripped)
        )
        if is_heading or has_dot_leader or (
            len(b_stripped) < 300 and looks_like_toc_section_heading
        ):
            toc_end_offset += len(b) + 2
            continue
        # Hit real prose → stop.
        break

    if toc_end_offset == 0:
        return md

    toc_absolute_end = m.end() + toc_end_offset
    return (
        md[: m.end()]
        + "\n\n_(Table of contents — see sections below.)_\n\n"
        + md[toc_absolute_end:].lstrip()
    )


# --- Phase 2: Gist + heatstrip heuristics (no external API calls) ---

_SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "safety": (
        "safety", "harm", "toxic", "bias", "refusal", "violative", "jailbreak",
        "misuse", "red team", "red-team", "redteam", "cbrn", "bio", "cyber",
        "weapon", "disallowed", "alignment", "scheming", "deception",
        "sycophancy", "sandbag", "guard",
    ),
    "evals": (
        "benchmark", "evaluation", "eval ", "mmlu", "humaneval", "gpqa",
        "accuracy", "pass rate", "score", "test set", "capability test",
    ),
    "risks": (
        "risk", "threat", "threshold", "uplift", "catastrophic", "concern",
        "dangerous capability", "autonomy", "self-exfiltrat",
    ),
    "mitigations": (
        "mitigation", "we decided not to", "crossed our threshold", "refused to",
        "did not release", "withheld", "guard", "filter", "classifier",
        "policy", "deployment restriction",
    ),
    "deployment": (
        "deploy", "available", "release", "api", "product", "rollout", "rollout",
        "launch", "shipping",
    ),
}

_REFUSAL_PATTERNS = re.compile(
    r"(we (?:decided|elected) not to|we have not|we did not (?:release|deploy)|"
    r"not (?:release|deploy|make available)|crossed our (?:threshold|trigger)|"
    r"elicited (?:harmful|dangerous|unsafe)|would not release|withheld|"
    r"refused to (?:release|deploy))[^.]{0,200}\.",
    re.IGNORECASE,
)
_CAPABILITY_PATTERNS = re.compile(
    r"(we (?:are releasing|release|have trained|trained|introduce|present) "
    r"[^.]{10,200})\.",
    re.IGNORECASE,
)
_DEPLOYMENT_PATTERNS = re.compile(
    r"(available (?:via|on|through)|deployed (?:to|via|through)|"
    r"accessible (?:via|through)|rolling out|launching) [^.]{5,150}\.",
    re.IGNORECASE,
)


def _build_gist(md: str, title: str) -> dict:
    """Extract Gist fields heuristically. Each field carries a verbatim quote
    (or None) and a char offset so the UI can anchor back to the prose."""
    def first_match(pattern: re.Pattern) -> tuple[str | None, int | None]:
        m = pattern.search(md)
        if not m:
            return None, None
        return m.group(0).strip(), m.start()

    # Overview = first 1-3 sentences of the first substantial paragraph
    first_para = next(
        (p for p in md.split("\n\n") if len(p) > 80 and not _MD_HEADER_RE.match(p)),
        "",
    )
    overview_sentences = re.split(r"(?<=[\.!?])\s+(?=[A-Z])", first_para)[:3]
    overview = " ".join(overview_sentences)[:500]

    refusal, refusal_idx = first_match(_REFUSAL_PATTERNS)
    capability, capability_idx = first_match(_CAPABILITY_PATTERNS)
    deployment, deployment_idx = first_match(_DEPLOYMENT_PATTERNS)

    return {
        "overview": overview,
        "capability_claim": capability,
        "capability_offset": capability_idx,
        "sharpest_risk": refusal,
        "sharpest_risk_offset": refusal_idx,
        "deployment_scope": deployment,
        "deployment_offset": deployment_idx,
        "title": title,
    }


def _build_heatstrip(md: str) -> list[dict]:
    """Segment the document into ~20 equal chunks; score each chunk's
    keyword density per category. Returns segments with their dominant
    category + counts, suitable for a horizontal heatstrip."""
    if not md:
        return []
    N_SEGMENTS = 20
    seg_len = max(1, len(md) // N_SEGMENTS)
    segments = []
    for i in range(N_SEGMENTS):
        start = i * seg_len
        end = start + seg_len if i < N_SEGMENTS - 1 else len(md)
        chunk = md[start:end].lower()
        scores = {}
        for cat, keywords in _SECTION_KEYWORDS.items():
            scores[cat] = sum(chunk.count(k) for k in keywords)
        total = sum(scores.values())
        dominant = max(scores, key=scores.get) if total > 0 else "other"
        segments.append({
            "index": i,
            "start": start,
            "end": end,
            "dominant": dominant,
            "scores": scores,
            "intensity": total,
        })
    return segments


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
        gist=_build_gist(cleaned, doc.title),
        heatstrip=_build_heatstrip(cleaned),
    )


