#!/usr/bin/env python3
"""Seed taxonomy categories, benchmarks, and model families from data/ files."""
import asyncio
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.db.session import AsyncSessionLocal, init_db
from packages.db.models import (
    TaxonomyCategory, BenchmarkDefinition, ModelFamily, ModelGeneration, Lab, Document,
)
from sqlalchemy import select

DATA_DIR = Path(__file__).parent.parent / "data"


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


async def seed_benchmarks(db) -> int:
    path = DATA_DIR / "benchmarks/benchmark_definitions.yaml"
    if not path.exists():
        return 0
    data = yaml.safe_load(path.read_text())
    count = 0
    for b in data.get("benchmarks", []):
        result = await db.execute(
            select(BenchmarkDefinition).where(BenchmarkDefinition.slug == b["slug"])
        )
        if not result.scalar_one_or_none():
            db.add(BenchmarkDefinition(
                slug=b["slug"],
                name=b["name"],
                category=b["category"],
                description=b.get("description"),
                metric_name=b.get("metric_name"),
                metric_unit=b.get("metric_unit"),
                higher_is_better=b.get("higher_is_better", True),
                source_url=b.get("source_url"),
                aliases=b.get("aliases"),
            ))
            count += 1
    await db.commit()
    return count


async def seed_families(db) -> int:
    path = DATA_DIR / "model_families/families.yaml"
    if not path.exists():
        return 0
    data = yaml.safe_load(path.read_text())
    count = 0
    for fam in data.get("families", []):
        # Find the lab
        lab_result = await db.execute(select(Lab).where(Lab.slug == fam["lab_slug"]))
        lab = lab_result.scalar_one_or_none()
        if not lab:
            print(f"  Warning: lab '{fam['lab_slug']}' not found, skipping family '{fam['slug']}'")
            continue

        # Create family if not exists
        fam_result = await db.execute(
            select(ModelFamily).where(ModelFamily.slug == fam["slug"])
        )
        family = fam_result.scalar_one_or_none()
        if not family:
            family = ModelFamily(slug=fam["slug"], name=fam["name"], lab_id=lab.id)
            db.add(family)
            await db.flush()
            count += 1

        # Create generations
        for gen in fam.get("generations", []):
            gen_result = await db.execute(
                select(ModelGeneration).where(ModelGeneration.slug == gen["slug"])
            )
            if not gen_result.scalar_one_or_none():
                # Try to find the linked document
                doc_id = None
                if doc_slug := gen.get("document_slug"):
                    doc_result = await db.execute(
                        select(Document).where(Document.slug == doc_slug)
                    )
                    doc = doc_result.scalar_one_or_none()
                    if doc:
                        doc_id = doc.id

                db.add(ModelGeneration(
                    family_id=family.id,
                    slug=gen["slug"],
                    name=gen["name"],
                    version_label=gen.get("version_label"),
                    document_id=doc_id,
                ))
                count += 1

    await db.commit()
    return count


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        t = await seed_taxonomy(db)
        b = await seed_benchmarks(db)
        f = await seed_families(db)
    print(f"Seeded: {t} taxonomy categories, {b} benchmarks, {f} families/generations")


if __name__ == "__main__":
    asyncio.run(main())
