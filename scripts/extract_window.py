#!/usr/bin/env python3
"""Ad-hoc extraction targeting a specific char-position window of one card.

For the rare case where the auto window-selector picks the wrong region —
e.g. Claude Opus 4.8 (508k chars) has two benchmark-dense regions and the
anchor-based selector only catches the first. This script lets an operator
say "give me chars 380000..410000 of doc 973" and extract from exactly that.

Idempotent: appends v3 rows; ON CONFLICT DO NOTHING handles overlap.

Usage:
  python3 scripts/extract_window.py --doc-id 973 --start 380000 --end 410000 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

sys.path.insert(0, str(ROOT / "scripts"))
# Reuse the proven extract_local helpers
from extract_local import (  # noqa: E402
    EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT,
    CLAUDE_BIN, MODEL, DISALLOWED_TOOLS, EXTRACTION_PROTOCOL_VERSION,
    parse_results, upsert_benchmark, _build_variant,
)


async def call_claude(content: str, timeout_s: float = 1200) -> tuple[str | None, str]:
    user = EXTRACTION_USER_PROMPT.format(content=content)
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
            *args, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                pass
        return None, f"timeout after {timeout_s}s"
    if proc.returncode != 0:
        return None, f"exit {proc.returncode}: {(stderr or b'').decode(errors='replace')[:300]} | {(stdout or b'').decode(errors='replace')[:300]}"
    try:
        envelope = json.loads(stdout.decode())
    except json.JSONDecodeError as e:
        return None, f"bad envelope: {e}"
    if envelope.get("is_error"):
        return None, f"is_error: {envelope.get('result','?')[:300]}"
    return (envelope.get("result") or "").strip(), ""


async def main(doc_id: int, start: int, end: int, apply: bool) -> None:
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT dv.id, dv.content_md FROM document_versions dv
                           WHERE document_id=%s ORDER BY version_date DESC LIMIT 1""", (doc_id,))
            version_id, content = cur.fetchone()

    window = content[start:end]
    print(f"doc={doc_id}  version={version_id}  window=chars[{start}..{end}] = {len(window):,} chars")
    print(f"  sample start: {window[:100]!r}")
    print(f"  sample end:   {window[-100:]!r}")

    raw, err = await call_claude(window)
    if raw is None:
        print(f"FAILED: {err}")
        return
    results = parse_results(raw)
    print(f"  → {len(results)} hits")
    for r in results[:5]:
        print(f"    {r.get('benchmark_name')!r}  score={r.get('score')!r}  split={r.get('split')!r}  metric={r.get('metric_path')!r}  model={r.get('model_name')!r}")
    if not apply:
        print("\n[dry-run] No DB writes. Re-run with --apply to insert.")
        return

    inserted = skipped = 0
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            for r in results:
                name = (r.get("benchmark_name") or "").strip()
                if not name: continue
                bid = upsert_benchmark(cur, name)
                if bid is None: continue
                shot_count = r.get("shot_count") if isinstance(r.get("shot_count"), int) else None
                method = (r.get("method") or "").strip().lower() or None
                language = (r.get("language") or "").strip() or None
                training_state = (r.get("training_state") or "").strip().lower() or None
                split = (r.get("split") or "").strip().lower() or None
                metric_path = (r.get("metric_path") or "").strip().lower() or None
                model_name = (r.get("model_name") or "").strip() or None
                state = (r.get("state") or "scored").strip().lower()
                score = r.get("score")
                if score is not None:
                    try: score = float(score)
                    except (TypeError, ValueError): score = None
                variant = _build_variant(shot_count, method, language, training_state, split, metric_path)
                cur.execute("""INSERT INTO eval_results
                    (document_version_id, benchmark_id, score, variant, model_name,
                     state, shot_count, method, language, training_state, split, metric_path,
                     extraction_protocol_version, score_details, extraction_confidence,
                     is_self_reported, source_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT uq_eval_result DO NOTHING RETURNING id""",
                    (version_id, bid, score, variant, model_name, state,
                     shot_count, method, language, training_state, split, metric_path,
                     EXTRACTION_PROTOCOL_VERSION,
                     json.dumps({"raw_text": (r.get("context") or "")[:300], "metric": r.get("metric") or ""}),
                     0.85, True, "model_card"))
                if cur.fetchone(): inserted += 1
                else: skipped += 1
        conn.commit()
    print(f"  inserted: {inserted}, dup-skipped: {skipped}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--doc-id", type=int, required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    asyncio.run(main(args.doc_id, args.start, args.end, args.apply))
