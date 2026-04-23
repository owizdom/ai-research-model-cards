"""Generate chaptered summaries for every document's latest version via Claude CLI.

Run: DATABASE_URL=<prod> python3 scripts/generate_summaries.py
Optionally: --only <doc_id> for a single doc. --force to regenerate.
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text, select

from apps.api.src.api.v1.documents import _clean_content
from apps.worker.src.extractor.claude_cli import call_claude_cli

SYSTEM_PROMPT = """You are a neutral research summarizer producing tight chaptered briefs of AI model cards — the kind a busy researcher skims in 90 seconds.

Your output is consumed by researchers who need a faithful, scannable rendering of what the lab claims — not what the reader hopes or worries about.

## Hard rules
1. ALWAYS produce EXACTLY these 8 chapters in this exact order, even when material is thin:
   - "What this is"
   - "Capabilities"
   - "Evaluation methodology"
   - "Safety testing"
   - "Mitigations"
   - "Deployment and access"
   - "Limitations"
   - "What's new"
2. Each chapter is 2-5 sentences. Never more than 5. Never a wall of text. If you can say it in 2 sentences, say it in 2.
3. Total across all 8 chapters: 400-800 words. Lean short.
4. If the source truly says nothing about a chapter's topic, write one short sentence: "Not disclosed in this document." or "The card does not discuss X." — whichever is accurate. Never omit a chapter.
5. Third person, present tense, neutral tone. No editorializing. No "This is exciting" / "importantly" / "notably".
6. Preserve hedging language verbatim in double quotes when it carries signal: "we believe", "we cannot rule out", "approached our threshold", "elicited harmful", "crossed our threshold", "we decided not to release". Never paraphrase hedges into confident claims.
7. Inline short verbatim quotes (5-30 words) when exact phrasing matters. Wrap in double quotes.
8. Use concrete numbers whenever the source has them: dates, scores, percentages, parameter counts, thresholds.
9. Never invent a fact. If the source doesn't state X, don't include X.
10. Do NOT quote the Table of Contents or changelog entries as safety findings.

## Chapter content guide
- "What this is" — model name, lab, release date, what it supersedes, one-sentence purpose.
- "Capabilities" — top 2-3 benchmark scores with context, modalities, context window.
- "Evaluation methodology" — how they tested (prompting, trials, external evaluators), contamination controls.
- "Safety testing" — red-team scope, catastrophic-risk evals (CBRN / cyber / autonomy), what crossed and what didn't. Preserve hedges verbatim.
- "Mitigations" — deployed safeguards, classifier thresholds, refusal training, access controls, ASL/FSF tier invoked.
- "Deployment and access" — license, API/product surface, restrictions, who gets access.
- "Limitations" — what the lab itself flags as unknown, unsolved, or untested.
- "What's new" — version deltas and changelog entries; if none, say so.

## Output format
Valid JSON only. No prose outside the JSON. No code fences. Exactly 8 chapters.

{
  "chapters": [
    {"title": "What this is", "prose": "2-5 sentences."},
    {"title": "Capabilities", "prose": "..."},
    {"title": "Evaluation methodology", "prose": "..."},
    {"title": "Safety testing", "prose": "..."},
    {"title": "Mitigations", "prose": "..."},
    {"title": "Deployment and access", "prose": "..."},
    {"title": "Limitations", "prose": "..."},
    {"title": "What's new", "prose": "..."}
  ]
}
"""

USER_PROMPT_TEMPLATE = """Source document title: {title}
Publisher: {lab_name}
Version date: {version_date}
Word count: {word_count}

--- SOURCE TEXT BEGINS ---
{content}
--- SOURCE TEXT ENDS ---

