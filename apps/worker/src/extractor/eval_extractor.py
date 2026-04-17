"""Extract structured eval/benchmark data from model card markdown using LLM."""
import asyncio
import json
import os
import re
import traceback
from datetime import datetime, timezone

import litellm
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .claude_cli import call_claude_cli
from .parse import parse_extraction_json as _parse_extraction_json

EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "sonnet")

CLAUDE_PREFIXES = ("claude", "sonnet", "opus", "haiku", "anthropic/")


def _is_claude_model(model: str) -> bool:
    m = model.lower()
    return any(m.startswith(p) for p in CLAUDE_PREFIXES)


def _normalize_claude_model(model: str) -> str:
    """Map full Anthropic model IDs to claude CLI short names."""
    m = model.lower().removeprefix("anthropic/")
    if "opus" in m:
        return "opus"
    if "haiku" in m:
        return "haiku"
    return "sonnet"  # default for any sonnet variant or bare "claude"


async def _llm_complete(system: str, user: str, model: str) -> str:
    """Provider-agnostic completion. Routes Claude through the CLI subprocess
    (because the Messages API rejects OAuth tokens) and everything else
    through litellm."""
    if _is_claude_model(model):
        result = await call_claude_cli(system, user, model=_normalize_claude_model(model))
        return result.content
    response = await litellm.acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=4096,
        temperature=0.0,
    )
    return response.choices[0].message.content or "[]"

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


def _extract_eval_sections(content: str, max_chars: int = 30000) -> str:
    """Scan full document for sections likely containing benchmark results.

    Increased from 14k to 30k chars and 20→40 line blocks to improve recall
    on dense comparison tables (audit showed 48% recall at the old settings).
    """
    lines = content.split("\n")
    scored_blocks: list[tuple[int, int, str]] = []

    block_size = 40
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
        # Serialize concurrent extract jobs for the same version_id via a
        # Postgres advisory lock scoped to this transaction. Different
        # version_ids hash to different keys and do not block each other.
        # Held for the duration of the LLM call — intentional: the point is
        # that a second caller must wait for the first to finish (or fail)
        # before deciding whether to re-run. Released on commit/rollback.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"extract:{version_id}"},
        )

        version = await db.get(DocumentVersion, version_id)
        if not version or not version.content_md:
            return 0

        # Skip only if an earlier completed run actually produced results.
        # A completed run with 0 evals is a failure mode (e.g. malformed LLM
        # output, parser fallback) that should be retried, not treated as done.
        existing = await db.execute(
            select(ExtractionRun).where(
                ExtractionRun.document_version_id == version_id,
                ExtractionRun.status == "completed",
                ExtractionRun.evals_extracted > 0,
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
            content = sections if sections else version.content_md[:30000]

            # Retry with backoff on rate limits
            response_text = None
            for attempt in range(4):
                try:
                    response_text = await _llm_complete(
                        EXTRACTION_SYSTEM_PROMPT,
                        EXTRACTION_USER_PROMPT.format(content=content),
                        EXTRACTION_MODEL,
                    )
                    break
                except Exception as e:
                    err = str(e).lower()
                    if any(s in err for s in ("rate", "429", "quota", "budget", "5h", "usage limit")):
                        wait = 30 * (attempt + 1)
                        print(f"[extractor] rate limited on v{version_id}, waiting {wait}s (attempt {attempt+1}/4)", flush=True)
                        await asyncio.sleep(wait)
                        if attempt == 3:
                            raise
                    else:
                        raise

            if response_text is None:
                raise RuntimeError("No response from LLM after retries")

            raw_output = response_text
            run.raw_output = raw_output

            parsed = _parse_extraction_json(raw_output)

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

                # Reject scores outside the benchmark's declared range.
                # Claude occasionally hallucinates numbers ("MMLU: 150") — when
                # the ontology defines a range, enforce it. Benchmarks without
                # a range pass through untouched.
                if not await _score_in_range(db, benchmark_id, score):
                    continue

                variant = (item.get("variant") or "default").strip()
                model_name = (item.get("model_name") or "").strip() or None

                # Dedup on the full uniqueness key (document_version_id,
                # generation_id, benchmark_id, variant, model_name) — matches
                # the DB uq_eval_result constraint. Papers that report a
                # benchmark for multiple sizes (e.g. Llama 3.1 8B/70B/405B)
                # correctly land as distinct rows because model_name differs.
                existing_eval = await db.execute(
                    select(EvalResult).where(
                        EvalResult.document_version_id == version_id,
                        EvalResult.benchmark_id == benchmark_id,
                        EvalResult.variant == variant,
                        EvalResult.model_name == model_name,
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
                    model_name=model_name,
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


async def _score_in_range(db: AsyncSession, benchmark_id: int, score: float) -> bool:
    """Return False if the score is outside the benchmark's declared range.

    Benchmarks without a range (score_min/score_max NULL) always pass.
    """
    from packages.db.models import BenchmarkDefinition
    b = await db.get(BenchmarkDefinition, benchmark_id)
    if b is None or b.score_min is None or b.score_max is None:
        return True
    # Small tolerance for rounding (e.g. score_max 100 but Claude emits 100.01)
    eps = 1e-3
    if score < b.score_min - eps or score > b.score_max + eps:
        print(
            f"[extractor] rejecting out-of-range score {score} for {b.slug} "
            f"(expected [{b.score_min}, {b.score_max}])",
            flush=True,
        )
        return False
    return True


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
