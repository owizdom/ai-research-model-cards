#!/usr/bin/env python3
"""
One-time backfill: run locally, populate Railway DB.
Computes embeddings (local, free) + taxonomy mapping + eval extraction.

By default extracts with Claude Sonnet 4.6 via the local `claude` CLI subprocess
(authenticated via CLAUDE_CODE_OAUTH_TOKEN against the user's Max subscription).
Falls back to Groq/Gemini via litellm when EXTRACTION_MODEL is set to a non-Claude
provider string.

ALL credentials must come from env vars. Required:
  RAILWAY_DB_URL or DATABASE_URL
                                Postgres connection string. Use RAILWAY_DB_URL when
                                running locally pointing at the Railway public proxy;
                                DATABASE_URL is auto-set inside the worker container.
  CLAUDE_CODE_OAUTH_TOKEN       Long-lived OAuth token from `claude setup-token`
                                (only required when EXTRACTION_MODEL is a Claude model)

Optional:
  EXTRACTION_MODEL              Default "sonnet". Set to "groq/llama-3.3-70b-versatile"
                                or "gemini/gemini-2.0-flash" to use the litellm fallback.
  EXTRACT_WORKERS               Default 3. Concurrent extraction worker count.
  GROQ_API_KEY / GEMINI_API_KEY Required if EXTRACTION_MODEL is non-Claude.

Usage:
  docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.dev.yml \\
    exec worker python /app/scripts/backfill_railway.py
"""
import asyncio
import json
import os
import sys
import time
import traceback

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

CLAUDE_PREFIXES = ("claude", "sonnet", "opus", "haiku", "anthropic/")


def _is_claude_model_name(model: str) -> bool:
    m = model.lower()
    return any(m.startswith(p) for p in CLAUDE_PREFIXES)


# ── Required env vars ─────────────────────────────────────────────────────────
DB_URL = os.environ.get("RAILWAY_DB_URL") or os.environ.get("DATABASE_URL")
if not DB_URL:
    sys.exit(
        "ERROR: set RAILWAY_DB_URL (for local runs against Railway public proxy) "
        "or DATABASE_URL (auto-set inside the worker container)."
    )

EXTRACTION_MODEL = os.environ.setdefault("EXTRACTION_MODEL", "sonnet")

if _is_claude_model_name(EXTRACTION_MODEL):
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        sys.exit(
            f"ERROR: EXTRACTION_MODEL={EXTRACTION_MODEL!r} is Claude but "
            "CLAUDE_CODE_OAUTH_TOKEN is not set. Mint one with `claude setup-token`."
        )
else:
    if not os.environ.get("GROQ_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        sys.exit(
            f"ERROR: EXTRACTION_MODEL={EXTRACTION_MODEL!r} is non-Claude but "
            "neither GROQ_API_KEY nor GEMINI_API_KEY is set."
        )

sys.path.insert(0, "/app")

