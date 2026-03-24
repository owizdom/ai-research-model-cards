"""Extract structured eval/benchmark data from model card markdown using LLM."""
import asyncio
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

EVAL_KEYWORDS = [
    "benchmark", "evaluation", "mmlu", "humaneval", "gsm8k", "accuracy",
    "performance", "results", "score", "pass@", "elo", "compared to",
    "safety eval", "red team", "capability", "gpqa", "swe-bench", "math",
    "hellaswag", "winogrande", "truthfulqa", "aime", "ifeval", "mbpp",
    "coding", "reasoning", "table", "figure", "f1", "precision", "recall",
    "toxicity", "bias", "refusal", "harmful", "drop", "arc-challenge",
    "mgsm", "mmmu", "multilingual", "vision", "instruction following",
]


def _extract_eval_sections(content: str, max_chars: int = 14000) -> str:
    """Scan full document for sections likely containing benchmark results."""
    lines = content.split("\n")
    scored_blocks: list[tuple[int, int, str]] = []

    block_size = 20
    for i in range(0, len(lines), block_size // 2):
        block = "\n".join(lines[i : i + block_size])
        block_lower = block.lower()
        score = sum(1 for kw in EVAL_KEYWORDS if kw in block_lower)
        if score > 0:
            scored_blocks.append((score, i, block))

    scored_blocks.sort(key=lambda x: -x[0])

    selected: list[tuple[int, str]] = []
    total = 0
    seen_indices: set[int] = set()
    for score, idx, block in scored_blocks:
        if idx in seen_indices:
            continue
        if total + len(block) > max_chars:
            break
        selected.append((idx, block))
        seen_indices.add(idx)
        total += len(block)

    if not selected:
        return ""

    selected.sort(key=lambda x: x[0])
    return "\n\n---\n\n".join(b for _, b in selected)


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


async def extract_evals_from_version(version_id: int, SessionLocal=None) -> int:
    """Extract evals from a document version. Returns count of evals extracted."""
    if SessionLocal is None:
        from packages.db.session import AsyncSessionLocal
        SessionLocal = AsyncSessionLocal

    from packages.db.models import (
        DocumentVersion, Document, BenchmarkDefinition,
        EvalResult, ExtractionRun, ModelGeneration,
    )

    async with SessionLocal() as db:
        version = await db.get(DocumentVersion, version_id)
        if not version or not version.content_md:
            return 0

        # Check if already extracted successfully
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
            # Smart section extraction — find eval-dense sections across full doc
            sections = _extract_eval_sections(version.content_md)
            content = sections if sections else version.content_md[:16000]

            # Retry with backoff on rate limits
            response = None
            for attempt in range(4):
                try:
                    response = await litellm.acompletion(
                        model=EXTRACTION_MODEL,
                        messages=[
                            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                            {"role": "user", "content": EXTRACTION_USER_PROMPT.format(content=content)},
                        ],
                        max_tokens=4096,
                        temperature=0.0,
                    )
                    break
                except Exception as e:
                    err = str(e).lower()
                    if "rate" in err or "429" in err or "quota" in err:
                        wait = 30 * (attempt + 1)
                        print(f"[extractor] rate limited on v{version_id}, waiting {wait}s (attempt {attempt+1}/4)", flush=True)
                        await asyncio.sleep(wait)
                        if attempt == 3:
                            raise
                    else:
                        raise

            if not response:
                raise RuntimeError("No response from LLM after retries")

            raw_output = response.choices[0].message.content or "[]"
            run.raw_output = raw_output

            # Parse results
            try:
                parsed = json.loads(raw_output)
            except json.JSONDecodeError:
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

            # Look up the generation linked to this document
            doc = await db.get(Document, version.document_id)
            generation_id = None
            if doc:
                gen_result = await db.execute(
                    select(ModelGeneration).where(ModelGeneration.document_id == doc.id)
                )
                gen = gen_result.scalar_one_or_none()
                if gen:
                    generation_id = gen.id

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
                    generation_id=generation_id,
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
            print(f"[extractor] extracted {count} evals from version {version_id} (gen={generation_id})", flush=True)
            return count

        except Exception as e:
            run.status = "failed"
            run.error = str(e)[:1000]
            await db.commit()
            print(f"[extractor] failed for version {version_id}: {e}", flush=True)
            traceback.print_exc()
            return 0


async def _load_benchmark_lookup(db: AsyncSession) -> dict:
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
    key = name.lower().strip()
    if key in lookup:
        return lookup[key]
    slug = _slugify(name)
    if slug in lookup:
        return lookup[slug]
    for known, bid in lookup.items():
        if key in known or known in key:
            return bid
    return None


async def _create_benchmark(db: AsyncSession, name: str, item: dict) -> int:
    from packages.db.models import BenchmarkDefinition
    slug = _slugify(name)
    existing = await db.execute(
        select(BenchmarkDefinition).where(BenchmarkDefinition.slug == slug)
    )
    if row := existing.scalar_one_or_none():
        return row.id
    benchmark = BenchmarkDefinition(
        slug=slug, name=name, category="other",
        metric_name=item.get("metric"), higher_is_better=True,
    )
    db.add(benchmark)
    await db.flush()
    return benchmark.id
