#!/usr/bin/env python3
"""
Robust re-backfill v2: diagnose, re-collect, re-link, embed, taxonomy, extract.

Runs locally against the Railway DB (no Redis needed).

Usage:
  # Diagnose only (read-only):
  python scripts/backfill_v2.py --diagnose

  # Full backfill (all phases):
  python scripts/backfill_v2.py

  # Specific phase:
  python scripts/backfill_v2.py --phase collect
  python scripts/backfill_v2.py --phase link
  python scripts/backfill_v2.py --phase embed
  python scripts/backfill_v2.py --phase taxonomy
  python scripts/backfill_v2.py --phase extract
"""
import argparse
import asyncio
import os
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import yaml
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── DB connection ────────────────────────────────────────────────────────────
DB_URL = os.environ.get(
    "RAILWAY_DB_URL",
    "postgresql+asyncpg://postgres:fncvFEcSwvsWiAbWRtleToglaXEqaVzF@shuttle.proxy.rlwy.net:59396/railway",
)

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

engine = create_async_engine(DB_URL, echo=False, poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Load .env if keys not set ────────────────────────────────────────────────
if not GROQ_KEY or not GEMINI_KEY:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()
        GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

if GROQ_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_KEY
if GEMINI_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_KEY

# ── Registry & family data ───────────────────────────────────────────────────
from apps.collector.src.collectors.registry import SOURCES, LAB_META
from apps.collector.src.collectors.base import (
    CollectedDocument, html_to_markdown, pdf_to_text, arxiv_pdf_to_text,
    clean_markdown, compute_hash, word_count,
)

DATA_DIR = PROJECT_ROOT / "data"
FAMILIES_YAML = DATA_DIR / "model_families" / "families.yaml"


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 0: DIAGNOSE
# ═════════════════════════════════════════════════════════════════════════════

async def phase_0_diagnose():
    print("\n" + "=" * 70)
    print("PHASE 0: DIAGNOSE (read-only)")
    print("=" * 70)

    async with SessionLocal() as db:
        # Count documents by type
        q = text("SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type ORDER BY doc_type")
        result = await db.execute(q)
        rows = result.fetchall()
        print(f"\nDocuments in DB:")
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

        # Model cards detail
        q = text("""
            SELECT d.slug, d.title, l.slug AS lab_slug,
                   dv.id AS version_id, dv.word_count,
                   (dv.embedding IS NOT NULL) AS has_embedding,
                   (SELECT COUNT(*) FROM extraction_runs er
                    WHERE er.document_version_id = dv.id AND er.status = 'completed') AS completed_extractions,
                   (SELECT COUNT(*) FROM extraction_runs er
                    WHERE er.document_version_id = dv.id AND er.status = 'failed') AS failed_extractions,
                   (SELECT COUNT(*) FROM eval_results er
                    WHERE er.document_version_id = dv.id) AS eval_count,
                   (SELECT mg.slug FROM model_generations mg
                    WHERE mg.document_id = d.id LIMIT 1) AS generation_slug
            FROM documents d
            JOIN labs l ON d.lab_id = l.id
            LEFT JOIN LATERAL (
                SELECT * FROM document_versions dv2
                WHERE dv2.document_id = d.id
                ORDER BY dv2.version_date DESC LIMIT 1
            ) dv ON true
            WHERE d.doc_type = 'model_card'
            ORDER BY l.slug, d.slug
        """)
        result = await db.execute(q)
        cards = result.fetchall()

        print(f"\nModel cards ({len(cards)} total):")
        print(f"  {'Slug':<35} {'Lab':<10} {'Words':>6} {'Emb':>4} {'Ext':>4} {'Fail':>5} {'Evals':>6} {'Generation':<20}")
        print("  " + "-" * 100)
        total_evals = 0
        problems = []
        for c in cards:
            wc = c.word_count or 0
            emb = "Y" if c.has_embedding else "-"
            ext = c.completed_extractions or 0
            fail = c.failed_extractions or 0
            evals = c.eval_count or 0
            gen = c.generation_slug or "-"
            total_evals += evals
            print(f"  {c.slug:<35} {c.lab_slug:<10} {wc:>6} {emb:>4} {ext:>4} {fail:>5} {evals:>6} {gen:<20}")

            if wc < 500:
                problems.append(f"  LOW CONTENT: {c.slug} ({wc} words)")
            if ext == 0 and fail == 0:
                problems.append(f"  NO EXTRACTION: {c.slug}")
            if ext > 0 and evals == 0:
                problems.append(f"  EXTRACTED BUT 0 EVALS: {c.slug}")
            if gen == "-":
                problems.append(f"  NO GENERATION LINK: {c.slug}")

        print(f"\n  Total evals: {total_evals}")

        # Check which registry sources are NOT in the DB
        q = text("SELECT slug FROM documents")
        result = await db.execute(q)
        db_slugs = {r.slug for r in result.fetchall()}
        model_card_sources = [s for s in SOURCES if s.doc_type == "model_card"]
        missing = [s for s in model_card_sources if s.slug not in db_slugs]
        if missing:
            print(f"\nModel card sources NOT in DB ({len(missing)}):")
            for s in missing:
                print(f"  {s.slug} ({s.lab_slug}) — {s.url[:60]}...")

        # Check generations with NULL document_id
        q = text("""
            SELECT mg.slug, mg.name, mf.slug AS family_slug, mg.document_id
            FROM model_generations mg
            JOIN model_families mf ON mg.family_id = mf.id
            WHERE mg.document_id IS NULL
            ORDER BY mf.slug, mg.slug
        """)
        result = await db.execute(q)
        null_gens = result.fetchall()
        if null_gens:
            print(f"\nGenerations with NULL document_id ({len(null_gens)}):")
            for g in null_gens:
                print(f"  {g.family_slug}/{g.slug} ({g.name})")

        if problems:
            print(f"\nProblems found ({len(problems)}):")
            for p in problems:
                print(p)
        else:
            print("\nNo problems found!")


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1: RE-COLLECT bad/missing model cards
# ═════════════════════════════════════════════════════════════════════════════

async def phase_1_recollect():
    print("\n" + "=" * 70)
    print("PHASE 1: RE-COLLECT bad/missing model cards")
    print("=" * 70)

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from packages.db.models import Lab, Document, DocumentVersion

    async with SessionLocal() as db:
        # Find model cards with low word count or missing entirely
        q = text("SELECT slug FROM documents")
        result = await db.execute(q)
        db_slugs = {r.slug for r in result.fetchall()}

        # Get word counts for existing model cards (latest version)
        q = text("""
            SELECT d.slug, dv.word_count
            FROM documents d
            LEFT JOIN LATERAL (
                SELECT word_count FROM document_versions dv2
                WHERE dv2.document_id = d.id
                ORDER BY dv2.version_date DESC LIMIT 1
            ) dv ON true
            WHERE d.doc_type = 'model_card'
        """)
        result = await db.execute(q)
        word_counts = {r.slug: r.word_count or 0 for r in result.fetchall()}

    model_card_sources = [s for s in SOURCES if s.doc_type == "model_card"]
    to_recollect = []
    for s in model_card_sources:
        if s.slug not in db_slugs:
            to_recollect.append((s, "missing from DB"))
        elif "arxiv.org/abs/" in s.url:
            # ArXiv sources were fetched as HTML (abstract only) — re-fetch as PDF
            to_recollect.append((s, f"arxiv HTML→PDF re-fetch ({word_counts.get(s.slug, 0)} words → full paper)"))
        elif word_counts.get(s.slug, 0) < 500:
            to_recollect.append((s, f"low content ({word_counts.get(s.slug, 0)} words)"))

    if not to_recollect:
        print("All model cards have sufficient content.")
        return

    print(f"Re-collecting {len(to_recollect)} model cards:")
    for s, reason in to_recollect:
        print(f"  {s.slug}: {reason}")

    collected = 0
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        for source, reason in to_recollect:
            try:
                print(f"\n  Fetching {source.slug}...", end=" ", flush=True)

                if source.method == "html":
                    if "arxiv.org/abs/" in source.url:
                        content = await arxiv_pdf_to_text(source.url, client)
                    else:
                        content = await html_to_markdown(source.url, client, source.selector)
                elif source.method == "pdf":
                    content = await pdf_to_text(source.url, client)
                elif source.method == "raw":
                    resp = await client.get(source.url)
                    resp.raise_for_status()
                    content = resp.text
                else:
                    print("unknown method, skipping")
                    continue

                content = clean_markdown(content)
                if not content.strip():
                    print("empty content, skipping")
                    continue

                wc = word_count(content)
                h = compute_hash(content)
                print(f"{wc} words", flush=True)

                # Store to DB
                async with SessionLocal() as db:
                    # Upsert lab
                    meta = LAB_META.get(source.lab_slug, {})
                    stmt = pg_insert(Lab).values(
                        slug=source.lab_slug, name=meta.get("name", source.lab_slug),
                        website=meta.get("website"), color_hex=meta.get("color_hex"),
                    ).on_conflict_do_update(
                        index_elements=["slug"],
                        set_={"name": meta.get("name", source.lab_slug)},
                    ).returning(Lab)
                    lab = (await db.execute(stmt)).scalar_one()
                    await db.commit()

                    # Upsert document
                    stmt = pg_insert(Document).values(
                        lab_id=lab.id, slug=source.slug, title=source.title,
                        doc_type=source.doc_type, source_url=source.url,
                    ).on_conflict_do_update(
                        index_elements=["slug"],
                        set_={"title": source.title, "source_url": source.url},
                    ).returning(Document)
                    document = (await db.execute(stmt)).scalar_one()
                    await db.commit()

                    # Check for duplicate version by hash
                    existing = await db.execute(
                        select(DocumentVersion).where(
                            DocumentVersion.document_id == document.id,
                            DocumentVersion.content_hash == h,
                        )
                    )
                    if existing.scalar_one_or_none():
                        print(f"  (version already exists with same hash)")
                        continue

                    version = DocumentVersion(
                        document_id=document.id, version_date=date.today(),
                        content_md=content.replace("\x00", ""),
                        content_hash=h, word_count=wc,
                    )
                    db.add(version)
                    await db.commit()
                    collected += 1
                    print(f"  Stored new version (id={version.id})")

            except Exception as e:
                print(f"FAILED: {e}")
                continue

    print(f"\nPhase 1 complete: {collected} new versions stored.")


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2: LINK GENERATIONS
# ═════════════════════════════════════════════════════════════════════════════

async def phase_2_link_generations():
    print("\n" + "=" * 70)
    print("PHASE 2: LINK GENERATIONS (fix NULL document_id)")
    print("=" * 70)

    from packages.db.models import ModelFamily, ModelGeneration, Document, Lab

    families_data = yaml.safe_load(FAMILIES_YAML.read_text())
    fixed = 0

    async with SessionLocal() as db:
        for fam in families_data.get("families", []):
            for gen in fam.get("generations", []):
                doc_slug = gen.get("document_slug")
                if not doc_slug:
                    continue

                gen_result = await db.execute(
                    select(ModelGeneration).where(ModelGeneration.slug == gen["slug"])
                )
                existing_gen = gen_result.scalar_one_or_none()

                if not existing_gen:
                    # Generation doesn't exist — need to create family first
                    lab_result = await db.execute(select(Lab).where(Lab.slug == fam["lab_slug"]))
                    lab = lab_result.scalar_one_or_none()
                    if not lab:
                        continue

                    fam_result = await db.execute(
                        select(ModelFamily).where(ModelFamily.slug == fam["slug"])
                    )
                    family = fam_result.scalar_one_or_none()
                    if not family:
                        family = ModelFamily(slug=fam["slug"], name=fam["name"], lab_id=lab.id)
                        db.add(family)
                        await db.flush()
                        print(f"  Created family: {fam['slug']}")

                    doc_result = await db.execute(
                        select(Document).where(Document.slug == doc_slug)
                    )
                    doc = doc_result.scalar_one_or_none()

                    new_gen = ModelGeneration(
                        family_id=family.id,
                        slug=gen["slug"],
                        name=gen["name"],
                        version_label=gen.get("version_label"),
                        document_id=doc.id if doc else None,
                    )
                    db.add(new_gen)
                    fixed += 1
                    print(f"  Created generation: {gen['slug']} (doc={'linked' if doc else 'NULL'})")

                elif existing_gen.document_id is None:
                    doc_result = await db.execute(
                        select(Document).where(Document.slug == doc_slug)
                    )
                    doc = doc_result.scalar_one_or_none()
                    if doc:
                        existing_gen.document_id = doc.id
                        db.add(existing_gen)
                        fixed += 1
                        print(f"  Linked: {gen['slug']} → {doc_slug} (doc_id={doc.id})")

        await db.commit()

    print(f"\nPhase 2 complete: {fixed} generations created/linked.")


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3: EMBEDDINGS
# ═════════════════════════════════════════════════════════════════════════════

async def phase_3_embeddings():
    print("\n" + "=" * 70)
    print("PHASE 3: EMBEDDINGS (local, free)")
    print("=" * 70)

    from apps.worker.src.embedder.model import embed_one
    from packages.db.models import DocumentVersion

    async with SessionLocal() as db:
        q = text("SELECT id FROM document_versions WHERE embedding IS NULL ORDER BY id")
        result = await db.execute(q)
        version_ids = [r.id for r in result.fetchall()]

    if not version_ids:
        print("All versions already have embeddings.")
        return

    print(f"Computing embeddings for {len(version_ids)} versions...")

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

    print(f"Phase 3 complete: {len(version_ids)} embeddings computed.")


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 4: TAXONOMY MAPPING
# ═════════════════════════════════════════════════════════════════════════════

async def phase_4_taxonomy():
    print("\n" + "=" * 70)
    print("PHASE 4: TAXONOMY MAPPING (local, free)")
    print("=" * 70)

    from apps.worker.src.embedder.model import embed
    from packages.db.models import DocumentVersion, TaxonomyCategory, DocumentTaxonomyMapping

    async with SessionLocal() as db:
        cats = (await db.execute(select(TaxonomyCategory))).scalars().all()
        if not cats:
            print("No taxonomy categories in DB.")
            return

        cat_texts = [f"{c.name}: {c.description}" for c in cats]
        cat_vecs = embed(cat_texts)

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

    print(f"Phase 4 complete: {len(version_ids)} versions mapped.")


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 5: EVAL EXTRACTION
# ═════════════════════════════════════════════════════════════════════════════

async def phase_5_extract():
    print("\n" + "=" * 70)
    print("PHASE 5: EVAL EXTRACTION (alternating Groq/Gemini)")
    print("=" * 70)

    from apps.worker.src.extractor.eval_extractor import extract_evals_from_version
    import apps.worker.src.extractor.eval_extractor as ext

    providers = ["groq/llama-3.3-70b-versatile", "gemini/gemini-2.0-flash"]
    cooldowns = {p: 0.0 for p in providers}  # timestamp when provider is available again

    async with SessionLocal() as db:
        # Find model cards without completed extraction on their latest version
        q = text("""
            SELECT dv.id AS version_id, d.slug, d.title, dv.word_count
            FROM documents d
            JOIN LATERAL (
                SELECT * FROM document_versions dv2
                WHERE dv2.document_id = d.id
                ORDER BY dv2.version_date DESC LIMIT 1
            ) dv ON true
            WHERE d.doc_type = 'model_card'
            AND NOT EXISTS (
                SELECT 1 FROM extraction_runs er
                WHERE er.document_version_id = dv.id AND er.status = 'completed'
            )
            AND dv.word_count > 100
            ORDER BY d.slug
        """)
        result = await db.execute(q)
        rows = result.fetchall()

    if not rows:
        print("All model cards already have completed extractions.")
        return

    print(f"Extracting {len(rows)} model cards...")
    total_evals = 0

    for i, row in enumerate(rows):
        # Pick the provider with the earliest cooldown
        now = time.time()
        provider = min(providers, key=lambda p: cooldowns[p])
        wait = cooldowns[provider] - now
        if wait > 0:
            print(f"  (waiting {wait:.0f}s for {provider.split('/')[0]} cooldown)")
            time.sleep(wait)

        # Set the extraction model
        ext.EXTRACTION_MODEL = provider
        os.environ["EXTRACTION_MODEL"] = provider

        print(f"  [{i+1}/{len(rows)}] v{row.version_id}: {row.slug} ({row.word_count} words, {provider.split('/')[0]})...", end=" ", flush=True)

        try:
            count = await extract_evals_from_version(row.version_id, SessionLocal)
            total_evals += count
            print(f"{count} evals")

            # Standard delay between successful extractions
            if i < len(rows) - 1:
                time.sleep(15)

        except Exception as e:
            err = str(e).lower()
            if "rate" in err or "429" in err or "quota" in err:
                # Set cooldown for this provider (60s)
                cooldowns[provider] = time.time() + 60
                print(f"RATE LIMITED — cooling down {provider.split('/')[0]} for 60s")

                # Try the other provider immediately
                other = [p for p in providers if p != provider][0]
                other_wait = cooldowns[other] - time.time()
                if other_wait > 0:
                    print(f"  (waiting {other_wait:.0f}s for {other.split('/')[0]})")
                    time.sleep(other_wait)

                ext.EXTRACTION_MODEL = other
                os.environ["EXTRACTION_MODEL"] = other

                try:
                    count = await extract_evals_from_version(row.version_id, SessionLocal)
                    total_evals += count
                    print(f"  Retry with {other.split('/')[0]}: {count} evals")
                except Exception as e2:
                    cooldowns[other] = time.time() + 60
                    print(f"  Retry also failed: {e2}")
            else:
                print(f"FAILED: {e}")

            time.sleep(20)

    print(f"\nPhase 5 complete: {total_evals} evals extracted from {len(rows)} cards.")


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 6: SUMMARY
# ═════════════════════════════════════════════════════════════════════════════

async def phase_6_summary():
    print("\n" + "=" * 70)
    print("PHASE 6: SUMMARY")
    print("=" * 70)

    async with SessionLocal() as db:
        # Total evals
        q = text("SELECT COUNT(*) FROM eval_results")
        total = (await db.execute(q)).scalar()
        print(f"\nTotal eval results: {total}")

        # Per lab
        q = text("""
            SELECT l.slug, l.name, COUNT(er.id)
            FROM eval_results er
            JOIN document_versions dv ON er.document_version_id = dv.id
            JOIN documents d ON dv.document_id = d.id
            JOIN labs l ON d.lab_id = l.id
            GROUP BY l.slug, l.name
            ORDER BY COUNT(er.id) DESC
        """)
        result = await db.execute(q)
        rows = result.fetchall()
        print(f"\nEvals per lab:")
        for r in rows:
            print(f"  {r.name:<20} {r[2]:>4} evals")

        # Per family
        q = text("""
            SELECT mf.name, mg.name AS gen_name, COUNT(er.id)
            FROM eval_results er
            JOIN model_generations mg ON er.generation_id = mg.id
            JOIN model_families mf ON mg.family_id = mf.id
            GROUP BY mf.name, mg.name
            ORDER BY mf.name, mg.name
        """)
        result = await db.execute(q)
        rows = result.fetchall()
        if rows:
            print(f"\nEvals per family/generation:")
            for r in rows:
                print(f"  {r[0]:<10} {r[1]:<25} {r[2]:>4} evals")

        # Evals with NULL generation_id
        q = text("SELECT COUNT(*) FROM eval_results WHERE generation_id IS NULL")
        null_gen = (await db.execute(q)).scalar()
        if null_gen:
            print(f"\n  Warning: {null_gen} eval results have NULL generation_id (won't appear in family comparisons)")

        # Model cards still without extractions
        q = text("""
            SELECT d.slug, d.title
            FROM documents d
            WHERE d.doc_type = 'model_card'
            AND NOT EXISTS (
                SELECT 1 FROM document_versions dv
                JOIN extraction_runs er ON er.document_version_id = dv.id
                WHERE dv.document_id = d.id AND er.status = 'completed'
            )
            ORDER BY d.slug
        """)
        result = await db.execute(q)
        remaining = result.fetchall()
        if remaining:
            print(f"\nModel cards still without completed extractions ({len(remaining)}):")
            for r in remaining:
                print(f"  {r.slug}: {r.title}")
        else:
            print("\nAll model cards have completed extractions!")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Backfill Railway DB v2")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose only (read-only)")
    parser.add_argument(
        "--phase",
        choices=["collect", "link", "embed", "taxonomy", "extract", "all"],
        default="all",
        help="Run a specific phase",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("BACKFILL v2 — Railway DB")
    print(f"Target DB: {DB_URL[:50]}...")
    print(f"Mode: {'diagnose' if args.diagnose else args.phase}")
    print("=" * 70)

    # Always diagnose first
    await phase_0_diagnose()

    if args.diagnose:
        await engine.dispose()
        return

    phase_map = {
        "collect": phase_1_recollect,
        "link": phase_2_link_generations,
        "embed": phase_3_embeddings,
        "taxonomy": phase_4_taxonomy,
        "extract": phase_5_extract,
    }

    if args.phase == "all":
        await phase_1_recollect()
        await phase_2_link_generations()
        await phase_3_embeddings()
        await phase_4_taxonomy()
        await phase_5_extract()
    else:
        await phase_map[args.phase]()

    await phase_6_summary()
    await engine.dispose()

    print("\n" + "=" * 70)
    print("BACKFILL v2 COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
