#!/usr/bin/env python3
"""Seed taxonomy categories, probes, and AI models from data/ files."""
import asyncio
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.db.session import AsyncSessionLocal, init_db
from packages.db.models import TaxonomyCategory, ProbeDefinition, AIModel
from sqlalchemy import select

DATA_DIR = Path(__file__).parent.parent / "data"

MODELS = [
    # ── Groq (free) ──────────────────────────────────────────────────────────
    {"slug": "llama-3.3-70b",     "name": "Llama 3.3 70B",      "provider": "meta",    "litellm_id": "groq/llama-3.3-70b-versatile"},
    {"slug": "llama-3.1-8b",      "name": "Llama 3.1 8B",       "provider": "meta",    "litellm_id": "groq/llama-3.1-8b-instant"},
    {"slug": "llama-4-scout",     "name": "Llama 4 Scout 17B",  "provider": "meta",    "litellm_id": "groq/meta-llama/llama-4-scout-17b-16e-instruct"},
    # ── Google AI Studio (free) ──────────────────────────────────────────────
    {"slug": "gemini-2.0-flash",  "name": "Gemini 2.0 Flash",   "provider": "google",  "litellm_id": "gemini/gemini-2.0-flash"},
]


async def seed_taxonomy(db) -> int:
    data = yaml.safe_load((DATA_DIR / "taxonomy/safety_categories.yaml").read_text())
    count = 0
    for cat in data["categories"]:
        result = await db.execute(
            select(TaxonomyCategory).where(TaxonomyCategory.slug == cat["slug"])
        )
        if not result.scalar_one_or_none():
            db.add(TaxonomyCategory(
                slug=cat["slug"],
                name=cat["name"],
                description=cat["description"].strip(),
            ))
            count += 1
    await db.commit()
    return count


async def seed_probes(db) -> int:
    data = yaml.safe_load((DATA_DIR / "probes/probes.yaml").read_text())
    count = 0
    for p in data["probes"]:
        result = await db.execute(
            select(ProbeDefinition).where(ProbeDefinition.probe_key == p["slug"])
        )
        if not result.scalar_one_or_none():
            db.add(ProbeDefinition(
                probe_key=p["slug"],
                category=p["category"],
                prompt=p["prompt_text"].strip(),
                notes=f"slant_axis:{p['slant_axis']}",
            ))
            count += 1
    await db.commit()
    return count


async def seed_models(db) -> int:
    count = 0
    for m in MODELS:
        result = await db.execute(
            select(AIModel).where(AIModel.slug == m["slug"])
        )
        if not result.scalar_one_or_none():
            db.add(AIModel(**m))
            count += 1
    await db.commit()
    return count


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        t = await seed_taxonomy(db)
        p = await seed_probes(db)
        m = await seed_models(db)
    print(f"Seeded: {t} taxonomy categories, {p} probes, {m} models")


if __name__ == "__main__":
    asyncio.run(main())
