#!/usr/bin/env python3
"""Ad-hoc extraction CLI — counterpart to scripts/ingest_one.py.

Runs the same extract_evals_from_version() code path the worker uses, but
with overridable params (window size, anchor, timeout, model) so a maintainer
can recover a stuck card without redeploying the worker. Connects to the
Railway DB via DATABASE_URL in .env (same pattern as ingest_one.py).

Usage:
  python scripts/extract_one.py --doc-id 972                # standard
  python scripts/extract_one.py --doc-id 972 --window-size 45000
  python scripts/extract_one.py --doc-id 972 --anchor "Capability evaluation summary"
  python scripts/extract_one.py --doc-id 972 --timeout-s 1800 --model haiku
  python scripts/extract_one.py --doc-id 972 --dry-run      # extract + parse, don't commit

When --anchor is set, the script trims content_md to a 30k window starting
at the first occurrence of the anchor text, bypassing _extract_eval_sections.
Useful when the keyword-density selector picks the wrong region.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path


REPO = Path(__file__).parent.parent
env_path = REPO / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

if not os.environ.get("DATABASE_URL"):
    print("ERROR: DATABASE_URL not set (and not in .env)", file=sys.stderr)
    sys.exit(1)

# Make sure DATABASE_URL uses the asyncpg driver
if os.environ["DATABASE_URL"].startswith("postgresql://"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "apps" / "worker"))


async def run(args):
    # Apply CLI overrides via env so the worker code picks them up
    os.environ["CLAUDE_CLI_TIMEOUT_S"] = str(args.timeout_s)

    from src.extractor import eval_extractor
    from src.extractor.claude_cli import call_claude_cli
    from src.extractor.parse import parse_extraction_json
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import NullPool

    eng = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    Session = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    # Locate the version_id for the requested doc_id
    async with Session() as db:
        v = (await db.execute(text("""
            SELECT id, content_md FROM document_versions
            WHERE document_id = :d ORDER BY version_date DESC LIMIT 1
        """), {"d": args.doc_id})).first()
        if not v:
            print(f"ERROR: no version for doc_id={args.doc_id}", file=sys.stderr)
            return 1
        version_id = v.id
        md = v.content_md
        print(f"[extract_one] doc_id={args.doc_id}  version_id={version_id}  "
              f"content={len(md):,} chars")

    # Decide the window
    if args.anchor:
        idx = md.lower().find(args.anchor.lower())
        if idx < 0:
            print(f"ERROR: anchor '{args.anchor}' not found in content", file=sys.stderr)
            return 2
        window = md[idx : idx + args.window_size]
        print(f"[extract_one] anchored at char {idx}, window {len(window):,} chars")
    else:
        sections = eval_extractor._extract_eval_sections(md, max_chars=args.window_size)
        window = sections if sections else md[: args.window_size]
        print(f"[extract_one] section-selected window: {len(window):,} chars")

    # Call CLI
    print(f"[extract_one] calling Claude CLI (model={args.model}, timeout={args.timeout_s}s)")
    result = await call_claude_cli(
        eval_extractor.EXTRACTION_SYSTEM_PROMPT,
        eval_extractor.EXTRACTION_USER_PROMPT.format(content=window),
        model=args.model,
    )
    print(f"[extract_one] CLI returned {len(result.content):,} chars  "
          f"out_tok={result.output_tokens}")

    parsed = parse_extraction_json(result.content)
    items = parsed["results"] if isinstance(parsed, dict) and "results" in parsed else parsed
    print(f"[extract_one] parsed {len(items)} items")

    if args.dry_run:
        print(f"[extract_one] --dry-run: NOT committing. Sample names:")
        for it in items[:8]:
            print(f"  · {it.get('benchmark_name')}  score={it.get('score')}  model={it.get('model_name')}")
        await eng.dispose()
        return 0

    # Commit using the worker's idempotent insert path. Easiest way: stash the
    # already-parsed items into a global the eval_extractor can pick up, OR
    # just inline a copy of the persist loop. The latter is clearer here.
    from packages.db.models import (
        BenchmarkDefinition, EvalResult, ExtractionRun, ModelGeneration, Document,
    )
    from datetime import datetime, timezone
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    async with Session() as db:
        # Advisory lock — match the worker's key so we serialize properly
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                          {"k": f"extract:{version_id}"})

        gen = (await db.execute(select(ModelGeneration).where(
            ModelGeneration.document_id == args.doc_id))).scalar_one_or_none()
        gen_id = gen.id if gen else None
        print(f"[extract_one] generation_id={gen_id}")

        run_row = ExtractionRun(
            document_version_id=version_id,
            model_used=f"{args.model}-extract_one",
            status="running",
        )
        db.add(run_row)
        await db.flush()
        print(f"[extract_one] created run #{run_row.id}")

        count = 0
        skipped = 0
        for item in items:
            name = (item.get("benchmark_name") or "").strip()
            if not name:
                continue
            state = (item.get("state") or "scored").strip().lower()
            raw_score = item.get("score")
            score = None
            if state == "scored":
                if raw_score is None:
                    continue
                try:
                    score = float(raw_score)
                except (ValueError, TypeError):
                    continue

            bench_id = await eval_extractor._create_benchmark(db, name, item)

            shot = item.get("shot_count")
            method = (item.get("method") or "").strip().lower() or None
            language = (item.get("language") or "").strip() or None
            training_state = (item.get("training_state") or "").strip().lower() or None
            model_name = (item.get("model_name") or "").strip() or None

            parts = []
            if shot is not None:
                parts.append(f"{shot}-shot")
            if method and method != "none":
                parts.append(method)
            if language and language != "English":
                parts.append(language)
            if training_state and training_state != "unknown":
                parts.append(training_state)
            variant = ", ".join(parts) if parts else "default"

            stmt = pg_insert(EvalResult).values(
                document_version_id=version_id, benchmark_id=bench_id,
                generation_id=gen_id, score=score, variant=variant,
                model_name=model_name, state=state,
                shot_count=shot if isinstance(shot, int) else None,
                method=method, language=language, training_state=training_state,
                extraction_protocol_version=eval_extractor.EXTRACTION_PROTOCOL_VERSION,
                score_details={"raw_text": item.get("context", ""),
                                "metric": item.get("metric", ""),
                                "model_name": item.get("model_name", "")},
                extraction_confidence=0.85, is_self_reported=True, source_type="model_card",
            ).on_conflict_do_nothing(constraint="uq_eval_result").returning(EvalResult.id)
            res = await db.execute(stmt)
            if res.first():
                count += 1
            else:
                skipped += 1

        run_row.status = "completed"
        run_row.evals_extracted = count
        run_row.completed_at = datetime.now(timezone.utc)
        await db.commit()
        print(f"[extract_one] DONE — inserted={count}  skipped_dup={skipped}  run #{run_row.id}")

    await eng.dispose()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--doc-id", type=int, required=True)
    ap.add_argument("--window-size", type=int, default=30000,
                    help="Content window size in chars (default 30000)")
    ap.add_argument("--anchor", type=str, default=None,
                    help="Force the window to start at the first occurrence of this text")
    ap.add_argument("--timeout-s", type=int, default=1500,
                    help="Claude CLI subprocess timeout (default 1500)")
    ap.add_argument("--model", type=str, default="sonnet",
                    help="Extractor model (sonnet|haiku|opus, default sonnet)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Extract + parse but don't write to DB")
    args = ap.parse_args()
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
