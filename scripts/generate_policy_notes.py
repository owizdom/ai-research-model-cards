#!/usr/bin/env python3
"""LLM-draft policy notes for benchmark_definitions rows whose policy_note
column is NULL. Paper-aligned: EvalCards Section 4.1 explicitly uses
LLM-generated Auto-BenchmarkCards for the same purpose, then human-reviews.

Pipeline:
  1. Pick the top-N most-used benchmarks (by eval_results count) where
     policy_note IS NULL.
  2. For each, gather slug/name/category/description + 5 most-frequent
     variant strings observed in eval_results (extractor's hints about
     splits, metrics, methodology).
  3. Call Claude (CLI subprocess, ~$0 on Max subscription) with a focused
     JSON-output prompt → measures/caveat/intended_for/how_to_read/
     topic_tags/sources.
  4. Validate the returned JSON; UPDATE benchmark_definitions on success.

Concurrency knob: --workers N runs N claude subprocesses in parallel.
Default 4 is conservative for OAuth quota.

Idempotent — re-runs only fill rows that are still NULL.

Usage:
  python3 scripts/generate_policy_notes.py --limit 30          # dry-run
  python3 scripts/generate_policy_notes.py --limit 30 --apply
  python3 scripts/generate_policy_notes.py --limit 400 --apply --workers 6
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
MODEL = os.environ.get("POLICY_NOTE_MODEL", "sonnet")

DISALLOWED_TOOLS = (
    "Read,Edit,Write,Bash,Glob,Grep,WebFetch,WebSearch,"
    "Agent,NotebookEdit,Skill,TaskCreate,TaskUpdate,TaskList"
)

SYSTEM_PROMPT = """You are a precise AI benchmark documentation writer.

Given a benchmark's name and metadata, write a Policy Note as a single JSON
object with these exact fields:

- measures (string): 1-2 plain-language sentences describing what the
  benchmark measures. Concrete: dataset size when known, task format,
  what kind of capability is being probed.
- caveat (string | null): known issues — saturation (frontier models score
  too high to differentiate), contamination (training-data leakage),
  errata in the dataset, label conflation between variants (e.g. SWE-bench
  vs SWE-bench Verified, MMLU vs MMLU-Pro), or scaffold dependence
  (different agentic frameworks produce different scores). Null if you
  genuinely don't know specific issues — DO NOT FABRICATE.
- intended_for (string): audience and primary use case.
- how_to_read (string): direction (higher better / lower better) plus
  scale context (typical frontier range, total models compared, etc.).
- topic_tags (array of 2-5 lowercase snake_case strings): topic markers
  like "coding", "math", "biology", "safety", "instruction_following",
  "long_context", "multimodal", "multilingual". Be concrete.
- sources (object): {label: url} flat map. Standard labels: "paper",
  "dataset", "source", "homepage". Only include if you're CONFIDENT
  the URL is correct. Better to return {} than to fabricate a URL.

Return ONLY the JSON object. No prose, no markdown fences, no backticks.
"""

USER_TEMPLATE = """Write the Policy Note for this benchmark.

Slug: {slug}
Name: {name}
Category: {category}
Existing description: {description}
Variant strings observed in cards reporting this benchmark: {variants}

