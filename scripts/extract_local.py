#!/usr/bin/env python3
"""Local v3 extraction — bypasses the Railway worker.

Why bypass: the worker's claude CLI subprocess fails inside the Railway
container with `exit 1: <empty stderr>` and we haven't yet isolated the
environment difference (token caching path? cwd? .claude.json schema?).
Local claude CLI works (we just used it for 475 policy notes). Same OAuth
token, same DATABASE_URL, same prod DB → same outcome.

Pipeline (one task per doc, parallel via asyncio.Semaphore):
  1. SELECT documents WHERE doc_type='model_card'
  2. For each, skip if any extraction_protocol_version=3 row already exists
  3. INSERT extraction_runs (status=running)
  4. Send full content_md to claude CLI with the v3 prompt
     (No 30k window — Sonnet 4.6 has 200k context; whole-card extraction
      is strictly better for the prose-context split/metric_path goal)
  5. Parse JSON, resolve benchmark slug (create if missing), insert
     eval_results with extraction_protocol_version=3, ON CONFLICT DO NOTHING
  6. UPDATE extraction_runs (status=completed/failed, evals_extracted=N)

Usage:
  python3 scripts/extract_local.py --doc-id 24                  # one doc, dry-run
  python3 scripts/extract_local.py --doc-id 24 --apply          # one doc, write
  python3 scripts/extract_local.py --all --apply --workers 3    # full corpus

Idempotent: re-runs skip docs already at v3.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


def _connect_with_retry(max_attempts: int = 4, base_backoff: float = 2.0):
    """psycopg2.connect() with retry on transient network errors.

    The Railway DB proxy occasionally returns "Can't assign requested address"
    (ephemeral port pressure on the proxy side) or sudden EOFs; treat both as
    retryable rather than failing the whole 51-card extraction over one blip.
    """
    last_err = None
    for attempt in range(max_attempts):
        try:
            return psycopg2.connect(DB_URL)
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            last_err = e
            if attempt == max_attempts - 1:
                raise
            time.sleep(base_backoff * (attempt + 1))
    raise RuntimeError(f"db connect failed: {last_err}")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
MODEL = os.environ.get("EXTRACTION_MODEL", "sonnet")
EXTRACTION_PROTOCOL_VERSION = 3
# 30k chars ~= 7.5k tokens. Matches the worker's WINDOW_SIZE_DEFAULT exactly
# (60k was 2x slower than expected — sonnet took 13+ min on the GPT-5 card).
# Worker historically extracted 207 hits from Llama with this window size in
# ~4 min, so this is the proven configuration.
MAX_CONTENT_CHARS = 30_000
# Char threshold above which we use a smart window (anchor + back-half bias)
# rather than just taking the first MAX_CONTENT_CHARS. Most cards smaller than
# this are short enough to send whole.
LONG_DOC_THRESHOLD = 40_000

# Anchors that mark the canonical capability table — when present, we slice a
# window starting just before the anchor. Mirrors the worker's CAPABILITY_ANCHORS.
CAPABILITY_ANCHORS = [
    "capability evaluation summary", "benchmark results", "performance overview",
    "swe-bench verified", "gpqa diamond", "mmlu-pro", "humaneval+",
    "livecodebench", "evaluation summary",
]


def select_content_window(content: str) -> str:
    """Return at most MAX_CONTENT_CHARS chars of content. For long docs, prefer
    a window centered on a capability anchor; else take the back half (most
    cards put benchmark tables near the end, behind the safety prose)."""
    if not content:
        return ""
    if len(content) <= MAX_CONTENT_CHARS:
        return content
    if len(content) <= LONG_DOC_THRESHOLD:
        return content[:MAX_CONTENT_CHARS]
    # Long doc: try anchor-first window
    lower = content.lower()
    best_anchor_pos = -1
    for anchor in CAPABILITY_ANCHORS:
        pos = lower.find(anchor)
        if pos != -1 and (best_anchor_pos == -1 or pos < best_anchor_pos):
            best_anchor_pos = pos
    if best_anchor_pos != -1:
        # Start 5k chars before the anchor so we capture preceding section
        # header context (split names live in section titles).
        start = max(0, best_anchor_pos - 5_000)
        return content[start:start + MAX_CONTENT_CHARS]
    # No anchor — bias toward the back half (capability tables tend to come
    # after introduction + safety sections in long Anthropic/OpenAI cards).
    start = max(0, len(content) - MAX_CONTENT_CHARS)
    return content[start:]

DISALLOWED_TOOLS = (
    "Read,Edit,Write,Bash,Glob,Grep,WebFetch,WebSearch,"
    "Agent,NotebookEdit,Skill,TaskCreate,TaskUpdate,TaskList"
)


# v3 prompts — sourced from apps/worker/src/extractor/eval_extractor.py at module
# load so they cannot drift. The old inline copy was missing the EXAMPLES,
# SPLIT GUIDANCE, and "Extract rows for ALL models in comparison tables" rules
# that the worker's prompt has, which caused Sonnet to skip the master
# comparison table in the Opus 4.8 card extraction (only 3 of ~50 rows emitted).
def _load_worker_prompts() -> tuple[str, str]:
    src = (ROOT / "apps/worker/src/extractor/eval_extractor.py").read_text()
    sys_m = re.search(r'EXTRACTION_SYSTEM_PROMPT = """(.*?)"""', src, re.DOTALL)
    usr_m = re.search(r'EXTRACTION_USER_PROMPT = """(.*?)"""', src, re.DOTALL)
    if not sys_m or not usr_m:
        raise RuntimeError("could not locate EXTRACTION_*_PROMPT in eval_extractor.py")
    return sys_m.group(1), usr_m.group(1)


EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT = _load_worker_prompts()


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", s.lower())
    return s.strip("_")


def _build_variant(shot_count, method, language, training_state, split, metric_path) -> str:
    parts = []
    if shot_count is not None:
        parts.append(f"{shot_count}-shot")
    if method and method != "none":
        parts.append(method)
    if language and language != "English":
        parts.append(language)
    if training_state and training_state != "unknown":
        parts.append(training_state)
    if split:
        parts.append(split)
    if metric_path:
        parts.append(metric_path)
    return ", ".join(parts) if parts else "default"


async def call_claude(content: str, timeout_s: float = 600) -> tuple[str | None, str]:
    """Run claude CLI. Returns (parsed_result_text, error_message_if_any)."""
    user = EXTRACTION_USER_PROMPT.format(content=select_content_window(content))
    args = [
        CLAUDE_BIN, "-p", user,
        "--append-system-prompt", EXTRACTION_SYSTEM_PROMPT,
        "--output-format", "json",
        "--model", MODEL,
        "--no-session-persistence",
        "--disallowedTools", DISALLOWED_TOOLS,
        "--max-budget-usd", "2.0",
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
        return None, f"timeout after {timeout_s}s"
    except FileNotFoundError:
        return None, f"claude CLI not found at {CLAUDE_BIN}"

    if proc.returncode != 0:
        err = (stderr or b"").decode(errors="replace")[:500]
        out = (stdout or b"").decode(errors="replace")[:500]
        return None, f"exit {proc.returncode}: stderr={err!r} stdout={out!r}"

    try:
        envelope = json.loads(stdout.decode())
    except json.JSONDecodeError as e:
        return None, f"bad envelope JSON: {e}"
    if envelope.get("is_error"):
        return None, f"claude is_error: {envelope.get('result', 'unknown')}"
    return (envelope.get("result") or "").strip(), ""


def parse_results(raw: str) -> list[dict]:
    """Tolerant parse — accept ```json fences, prose wrappers, etc."""
    if not raw:
        return []
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
        s = s.strip()
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        # Last-ditch: find outer {...}
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return []
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(obj, dict):
        return obj.get("results", []) or []
    if isinstance(obj, list):
        return obj
    return []


def upsert_benchmark(cur, name: str) -> int | None:
    """Resolve a benchmark_name to benchmark_definitions.id, inserting if new."""
    if not name:
        return None
    slug = _slugify(name)
    if not slug:
        return None
    cur.execute("SELECT id FROM benchmark_definitions WHERE slug = %s", (slug,))
    row = cur.fetchone()
    if row:
        return row[0]
    # Insert new
    cur.execute(
        "INSERT INTO benchmark_definitions (slug, name, category, higher_is_better) "
        "VALUES (%s, %s, 'other', true) "
        "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name "
        "RETURNING id",
        (slug, name),
    )
    return cur.fetchone()[0]


async def extract_one_doc(doc_row: tuple, semaphore: asyncio.Semaphore, apply: bool) -> dict:
    """Extract evals from one document. Returns a result dict for reporting."""
    doc_id, doc_title, version_id, content_md = doc_row
    async with semaphore:
        # Idempotency: skip if any v3 rows exist for this version
        with _connect_with_retry() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM eval_results WHERE document_version_id = %s "
                    "AND extraction_protocol_version = %s",
                    (version_id, EXTRACTION_PROTOCOL_VERSION),
                )
                if cur.fetchone()[0] > 0:
                    return {"doc_id": doc_id, "title": doc_title, "status": "skipped",
                            "reason": f"already has v{EXTRACTION_PROTOCOL_VERSION} rows", "inserted": 0}

        # Create extraction_runs row (if applying)
        run_id = None
        if apply:
            with _connect_with_retry() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO extraction_runs (document_version_id, model_used, status) "
                        "VALUES (%s, %s, 'running') RETURNING id",
                        (version_id, MODEL),
                    )
                    run_id = cur.fetchone()[0]
                conn.commit()

        t0 = time.time()
        raw, err = await call_claude(content_md or "")
        elapsed = time.time() - t0
        if raw is None:
            if apply and run_id is not None:
                with _connect_with_retry() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE extraction_runs SET status='failed', error=%s, "
                            "completed_at=NOW() WHERE id=%s",
                            (err[:1000], run_id),
                        )
                    conn.commit()
            return {"doc_id": doc_id, "title": doc_title, "status": "failed",
                    "reason": err, "inserted": 0, "elapsed": elapsed}

        results = parse_results(raw)
        if not apply:
            return {"doc_id": doc_id, "title": doc_title, "status": "dry-run",
                    "found": len(results), "inserted": 0, "elapsed": elapsed,
                    "sample": results[:3]}

        # Persist
        inserted = 0
        skipped = 0
        with _connect_with_retry() as conn:
            with conn.cursor() as cur:
                for r in results:
                    name = (r.get("benchmark_name") or "").strip()
                    if not name:
                        continue
                    benchmark_id = upsert_benchmark(cur, name)
                    if benchmark_id is None:
                        continue
                    shot_count = r.get("shot_count")
                    if not isinstance(shot_count, int):
                        shot_count = None
                    method = (r.get("method") or "").strip().lower() or None
                    language = (r.get("language") or "").strip() or None
                    training_state = (r.get("training_state") or "").strip().lower() or None
                    split = (r.get("split") or "").strip().lower() or None
                    metric_path = (r.get("metric_path") or "").strip().lower() or None
                    model_name = (r.get("model_name") or "").strip() or None
                    state = (r.get("state") or "scored").strip().lower()
                    score = r.get("score")
                    if score is not None:
                        try:
                            score = float(score)
                        except (TypeError, ValueError):
                            score = None
                    variant = _build_variant(shot_count, method, language, training_state, split, metric_path)
                    cur.execute(
                        """INSERT INTO eval_results
                           (document_version_id, benchmark_id, score, variant, model_name,
                            state, shot_count, method, language, training_state, split, metric_path,
                            extraction_protocol_version, score_details, extraction_confidence,
                            is_self_reported, source_type)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT ON CONSTRAINT uq_eval_result DO NOTHING
                           RETURNING id""",
                        (version_id, benchmark_id, score, variant, model_name,
                         state, shot_count, method, language, training_state, split, metric_path,
                         EXTRACTION_PROTOCOL_VERSION,
                         json.dumps({"raw_text": (r.get("context") or "")[:300],
                                     "metric": r.get("metric") or "",
                                     "model_name": model_name or ""}),
                         0.85, True, "model_card"),
                    )
                    if cur.fetchone():
                        inserted += 1
                    else:
                        skipped += 1
                # Update run
                if run_id is not None:
                    cur.execute(
                        "UPDATE extraction_runs SET status='completed', "
                        "evals_extracted=%s, completed_at=NOW() WHERE id=%s",
                        (inserted, run_id),
                    )
            conn.commit()

        return {"doc_id": doc_id, "title": doc_title, "status": "completed",
                "found": len(results), "inserted": inserted, "skipped_dup": skipped,
                "elapsed": elapsed}


async def main(doc_id: int | None, do_all: bool, apply: bool, workers: int, limit: int | None) -> None:
    # Pick docs
    with _connect_with_retry() as conn:
        with conn.cursor() as cur:
            if doc_id is not None:
                cur.execute("""
                    SELECT d.id, d.title, dv.id, dv.content_md
                    FROM documents d
                    JOIN document_versions dv ON dv.document_id = d.id
                    WHERE d.id = %s
                    ORDER BY dv.version_date DESC LIMIT 1
                """, (doc_id,))
            elif do_all:
                base = """
                    SELECT d.id, d.title, dv.id, dv.content_md
                    FROM documents d
                    JOIN LATERAL (
                        SELECT id, content_md FROM document_versions
                        WHERE document_id = d.id
                        ORDER BY version_date DESC LIMIT 1
                    ) dv ON true
                    WHERE d.doc_type = 'model_card' AND dv.content_md IS NOT NULL
                    ORDER BY length(dv.content_md) ASC
                """
                if limit:
                    base += f" LIMIT {int(limit)}"
                cur.execute(base)
            else:
                print("ERROR: pass --doc-id N or --all", file=sys.stderr)
                sys.exit(2)
            docs = cur.fetchall()

    print(f"targets: {len(docs)} model cards", flush=True)
    print(f"workers={workers}, model={MODEL}, apply={apply}", flush=True)
    if not docs:
        return

    sem = asyncio.Semaphore(workers)
    start = time.time()
    completed = 0
    total_inserted = 0
    failures: list[str] = []

    async def run_and_report(d):
        nonlocal completed, total_inserted
        r = await extract_one_doc(d, sem, apply)
        completed += 1
        if r["status"] in ("failed",):
            failures.append(f"{r['doc_id']}: {r['reason'][:120]}")
            print(f"  [{completed}/{len(docs)}] doc={r['doc_id']:4d}  ✗ FAILED: {r['reason'][:150]}", flush=True)
        elif r["status"] == "skipped":
            print(f"  [{completed}/{len(docs)}] doc={r['doc_id']:4d}  ⊘ skipped: {r['reason']}", flush=True)
        elif r["status"] == "dry-run":
            print(f"  [{completed}/{len(docs)}] doc={r['doc_id']:4d}  · {r['found']} hits ({r['elapsed']:.1f}s) — {r['title'][:50]}", flush=True)
            if r.get("sample"):
                for s in r["sample"][:3]:
                    print(f"        sample: bench={s.get('benchmark_name')!r} score={s.get('score')!r} split={s.get('split')!r} metric={s.get('metric_path')!r}", flush=True)
        else:
            total_inserted += r["inserted"]
            print(f"  [{completed}/{len(docs)}] doc={r['doc_id']:4d}  ✓ {r['inserted']:3d} inserted "
                  f"(+{r['skipped_dup']} dup, {r['found']} hits, {r['elapsed']:.1f}s) — {r['title'][:40]}", flush=True)

    await asyncio.gather(*(run_and_report(d) for d in docs))
    elapsed = time.time() - start
    print(flush=True)
    print(f"=== {len(docs) - len(failures)}/{len(docs)} succeeded, {total_inserted} v3 rows inserted, {elapsed:.1f}s ===", flush=True)
    if failures:
        print(f"failed:", flush=True)
        for f in failures: print(f"  {f}", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--doc-id", type=int, help="Extract just this document_id")
    p.add_argument("--all", action="store_true", help="Extract every doc_type='model_card' document")
    p.add_argument("--apply", action="store_true", help="Commit writes (default dry-run)")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--limit", type=int, help="Limit total docs (use with --all)")
    args = p.parse_args()
    asyncio.run(main(args.doc_id, args.all, args.apply, args.workers, args.limit))