Produce the chaptered summary JSON per the system prompt."""

MAX_SOURCE_CHARS = 120_000  # ~30k tokens — safe headroom under Sonnet's window


def truncate_for_context(md: str, max_chars: int = MAX_SOURCE_CHARS) -> str:
    """Keep the front-loaded content where model cards put the most
    summary-relevant material. If the doc is too long, chop mid-appendix."""
    if len(md) <= max_chars:
        return md
    # Try to cut at a sensible boundary (end of paragraph)
    cut = md[:max_chars]
    last_para = cut.rfind("\n\n")
    if last_para > max_chars * 0.8:
        cut = cut[:last_para]
    return cut + "\n\n[... source truncated ...]"


async def generate_one(
    db: AsyncSession,
    doc_id: int,
    title: str,
    lab_name: str,
    version_id: int,
    version_date: str,
    raw_md: str,
    force: bool = False,
    timeout_s: float = 300.0,
) -> dict:
    cleaned = _clean_content(raw_md)
    source_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]

    # Skip if we already have one with matching hash unless --force.
    if not force:
        existing = (await db.execute(text(
            "SELECT id, source_hash FROM document_summaries WHERE document_version_id=:vid"
        ), {"vid": version_id})).fetchone()
        if existing and existing.source_hash == source_hash:
            return {"doc_id": doc_id, "status": "skip_cached"}

    truncated = truncate_for_context(cleaned)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        lab_name=lab_name or "Unknown",
        version_date=version_date,
        word_count=len(cleaned.split()),
        content=truncated,
    )

    t0 = time.time()
    try:
        result = await call_claude_cli(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model="sonnet",
            timeout_s=timeout_s,
            max_budget_usd=2.0,
        )
    except Exception as e:
        await db.execute(text("""
            INSERT INTO document_summaries (document_version_id, source_hash, model_used, chapters, total_words, error)
            VALUES (:vid, :hash, :model, :chapters, 0, :err)
            ON CONFLICT (document_version_id) DO UPDATE
              SET source_hash=:hash, model_used=:model, chapters=:chapters, total_words=0, error=:err, generated_at=NOW()
        """), {
            "vid": version_id, "hash": source_hash, "model": "sonnet",
            "chapters": json.dumps([]), "err": str(e)[:500],
        })
        await db.commit()
        return {"doc_id": doc_id, "status": "error", "error": str(e)[:200]}

    # Parse JSON — tolerate fenced output.
    raw = result.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"doc_id": doc_id, "status": "bad_json", "error": str(e)[:200]}

    chapters = payload.get("chapters", [])
    total_words = sum(len((c.get("prose") or "").split()) for c in chapters)

    await db.execute(text("""
        INSERT INTO document_summaries (document_version_id, source_hash, model_used, chapters, total_words, error)
        VALUES (:vid, :hash, :model, :chapters, :tw, NULL)
        ON CONFLICT (document_version_id) DO UPDATE
          SET source_hash=:hash, model_used=:model, chapters=:chapters, total_words=:tw, error=NULL, generated_at=NOW()
    """), {
        "vid": version_id, "hash": source_hash, "model": "sonnet",
        "chapters": json.dumps(chapters), "tw": total_words,
    })
    await db.commit()

    elapsed = time.time() - t0
    return {
        "doc_id": doc_id, "status": "ok",
        "chapters": len(chapters), "words": total_words,
        "elapsed_s": round(elapsed, 1),
        "tokens_in": result.input_tokens, "tokens_out": result.output_tokens,
    }


async def main(only: int | None, force: bool, parallel: int, retry_errors: bool, timeout_s: float):
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    engine = create_async_engine(dsn, pool_size=parallel + 2)

    async with AsyncSession(engine) as db:
        # Latest version per document.
        q = """
            SELECT DISTINCT ON (d.id)
                d.id AS doc_id, d.title, l.name AS lab_name,
                dv.id AS version_id, dv.version_date::text AS version_date,
                dv.content_md, dv.word_count
            FROM documents d
            JOIN document_versions dv ON dv.document_id = d.id
            LEFT JOIN labs l ON d.lab_id = l.id
            WHERE dv.content_md IS NOT NULL
        """
        params: dict = {}
        if only:
            q += " AND d.id = :only"
            params["only"] = only
        if retry_errors:
            q += """ AND EXISTS (
                SELECT 1 FROM document_summaries ds
                WHERE ds.document_version_id = dv.id
                  AND ds.error IS NOT NULL AND ds.error != ''
            )"""
        q += " ORDER BY d.id, dv.version_date DESC"
        rows = (await db.execute(text(q), params)).fetchall()
        if retry_errors:
            force = True  # retry always overwrites

    print(f"→ {len(rows)} documents to process")
    sem = asyncio.Semaphore(parallel)

    async def worker(row):
        async with sem:
            async with AsyncSession(engine) as db_local:
                return await generate_one(
                    db_local, row.doc_id, row.title, row.lab_name,
                    row.version_id, row.version_date, row.content_md,
                    force=force, timeout_s=timeout_s,
                )

    results = []
    for i, row in enumerate(rows, 1):
        pass  # placeholder to let gather work below
    results = await asyncio.gather(*(worker(r) for r in rows))

    # Summarize run
    ok = sum(1 for r in results if r["status"] == "ok")
    skip = sum(1 for r in results if r["status"] == "skip_cached")
    err = sum(1 for r in results if r["status"] not in ("ok", "skip_cached"))
    total_words = sum(r.get("words", 0) for r in results if r["status"] == "ok")
    total_tokens_in = sum(r.get("tokens_in", 0) for r in results if r["status"] == "ok")
    total_tokens_out = sum(r.get("tokens_out", 0) for r in results if r["status"] == "ok")

    print()
    print(f"✓ {ok} generated  · {skip} skipped (cached)  · {err} errors")
    print(f"  total words: {total_words:,}  ·  tokens in/out: {total_tokens_in:,} / {total_tokens_out:,}")
    if err:
        print("  Errors:")
        for r in results:
            if r["status"] not in ("ok", "skip_cached"):
                print(f"    doc {r['doc_id']}: {r['status']} — {r.get('error', '')[:150]}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--only", type=int, help="Run for only this document id")
    p.add_argument("--force", action="store_true", help="Regenerate even if cached")
    p.add_argument("--parallel", type=int, default=3, help="How many Claude calls in parallel")
    p.add_argument("--retry-errors", action="store_true", help="Only retry rows with a stored error")
    p.add_argument("--timeout", type=float, default=300.0, help="Claude CLI timeout seconds")
    args = p.parse_args()
    asyncio.run(main(args.only, args.force, args.parallel, args.retry_errors, args.timeout))
