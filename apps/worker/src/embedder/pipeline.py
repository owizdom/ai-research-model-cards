"""Consume embed_jobs queue, compute embeddings + taxonomy scores."""
import asyncio
import json
import os
import traceback

import numpy as np
from sqlalchemy import select

from packages.db.models import DocumentVersion, Document, TaxonomyCategory, DocumentTaxonomyMapping
from .model import embed_one, embed


async def process_embed_job(version_id: int, SessionLocal=None) -> None:
    if SessionLocal is None:
        from packages.db.session import AsyncSessionLocal
        SessionLocal = AsyncSessionLocal

    async with SessionLocal() as db:
        result = await db.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            print(f"[worker] version {version_id} not found, skipping", flush=True)
            return
        if not version.content_md:
            print(f"[worker] version {version_id} has no content, skipping", flush=True)
            return

        # Embed document
        doc_vec = embed_one(version.content_md[:8000])
        version.embedding = doc_vec
        db.add(version)
        await db.commit()
        print(f"[worker] embedded version {version_id} ({len(doc_vec)} dims)", flush=True)

        # Score against taxonomy
        tax_result = await db.execute(select(TaxonomyCategory))
        cats = tax_result.scalars().all()
        if not cats:
            return
        texts = [f"{c.name}: {c.description}" for c in cats]
        cat_vecs = embed(texts)
        taxonomy_pairs = [(c.id, v) for c, v in zip(cats, cat_vecs)]

        doc_arr = np.array(doc_vec)
        mapped = 0
        for cat_id, cat_vec in taxonomy_pairs:
            sim = float(np.dot(doc_arr, np.array(cat_vec)))
            if sim < 0.20:
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

        # Auto-enqueue extraction for model cards
        doc_result = await db.execute(
            select(Document).where(Document.id == version.document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if doc and doc.doc_type == "model_card":
            import redis as redis_lib
            r = redis_lib.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            r.rpush("extract_jobs", json.dumps({"version_id": version_id}))
            print(f"[worker] enqueued extract job for version {version_id}", flush=True)

    print(f"[worker] version {version_id}: mapped to {mapped} taxonomy categories", flush=True)
