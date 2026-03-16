"""Consume embed_jobs queue, compute embeddings + taxonomy scores."""
import asyncio
import json
import os
import traceback

import redis
import numpy as np
from sqlalchemy import select

from packages.db.session import AsyncSessionLocal
from packages.db.models import DocumentVersion, TaxonomyCategory, DocumentTaxonomyMapping
from .model import embed_one, embed


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


async def _load_taxonomy_embeddings(db) -> list[tuple[int, list[float]]]:
    result = await db.execute(select(TaxonomyCategory))
    cats = result.scalars().all()
    if not cats:
        print("[worker] WARNING: no taxonomy categories found — run seed first")
        return []
    texts = [f"{c.name}: {c.description}" for c in cats]
    vecs = embed(texts)
    return [(c.id, v) for c, v in zip(cats, vecs)]


async def process_embed_job(version_id: int) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            print(f"[worker] version {version_id} not found, skipping")
            return
        if not version.content_md:
            print(f"[worker] version {version_id} has no content, skipping")
            return

        # Embed document (sync, run in thread to not block event loop)
        doc_vec = await asyncio.to_thread(embed_one, version.content_md[:8000])
        version.embedding = doc_vec
        db.add(version)
        await db.commit()
        print(f"[worker] embedded version {version_id} ({len(doc_vec)} dims)")

        # Score against taxonomy
        taxonomy_vecs = await asyncio.to_thread(
            lambda: None  # placeholder, actual work below
        )
        # Load taxonomy embeddings (involves sync embed call)
        tax_result = await db.execute(select(TaxonomyCategory))
        cats = tax_result.scalars().all()
        if not cats:
            return
        texts = [f"{c.name}: {c.description}" for c in cats]
        cat_vecs = await asyncio.to_thread(embed, texts)
        taxonomy_pairs = [(c.id, v) for c, v in zip(cats, cat_vecs)]

        doc_arr = np.array(doc_vec)
        mapped = 0
        for cat_id, cat_vec in taxonomy_pairs:
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
            mapped += 1
        await db.commit()
    print(f"[worker] version {version_id}: mapped to {mapped} taxonomy categories")


async def run_embed_loop() -> None:
    r = get_redis()
    print("[worker] embed loop started")
    while True:
        # Run blocking redis call in a thread so we don't block the event loop
        item = await asyncio.to_thread(r.blpop, "embed_jobs", 5)
        if item is None:
            continue
        try:
            payload = json.loads(item[1])
            await process_embed_job(payload["version_id"])
        except Exception as e:
            print(f"[worker] embed error: {e}")
            traceback.print_exc()