engine = create_async_engine(DB_URL, echo=False, poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── PHASE 1: Embeddings (100% local, $0) ──────────────────────────────────────

async def backfill_embeddings():
    print("\n=== PHASE 1: Embeddings (local, free) ===")
    from src.embedder.model import embed_one, embed

    async with SessionLocal() as db:
        # Get versions without embeddings
        q = text("SELECT id FROM document_versions WHERE embedding IS NULL ORDER BY id")
        result = await db.execute(q)
        version_ids = [r.id for r in result.fetchall()]

    if not version_ids:
        print("All versions already have embeddings.")
        return

    print(f"Computing embeddings for {len(version_ids)} versions...")

    from packages.db.models import DocumentVersion

    for i, vid in enumerate(version_ids):
        async with SessionLocal() as db:
            version = await db.get(DocumentVersion, vid)
            if not version or not version.content_md:
                continue
            vec = embed_one(version.content_md[:8000])
            version.embedding = vec
            db.add(version)
            await db.commit()
        print(f"  [{i+1}/{len(version_ids)}] v{vid} embedded ({len(vec)} dims)")

    print(f"Done: {len(version_ids)} embeddings computed.")


# ── PHASE 2: Taxonomy mapping (100% local, $0) ────────────────────────────────

async def backfill_taxonomy():
    print("\n=== PHASE 2: Taxonomy Coverage Mapping (local, free) ===")
    from src.embedder.model import embed
    from packages.db.models import DocumentVersion, TaxonomyCategory, DocumentTaxonomyMapping

    async with SessionLocal() as db:
        # Get taxonomy categories
        cats = (await db.execute(select(TaxonomyCategory))).scalars().all()
        if not cats:
            print("No taxonomy categories in DB.")
            return

        cat_texts = [f"{c.name}: {c.description}" for c in cats]
        cat_vecs = embed(cat_texts)

        # Get versions with embeddings but no taxonomy mappings
        q = text("""
            SELECT dv.id FROM document_versions dv
            WHERE dv.embedding IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM document_taxonomy_mappings dtm
                WHERE dtm.document_version_id = dv.id
            )
            ORDER BY dv.id
        """)
        result = await db.execute(q)
        version_ids = [r.id for r in result.fetchall()]

    if not version_ids:
        print("All embedded versions already have taxonomy mappings.")
        return

    print(f"Mapping {len(version_ids)} versions to {len(cats)} categories...")

    for i, vid in enumerate(version_ids):
        async with SessionLocal() as db:
            version = await db.get(DocumentVersion, vid)
            if not version or version.embedding is None:
                continue

            doc_arr = np.array(version.embedding)
            mapped = 0
            for cat, cat_vec in zip(cats, cat_vecs):
                sim = float(np.dot(doc_arr, np.array(cat_vec)))
                if sim < 0.25:
                    continue
                existing = await db.execute(
                    select(DocumentTaxonomyMapping).where(
                        DocumentTaxonomyMapping.document_version_id == vid,
                        DocumentTaxonomyMapping.taxonomy_category_id == cat.id,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                db.add(DocumentTaxonomyMapping(
                    document_version_id=vid,
                    taxonomy_category_id=cat.id,
                    similarity_score=sim,
                    is_covered=True,
                ))
                mapped += 1
            await db.commit()
        print(f"  [{i+1}/{len(version_ids)}] v{vid} → {mapped} categories")

    print("Done: taxonomy mapping complete.")


# ── PHASE 3: Eval extraction (parallel) ───────────────────────────────────────

async def backfill_extraction():
    print(f"\n=== PHASE 3: Eval Extraction ({EXTRACTION_MODEL}) ===")
    from src.extractor.eval_extractor import extract_evals_from_version

    async with SessionLocal() as db:
        q = text("""
            SELECT dv.id, d.title FROM document_versions dv
            JOIN documents d ON dv.document_id = d.id
            WHERE d.doc_type = 'model_card'
            AND NOT EXISTS (
                SELECT 1 FROM extraction_runs er
                WHERE er.document_version_id = dv.id AND er.status = 'completed'
            )
            ORDER BY dv.id
        """)
        result = await db.execute(q)
        rows = result.fetchall()

    if not rows:
        print("All model cards already extracted.")
        return

    concurrency = int(os.environ.get("EXTRACT_WORKERS", "3"))
    print(f"Extracting {len(rows)} cards with concurrency={concurrency}...")

    sem = asyncio.Semaphore(concurrency)
    counter = {"done": 0, "failed": 0, "total_evals": 0}

    async def one(row):
        async with sem:
            try:
                count = await extract_evals_from_version(row.id, SessionLocal)
            except Exception as e:
                counter["failed"] += 1
                print(f"  v{row.id} ({row.title[:40]}): FAILED — {e}", flush=True)
                return
            counter["done"] += 1
            counter["total_evals"] += count
            print(
                f"  [{counter['done']}/{len(rows)}] v{row.id} "
                f"({row.title[:40]}): {count} evals",
                flush=True,
            )

    started = time.time()
    await asyncio.gather(*(one(r) for r in rows))
    elapsed = time.time() - started
    print(
        f"\nDone: {counter['total_evals']} evals from "
        f"{counter['done']}/{len(rows)} cards "
        f"({counter['failed']} failed) in {elapsed:.1f}s"
    )


# ── MAIN ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("BACKFILL RAILWAY DB — Local compute, $0 cost")
    print(f"Target DB: {DB_URL[:50]}...")
    print("=" * 60)

    # Phase 1: Embeddings (free, local)
    await backfill_embeddings()

    # Phase 2: Taxonomy mapping (free, local)
    await backfill_taxonomy()

    # Phase 3: Eval extraction (alternating LLM providers)
    await backfill_extraction()

    await engine.dispose()
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
