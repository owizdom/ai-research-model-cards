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

SYSTEM_PROMPT = """You are a neutral research summarizer producing chaptered briefs of AI model cards.

Your output is consumed by researchers who need a faithful, concise rendering of what the lab claims — not what the reader hopes or worries about.

Rules:
1. Total length: 1500-2000 words across all chapters combined.
2. Output 5-8 chapters. Each chapter is 200-350 words of flowing prose (not bullet points).
3. Write in third person, present tense, neutral tone. Never editorialize.
4. Preserve the lab's hedging language verbatim inside double quotes when it carries signal — phrases like "we believe", "we cannot rule out", "approached our threshold", "elicited harmful", "crossed our threshold", "we decided not to release", "limitations include". Do NOT paraphrase hedges into confident claims.
5. Inline short verbatim quotes (5-40 words) sparingly when the exact phrasing matters (thresholds, refusals, policy commitments, safety findings). Wrap them in double quotes.
6. Use concrete numbers whenever the source provides them: dates, scores, percentages, parameter counts, token counts, threshold levels.
7. Never invent a fact. If the source doesn't state X, don't include X. If a chapter has no source material, omit the chapter entirely.
8. Do NOT quote the Table of Contents or changelog entries as safety findings.

Chapters (include only those with source material, in this order):
- "What this is" — model name, lab, release date, version deltas vs predecessor, the single-sentence purpose
- "Capabilities" — what the model can do, headline benchmark scores in context, modalities, context window
- "Evaluation methodology" — how the lab tested capabilities; any contamination controls, prompting regimes, elicitation notes
- "Safety testing" — red-team process, catastrophic-risk evals (CBRN, cyber, autonomy), what crossed and what did not; preserve hedging language
- "Mitigations" — deployed safeguards, classifier thresholds, refusal training, access controls
- "Deployment and access" — license, API/product surface, restrictions, availability, who gets access
- "Limitations" — what the lab itself flags as unknown, unsolved, or explicitly untested
- "What's new" — version deltas and changelog entries if present

Output format — valid JSON only, no prose outside the JSON, no code fences:
{
  "chapters": [
    {"title": "What this is", "prose": "200-350 words of flowing prose..."},
    {"title": "Capabilities", "prose": "..."},
    ...
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
            timeout_s=300,
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


async def main(only: int | None, force: bool, parallel: int):
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
        q += " ORDER BY d.id, dv.version_date DESC"
        rows = (await db.execute(text(q), params)).fetchall()

    print(f"→ {len(rows)} documents to process")
    sem = asyncio.Semaphore(parallel)

    async def worker(row):
        async with sem:
            async with AsyncSession(engine) as db_local:
                return await generate_one(
                    db_local, row.doc_id, row.title, row.lab_name,
                    row.version_id, row.version_date, row.content_md,
                    force=force,
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
    args = p.parse_args()
    asyncio.run(main(args.only, args.force, args.parallel))