Return JSON only.
"""


async def call_claude(system: str, user: str, timeout_s: float = 60) -> dict | None:
    """Run claude CLI, return parsed result JSON or None on any failure.

    Important: on timeout we MUST kill the subprocess. asyncio.wait_for only
    cancels the awaitable; the subprocess keeps running and ties up file
    descriptors + the CLI's network connection. The first version of this
    script had subprocesses hanging for 23+ minutes because of this — the
    Python side moved on but the orphans accumulated and saturated CLI capacity.
    """
    args = [
        CLAUDE_BIN, "-p", user,
        "--append-system-prompt", system,
        "--output-format", "json",
        "--model", MODEL,
        "--no-session-persistence",
        "--disallowedTools", DISALLOWED_TOOLS,
        "--max-budget-usd", "1.0",
    ]
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                pass
        return None
    except FileNotFoundError:
        print(f"ERROR: claude CLI not found at {CLAUDE_BIN}", file=sys.stderr)
        return None

    if proc.returncode != 0:
        return None
    try:
        envelope = json.loads(stdout.decode())
    except json.JSONDecodeError:
        return None
    if envelope.get("is_error"):
        return None
    inner = (envelope.get("result") or "").strip()
    # Strip any accidental markdown fence
    if inner.startswith("```"):
        inner = inner.split("\n", 1)[-1]
        if inner.endswith("```"):
            inner = inner.rsplit("```", 1)[0]
    inner = inner.strip()
    try:
        return json.loads(inner)
    except json.JSONDecodeError:
        return None


def validate_note(note: dict) -> dict | None:
    """Coerce a draft to our shape. Returns None if unfixable."""
    if not isinstance(note, dict):
        return None
    out = {}
    for k in ("measures", "caveat", "intended_for", "how_to_read"):
        v = note.get(k)
        if v is None:
            out[k] = None
        elif isinstance(v, str):
            out[k] = v.strip() or None
        else:
            return None
    tags = note.get("topic_tags") or []
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        return None
    out["topic_tags"] = [t.lower().strip().replace(" ", "_") for t in tags if t.strip()][:6]
    sources = note.get("sources") or {}
    if not isinstance(sources, dict):
        return None
    out["sources"] = {
        str(k).strip().lower(): str(v).strip()
        for k, v in sources.items()
        if isinstance(v, str) and v.strip().startswith("http")
    }
    if not out["measures"]:
        return None  # measures is the load-bearing field
    return out


async def gen_one(row, sem) -> tuple[str, dict | None]:
    slug, name, category, description, variants = row
    async with sem:
        user = USER_TEMPLATE.format(
            slug=slug,
            name=name or slug,
            category=category or "unknown",
            description=description or "(no description in registry)",
            variants=", ".join(variants[:5]) if variants else "none",
        )
        note = await call_claude(SYSTEM_PROMPT, user)
        if note is None:
            return slug, None
        return slug, validate_note(note)


def _write_one(slug: str, note: dict) -> None:
    """Sync UPDATE — fresh connection per write so it's safe to call from
    asyncio via run_in_executor without worrying about psycopg2 thread-safety."""
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE benchmark_definitions SET policy_note = %s "
                "WHERE slug = %s AND policy_note IS NULL",
                (json.dumps(note), slug),
            )
        conn.commit()


async def main(limit: int, apply: bool, workers: int) -> None:
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT bd.slug, bd.name, bd.category, bd.description,
                       COALESCE(array_agg(DISTINCT er.variant)
                                FILTER (WHERE er.variant IS NOT NULL AND er.variant != 'default'),
                                ARRAY[]::text[]) AS variants,
                       COUNT(er.id) AS n
                FROM benchmark_definitions bd
                LEFT JOIN eval_results er ON er.benchmark_id = bd.id
                WHERE bd.policy_note IS NULL
                GROUP BY bd.id, bd.slug, bd.name, bd.category, bd.description
                ORDER BY n DESC, bd.slug
                LIMIT %s
            """, (limit,))
            targets = cur.fetchall()

    print(f"targets: {len(targets)} benchmarks (top by eval_results count)", flush=True)
    print(f"workers: {workers}, model: {MODEL}, apply: {apply}", flush=True)
    if not targets:
        return

    rows = [(slug, name, category, description, variants)
            for slug, name, category, description, variants, _n in targets]

    sem = asyncio.Semaphore(workers)
    start = time.time()
    completed = 0
    successes = 0
    failures: list[str] = []
    loop = asyncio.get_event_loop()

    async def run_and_report(row):
        nonlocal completed, successes
        slug, note = await gen_one(row, sem)
        completed += 1
        if note is None:
            failures.append(slug)
            print(f"  [{completed}/{len(rows)}] {slug:40s} ✗ FAILED", flush=True)
        else:
            # Commit per row: progress is visible in the DB as it runs and
            # a mid-run kill loses at most one row's work.
            if apply:
                try:
                    await loop.run_in_executor(None, _write_one, slug, note)
                except Exception as e:
                    print(f"  [{completed}/{len(rows)}] {slug:40s} ⚠ DB write failed: {e}", flush=True)
                    failures.append(slug)
                    return slug, None
            successes += 1
            preview = (note["measures"] or "")[:60].replace("\n", " ")
            print(f"  [{completed}/{len(rows)}] {slug:40s} ✓ {preview}...", flush=True)
        return slug, note

    await asyncio.gather(*(run_and_report(r) for r in rows))
    elapsed = time.time() - start
    print(flush=True)
    print(f"=== {successes}/{len(rows)} succeeded in {elapsed:.1f}s "
          f"(avg {elapsed/max(1,len(rows)):.1f}s/call) ===", flush=True)
    if failures:
        print(f"failed: {failures[:10]}{'...' if len(failures) > 10 else ''}", flush=True)
    if not apply:
        print("\n[dry-run] No DB writes. Re-run with --apply to commit.", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--limit", type=int, default=10,
                   help="Max number of benchmarks to draft notes for. Sorted by eval_results count desc.")
    p.add_argument("--apply", action="store_true",
                   help="Commit writes. Without this, drafts are generated and printed but not persisted.")
    p.add_argument("--workers", type=int, default=4,
                   help="Number of concurrent claude CLI subprocesses (default 4).")
    args = p.parse_args()
    asyncio.run(main(limit=args.limit, apply=args.apply, workers=args.workers))
