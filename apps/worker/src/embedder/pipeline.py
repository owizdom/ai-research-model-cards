"""Consume embed_jobs queue, compute embeddings + taxonomy scores."""
import json
import os

import redis
from sqlalchemy import select

from packages.db.session import AsyncSessionLocal
from packages.db.models import DocumentVersion, TaxonomyCategory, DocumentTaxonomyMapping
from .model import embed_one, embed


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


async def _load_taxonomy_embeddings(db) -> list[tuple[int, list[float]]]:
    result = await db.execute(select(TaxonomyCategory))
    cats = result.scalars().all()
    texts = [f"{c.name}: {c.description}" for c in cats]
    vecs = embed(texts)
    return [(c.id, v) for c, v in zip(cats, vecs)]


async def process_embed_job(version_id: int) -> None:
    import numpy as np

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version or not version.content_md:
            return

        # Embed document
        doc_vec = embed_one(version.content_md[:8000])
        version.embedding = doc_vec
        db.add(version)
        await db.commit()

        # Score against taxonomy
        taxonomy_vecs = await _load_taxonomy_embeddings(db)
        doc_arr = np.array(doc_vec)
        for cat_id, cat_vec in taxonomy_vecs:
            sim = float(np.dot(doc_arr, np.array(cat_vec)))
            if sim < 0.25:
                continue
            existing = await db.execute(
                select(DocumentTaxonomyMapping).where(
                    DocumentTaxonomyMapping.document_version_id == version_id,
                    DocumentTaxonomyMapping.taxonomy_category_id == cat_id,
                )
            )
            if existing.scalar_one_or_none():
                continue
            db.add(DocumentTaxonomyMapping(
                document_version_id=version_id,
                taxonomy_category_id=cat_id,
                similarity_score=sim,
                is_covered=True,
            ))
        await db.commit()
    print(f"[worker] Embedded version {version_id}")


async def run_embed_loop() -> None:
    r = get_redis()
    print("[worker] embed loop started")
    while True:
        item = r.blpop("embed_jobs", timeout=5)
        if item is None:
            continue
        try:
            payload = json.loads(item[1])
            await process_embed_job(payload["version_id"])
        except Exception as e:
            print(f"[worker] embed error: {e}")
