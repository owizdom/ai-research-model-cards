"""Extract structured eval/benchmark data from model card markdown using LLM."""
import json
import os
import re
import traceback
from datetime import datetime, timezone

import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "groq/llama-3.3-70b-versatile")

EXTRACTION_SYSTEM_PROMPT = """You are a precise data extraction assistant. Your task is to extract ALL benchmark/evaluation results from a model card or technical report.

For each benchmark result found, extract:
- benchmark_name: The exact benchmark name (e.g., "MMLU", "HumanEval", "GSM8K")
- score: The numerical score as a float
- variant: Any variant info like shot count or method (e.g., "5-shot", "CoT", "0-shot", "pass@1"). Use "default" if none specified.
- metric: The metric type if mentioned (e.g., "accuracy", "pass@1", "elo")
- model_name: Which specific model the score belongs to (e.g., "Claude 3.5 Sonnet", "GPT-4o")
- context: Brief surrounding text for verification (max 80 chars)

Return a JSON object with a "results" key containing an array. If no benchmarks are found, return {"results": []}.
Do NOT hallucinate scores. Only extract scores explicitly stated in the text.
Extract scores for ALL models mentioned (the primary model and comparison models).

Example output:
{"results": [
  {"benchmark_name": "MMLU", "score": 86.8, "variant": "5-shot", "metric": "accuracy", "model_name": "Claude 3.5 Sonnet", "context": "Claude 3.5 Sonnet achieves 86.8% on MMLU"},
  {"benchmark_name": "HumanEval", "score": 92.0, "variant": "pass@1", "metric": "pass@1", "model_name": "Claude 3.5 Sonnet", "context": "92.0% pass@1 on HumanEval"}
]}"""

EXTRACTION_USER_PROMPT = """Extract all benchmark/evaluation results from this model card content. Return ONLY the JSON object with a "results" key.

MODEL CARD CONTENT:
{content}"""


def _slugify(name: str) -> str:
    """Convert a benchmark name to a slug."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


async def extract_evals_from_version(version_id: int, SessionLocal=None) -> int:
    """Extract evals from a document version. Returns count of evals extracted."""
    if SessionLocal is None:
        from packages.db.session import AsyncSessionLocal
        SessionLocal = AsyncSessionLocal

    from packages.db.models import DocumentVersion, BenchmarkDefinition, EvalResult, ExtractionRun

    async with SessionLocal() as db:
        version = await db.get(DocumentVersion, version_id)
        if not version or not version.content_md:
            return 0

        # Check if already extracted
        existing = await db.execute(
            select(ExtractionRun).where(
                ExtractionRun.document_version_id == version_id,
                ExtractionRun.status == "completed",
            )
        )
        if existing.scalar_one_or_none():
            return 0

        # Create extraction run
        run = ExtractionRun(
            document_version_id=version_id,
            model_used=EXTRACTION_MODEL,
            status="running",
        )
        db.add(run)
        await db.flush()

        try:
            content = version.content_md[:16000]

            response = await litellm.acompletion(
                model=EXTRACTION_MODEL,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": EXTRACTION_USER_PROMPT.format(content=content)},
                ],
                max_tokens=4096,
                temperature=0.0,
            )

            raw_output = response.choices[0].message.content or "[]"
            run.raw_output = raw_output

            # Parse results — handle both {"results": [...]} and bare [...]
            try:
                parsed = json.loads(raw_output)
            except json.JSONDecodeError:
                # Try extracting JSON from markdown code block
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_output)
                if match:
                    parsed = json.loads(match.group(1))
                else:
                    parsed = {"results": []}

            if isinstance(parsed, dict) and "results" in parsed:
                items = parsed["results"]
            elif isinstance(parsed, list):
                items = parsed
            else:
                items = []

            # Load benchmark lookup
            benchmarks = await _load_benchmark_lookup(db)

            count = 0
            for item in items:
                benchmark_name = item.get("benchmark_name", "").strip()
                score = item.get("score")
                if not benchmark_name or score is None:
                    continue

                try:
                    score = float(score)
                except (ValueError, TypeError):
                    continue

                benchmark_id = _match_benchmark(benchmark_name, benchmarks)
                if not benchmark_id:
                    benchmark_id = await _create_benchmark(db, benchmark_name, item)
                    benchmarks = await _load_benchmark_lookup(db)

                variant = (item.get("variant") or "default").strip()

                # Check for duplicate
                existing_eval = await db.execute(
                    select(EvalResult).where(
                        EvalResult.document_version_id == version_id,
                        EvalResult.benchmark_id == benchmark_id,
                        EvalResult.variant == variant,
                    )
                )
                if existing_eval.scalar_one_or_none():
                    continue

                eval_result = EvalResult(
                    document_version_id=version_id,
                    benchmark_id=benchmark_id,
                    score=score,
                    variant=variant,
                    score_details={
                        "raw_text": item.get("context", ""),
                        "metric": item.get("metric", ""),
                        "model_name": item.get("model_name", ""),
                    },
                    extraction_confidence=0.85,
                    is_self_reported=True,
                    source_type="model_card",
                )
                db.add(eval_result)
                count += 1

            run.status = "completed"
            run.evals_extracted = count
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            print(f"[extractor] extracted {count} evals from version {version_id}", flush=True)
            return count

        except Exception as e:
            run.status = "failed"
            run.error = str(e)[:1000]
            await db.commit()
            print(f"[extractor] failed for version {version_id}: {e}", flush=True)
            traceback.print_exc()
            return 0


async def _load_benchmark_lookup(db: AsyncSession) -> dict:
    """Load all benchmarks into a lookup dict keyed by slug and aliases."""
    from packages.db.models import BenchmarkDefinition

    result = await db.execute(select(BenchmarkDefinition))
    benchmarks = result.scalars().all()

    lookup = {}
    for b in benchmarks:
        lookup[b.slug.lower()] = b.id
        lookup[b.name.lower()] = b.id
        if b.aliases:
            for alias in b.aliases:
                lookup[alias.lower()] = b.id
    return lookup


def _match_benchmark(name: str, lookup: dict) -> int | None:
    """Fuzzy-match a benchmark name to a known definition ID."""
    key = name.lower().strip()
    if key in lookup:
        return lookup[key]

    # Try slugified version
    slug = _slugify(name)
    if slug in lookup:
        return lookup[slug]

    # Try partial match
    for known, bid in lookup.items():
        if key in known or known in key:
            return bid

    return None


async def _create_benchmark(db: AsyncSession, name: str, item: dict) -> int:
    """Create a new BenchmarkDefinition for an unknown benchmark."""
    from packages.db.models import BenchmarkDefinition

    slug = _slugify(name)
    # Check it doesn't already exist
    existing = await db.execute(
        select(BenchmarkDefinition).where(BenchmarkDefinition.slug == slug)
    )
    if row := existing.scalar_one_or_none():
        return row.id

    benchmark = BenchmarkDefinition(
        slug=slug,
        name=name,
        category="other",
        metric_name=item.get("metric"),
        higher_is_better=True,
    )
    db.add(benchmark)
    await db.flush()
    return benchmark.id
