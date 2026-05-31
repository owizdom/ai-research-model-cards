#!/usr/bin/env python3
"""Local-only ingest for one new model card. Bypasses Railway collector.

Why bypass: collector service requires a redeploy + railway run dance to
pick up registry.py changes. For a single new card (Opus 4.8), we just
download + parse + insert directly here.

Use the slug from apps/collector/src/collectors/registry.py — this script
reads that file as the source of truth for URL, lab, doc_type, etc.

Usage:
  python3 scripts/ingest_one_local.py anthropic_opus48_card --apply
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import os
import re
import sys
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


def parse_registry_for_slug(slug: str) -> dict:
    """Crude but sufficient — parse registry.py for the Source(...) entry."""
    text = (ROOT / "apps/collector/src/collectors/registry.py").read_text()
    # Find Source("slug", ...)
    pattern = re.compile(
        rf'Source\(\s*"{re.escape(slug)}"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"',
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        raise SystemExit(f"slug {slug!r} not found in registry.py")
    return {
        "slug": slug,
        "lab_slug": m.group(1),
        "title": m.group(2),
        "doc_type": m.group(3),
        "url": m.group(4),
        "method": m.group(5),
    }


def fetch_pdf_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 AI-Safety-Research-Bot/1.0"}
    print(f"  fetching {url}")
    r = requests.get(url, headers=headers, allow_redirects=True, timeout=60)
    r.raise_for_status()
    print(f"  got {len(r.content):,} bytes (final URL {r.url})")
    reader = PdfReader(io.BytesIO(r.content))
    text = "\n\n".join(p.extract_text() for p in reader.pages if p.extract_text())
    print(f"  parsed {len(text):,} chars of text from {len(reader.pages)} pages")
    return text


def main(slug: str, apply: bool) -> None:
    src = parse_registry_for_slug(slug)
    print(f"source: {src['title']} (lab={src['lab_slug']}, type={src['doc_type']})")
    text = fetch_pdf_text(src["url"])
    if not text.strip():
        raise SystemExit("PDF parsed to empty text — bad source URL or pdf format")

    # Normalize newlines and strip wide whitespace runs (collector does the same)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.split("\n")).strip()
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    word_count = len(text.split())
    print(f"  word_count={word_count:,}  content_hash={content_hash[:12]}")

    if not apply:
        print("\n[dry-run] No DB writes. Re-run with --apply.")
        return

    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            # Lab id
            cur.execute("SELECT id FROM labs WHERE slug = %s", (src["lab_slug"],))
            row = cur.fetchone()
            if not row:
                raise SystemExit(f"lab {src['lab_slug']} not found in labs table")
            lab_id = row[0]

            # Upsert document
            cur.execute(
                """INSERT INTO documents (slug, lab_id, title, doc_type, source_url, updated_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())
                   ON CONFLICT (slug) DO UPDATE
                   SET title = EXCLUDED.title, doc_type = EXCLUDED.doc_type,
                       source_url = EXCLUDED.source_url, updated_at = NOW()
                   RETURNING id, (xmax = 0) AS inserted""",
                (slug, lab_id, src["title"], src["doc_type"], src["url"]),
            )
            doc_id, inserted = cur.fetchone()
            print(f"  document_id={doc_id}  {'(NEW)' if inserted else '(updated)'}")

            # Insert version (skip if same content_hash already exists for this doc)
            cur.execute(
                "SELECT id FROM document_versions WHERE document_id=%s AND content_hash=%s",
                (doc_id, content_hash),
            )
            existing = cur.fetchone()
            if existing:
                print(f"  version exists with same content_hash → version_id={existing[0]}, skipping insert")
                version_id = existing[0]
            else:
                cur.execute(
                    """INSERT INTO document_versions
                       (document_id, version_date, content_md, content_hash, word_count, fetched_at)
                       VALUES (%s, %s, %s, %s, %s, NOW())
                       RETURNING id""",
                    (doc_id, dt.date.today(), text, content_hash, word_count),
                )
                version_id = cur.fetchone()[0]
                print(f"  NEW version_id={version_id} (version_date={dt.date.today()})")
        conn.commit()

    print(f"\ndone — doc_id={doc_id}  version_id={version_id}")
    print(f"  next: python3 scripts/extract_local.py --doc-id {doc_id} --apply")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("slug", help="Source slug from registry.py (e.g. anthropic_opus48_card)")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    main(args.slug, args.apply)
