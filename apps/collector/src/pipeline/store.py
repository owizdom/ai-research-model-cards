"""Persist collected documents to DB and enqueue embedding jobs."""
import json
import os
from datetime import date

import redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from packages.db.models import Lab, Document, DocumentVersion
from packages.db.session import AsyncSessionLocal
from ..collectors.base import CollectedDocument, HistoricalVersion
from ..collectors.registry import LAB_META


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


async def _upsert_lab(db, slug: str) -> Lab:
    meta = LAB_META.get(slug, {})
    stmt = pg_insert(Lab).values(
        slug=slug, name=meta.get("name", slug),
        website=meta.get("website"), color_hex=meta.get("color_hex"),
    ).on_conflict_do_update(index_elements=["slug"], set_={"name": meta.get("name", slug)}).returning(Lab)
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def _upsert_document(db, lab_id: int, doc: CollectedDocument) -> Document:
    stmt = pg_insert(Document).values(
        lab_id=lab_id, slug=doc.slug, title=doc.title,
        doc_type=doc.doc_type, source_url=doc.source_url,
    ).on_conflict_do_update(
        index_elements=["slug"],
        set_={"title": doc.title, "source_url": doc.source_url},
    ).returning(Document)
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def store_document(doc: CollectedDocument) -> bool:
    """Returns True if a new version was stored."""
    r = get_redis()
    async with AsyncSessionLocal() as db:
        lab = await _upsert_lab(db, doc.lab_slug)
        document = await _upsert_document(db, lab.id, doc)

        existing = await db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.content_hash == doc.content_hash,
            )
        )
        if existing.scalar_one_or_none():
            return False

        version = DocumentVersion(
            document_id=document.id, version_date=date.today(),
            content_md=doc.content_md.replace("\x00", ""), content_hash=doc.content_hash, word_count=doc.word_count,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        r.rpush("embed_jobs", json.dumps({"version_id": version.id}))
        return True


async def store_historical(document_id: int, h: HistoricalVersion) -> bool:
    r = get_redis()
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.content_hash == h.content_hash,
            )
        )
        if existing.scalar_one_or_none():
            return False
        from datetime import date as dt
        version = DocumentVersion(
            document_id=document_id,
            version_date=dt.fromisoformat(h.version_date),
            content_md=h.content_md.replace("\x00", ""), content_hash=h.content_hash,
            word_count=h.word_count, wayback_url=h.wayback_url,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        r.rpush("embed_jobs", json.dumps({"version_id": version.id}))
        return True
