"""Extract structured eval/benchmark data from model card markdown using LLM."""
from __future__ import annotations

import asyncio
import json
import os
import re
import traceback
from datetime import datetime, timezone

import litellm
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.pipeline_config import (
    ANCHOR_BOOST,
    CLI_RETRY_ATTEMPTS,
    CLI_RETRY_BASE_BACKOFF_S,
    EXTRACTION_PROTOCOL_VERSION,
    LONG_DOC_THRESHOLD,
    WINDOW_SIZE_DEFAULT,
)

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


EXTRACTION_SYSTEM_PROMPT = """You are a precise data extraction assistant. Extract EVERY benchmark/evaluation reference from a model card or technical report, regardless of whether it was actually run.

For each benchmark reference, emit an object with these fields:

- benchmark_name (TEXT, required): the canonical benchmark name with NO subset suffix, e.g. "MMLU" (not "MMLU-Pro"), "SWE-bench" (not "SWE-bench Verified"), "GPQA" (not "GPQA Diamond"). Put the subset in `split` instead.
- score (FLOAT | null): the numerical score. null if state != "scored".
- state (TEXT, required, one of): "scored" | "mentioned" | "cited".
- shot_count (INT | null): 0 for zero-shot, 5 for 5-shot, etc. null if not stated.
- method (TEXT | null): evaluation methodology. Allowed: "CoT", "self-consistency", "RAG", "extended-thinking", "majority-voting", "with-tools", "no-tools", "pre-mitigation", "post-mitigation", "without-mitigations", "without-safeguards", "none". null if unspecified.
- language (TEXT | null): for multilingual benchmarks, the evaluation language or "Average". "English" if explicitly English-only. null if not applicable.
- training_state (TEXT | null): "pretrained", "instruction-tuned", "RLHF", "base", or "unknown". null if paper does not indicate.
- split (TEXT | null): sub-task or subset WITHIN the benchmark — read from prose context, table headers, OR surrounding section titles. Examples: "verified" (SWE-bench Verified), "diamond" (GPQA Diamond), "pro" (MMLU-Pro), "500" (MATH-500), "ambiguous"/"disambiguated" (BBQ), "magnification"/"acquisition"/"ideation"/"formulation"/"release" (OpenAI biorisk sub-tasks), "biology"/"physics"/"chemistry" (GPQA), "2024"/"2026" (year-anchored Olympiad). Lowercase, snake-case-ish. null if no subset/sub-task is identifiable.
- metric_path (TEXT | null): the scoring rule applied. Examples: "accuracy", "pass_at_1", "pass_at_10", "cot_correct" (chain-of-thought scoring distinct from raw accuracy), "win_rate", "f1", "exact_match", "resolve_rate" (SWE-bench native), "elo". null if not explicitly stated. KEY: a single benchmark can be reported under multiple metric_paths in the same card — emit a row for each.
- model_name (TEXT | null): the specific model this row refers to, e.g. "Claude 3.5 Sonnet", "GPT-4o", "Llama 3.1 70B". null only for generic "cited" rows.
- context (TEXT, required, max 300 chars): surrounding text WITH the model name, benchmark name, and score all included when possible. This is the evidence snippet for downstream audit — if you only include the table caption, the extraction is not self-verifiable. When extracting from tables, include the header row + the specific data row. When extracting from prose, include the full sentence.

STATE RULES (critical distinction):

1) "scored" = document contains an EXPLICIT NUMERIC value for this model on this benchmark. Table cells, figure annotations, inline claims like "86.8%", "0.742 F1", "pass@1 of 92.0".
2) "mentioned" = benchmark discussed in PROSE as something authors evaluated/plan-to/declined-to — but NO number attached here. E.g. "We also tested on X but results are forthcoming", "X is left to future work".
3) "cited" = benchmark appears ONLY as a reference marker, bibliography entry, or methodological pointer WITHOUT being the subject of evaluative discussion. E.g. bare "[Hendrycks et al. 2021]".

Disambiguation heuristic:
- Is there a number? → scored.
- Is the benchmark the subject of a sentence about THIS model's evaluation? → mentioned.
- Otherwise → cited.

Priority when same (benchmark, model) appears in multiple states: scored > mentioned > cited. Emit only the highest.

OUTPUT RULES:
- Return {"results": [...]}. No prose, no markdown fences.
- One row per (model_name, benchmark_name, variant) tuple.
- For "cited" rows without model attribution, set model_name=null.
- Do NOT hallucinate scores. If no number, emit state="mentioned" or "cited" with score=null.
- Extract rows for ALL models in comparison tables.
- Normalize: "5-shot"→5, "zero-shot"/"0-shot"→0, "few-shot" w/o number→null. "chain-of-thought"→"CoT", "extended thinking"→"extended-thinking".
- If no benchmarks present, return {"results": []}.

EXAMPLES:
- "MMLU (5-shot) | 88.7" → {"benchmark_name":"MMLU","score":88.7,"state":"scored","shot_count":5,"method":"none","split":null,"metric_path":"accuracy","metric":"accuracy",...}
- "MMLU-Pro CoT correct | 84.2" → {"benchmark_name":"MMLU","score":84.2,"state":"scored","split":"pro","method":"CoT","metric_path":"cot_correct","metric":"accuracy",...} — note benchmark_name is MMLU, "pro" is the split.
- "SWE-bench Verified resolve rate: 72.5%" → {"benchmark_name":"SWE-bench","score":72.5,"split":"verified","metric_path":"resolve_rate","metric":"resolve_rate",...}
- "GPQA Diamond accuracy: 84.2" → {"benchmark_name":"GPQA","score":84.2,"split":"diamond","metric_path":"accuracy",...}
- "Long-form biological-risk questions, Magnification, pre-mitigation: 59.0" → {"benchmark_name":"long_form_biological_risk_questions","split":"magnification","method":"pre-mitigation",...}
- "HumanEval pass@10: 95.2" → {"benchmark_name":"HumanEval","score":95.2,"split":null,"metric_path":"pass_at_10",...}
- "We also ran preliminary evaluations on MMLU-Pro; full results forthcoming." → {"benchmark_name":"MMLU","split":"pro","score":null,"state":"mentioned",...}
- "Prior work includes BIG-Bench [Srivastava 2022]" → {"benchmark_name":"BIG-Bench","score":null,"state":"cited","model_name":null,...}
- "On MGSM avg: 91.6; Swahili: 83.4" → emit two rows with language="Average" and language="Swahili".

SPLIT GUIDANCE — read prose context, not just table headers:
- If the section heading says "SWE-bench Verified Results" and every cell underneath is a SWE-bench number, set split="verified" on every row from that table even if the cell header doesn't repeat "Verified".
- If a card has separate "MMLU" and "MMLU-Pro" tables, emit benchmark_name="MMLU" for both and use split=null vs split="pro" to distinguish.
- Mitigation tables (OpenAI-style) typically alternate pre-/post-mitigation columns under a single benchmark name. Read the column header for the mitigation state and put it in `method`.
"""

EXTRACTION_USER_PROMPT = """Extract every benchmark/evaluation reference (scored, mentioned, or cited) from the model card content below. Return ONLY the JSON object with a "results" key.

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

# Strong anchors for canonical capability tables. A block containing any of
# these gets a big score bonus, which guarantees the comparison table beats
# out keyword-dense narrative (e.g. CBRN safety prose in long Anthropic cards).
# The 232-page Opus 4.7 card put its capability summary at char 368k, past
# the 30k extraction window, because the safety section was keyword-denser —
# these anchors fix that without growing the window.
CAPABILITY_ANCHORS = [
    "capability evaluation summary",
    "benchmark results",
    "performance overview",
    "swe-bench verified",
    "gpqa diamond",
    "mmlu-pro",
    "humaneval+",
    "livecodebench",
    "evaluation summary",
]

# Numbered section headers like "8.1 Capability evaluation summary",
# "## 5 Capabilities", or "8 Capability" — common in Anthropic/OpenAI
# system cards. Match the singular "capability" AND the plural; same for
# "benchmark/benchmarks", "evaluation/evaluations".
_SECTION_HEADER_RE = re.compile(
    r"^(?:#+\s*)?\d+(?:\.\d+)*\s+"
    r"(reasoning|coding|math|safety|capability|capabilities|"
    r"benchmark|benchmarks|evaluation|evaluations|performance)\b",
    re.IGNORECASE | re.MULTILINE,
)

# ANCHOR_BOOST and LONG_DOC_THRESHOLD live in packages/pipeline_config.


def _score_block(block: str) -> int:
    """Score a block by EVAL_KEYWORDS density plus capability-anchor bonus."""
    block_lower = block.lower()
    score = sum(1 for kw in EVAL_KEYWORDS if kw in block_lower)
    for anchor in CAPABILITY_ANCHORS:
        if anchor in block_lower:
            score += ANCHOR_BOOST
    if _SECTION_HEADER_RE.search(block):
        score += ANCHOR_BOOST
    return score


def _select_top_blocks(lines: list[str], char_budget: int, line_offset: int = 0):
    """Score 40-line blocks in `lines`, return non-overlapping top picks up to
    `char_budget` chars. Returns list of (original_line_index, block_text).
    line_offset is added to indices so callers can stitch multiple ranges.
    """
    block_size = 40
    scored = []
    for i in range(0, len(lines), block_size // 2):
        block = "\n".join(lines[i : i + block_size])
        s = _score_block(block)
        if s > 0:
            scored.append((s, i + line_offset, block))
    scored.sort(key=lambda x: -x[0])

    selected = []
    total = 0
    seen = set()
    for s, idx, block in scored:
        if idx in seen:
            continue
        if total + len(block) > char_budget:
            break
        selected.append((idx, block))
        seen.add(idx)
        total += len(block)
    return selected


def _extract_eval_sections(content: str, max_chars: int = WINDOW_SIZE_DEFAULT) -> str:
    """Scan full document for sections likely containing benchmark results.

    Two-window split for long docs (>80k chars): allocate half the budget to
    the first half of the doc and half to the second half. This catches both
    early-doc methodology/safety content AND late-doc capability tables
    (which can sit at char 350k+ in long system cards).
    """
    lines = content.split("\n")

    if len(content) > LONG_DOC_THRESHOLD:
        half = len(lines) // 2
        front = _select_top_blocks(lines[:half], max_chars // 2, line_offset=0)
        back = _select_top_blocks(lines[half:], max_chars // 2, line_offset=half)
        selected = front + back
    else:
        selected = _select_top_blocks(lines, max_chars, line_offset=0)

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

        # Skip only if we already have eval_results at the CURRENT protocol
        # version for this doc. Sprint-1 (protocol 1) rows don't block a
        # Sprint-2 (protocol 2) re-extraction — they coexist so the UI can
        # filter between them. A completed run with 0 evals at the current
        # protocol is a failure mode that should be retried, not treated
        # as done.
        existing_v2 = await db.execute(
            select(EvalResult).where(
                EvalResult.document_version_id == version_id,
                EvalResult.extraction_protocol_version == EXTRACTION_PROTOCOL_VERSION,
            ).limit(1)
        )
        if existing_v2.scalar_one_or_none():
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
            content = sections if sections else version.content_md[:WINDOW_SIZE_DEFAULT]

            # Retry with backoff on rate limits
            response_text = None
            for attempt in range(CLI_RETRY_ATTEMPTS):
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
                        wait = CLI_RETRY_BASE_BACKOFF_S * (attempt + 1)
                        print(f"[extractor] rate limited on v{version_id}, waiting {wait}s (attempt {attempt+1}/{CLI_RETRY_ATTEMPTS})", flush=True)
                        await asyncio.sleep(wait)
                        if attempt == CLI_RETRY_ATTEMPTS - 1:
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
            skipped_dup = 0
            for item in items:
                benchmark_name = item.get("benchmark_name", "").strip()
                if not benchmark_name:
                    continue

                state = (item.get("state") or "scored").strip().lower()
                if state not in ("scored", "mentioned", "cited"):
                    state = "scored" if item.get("score") is not None else "mentioned"

                raw_score = item.get("score")
                score: float | None = None
                if state == "scored":
                    if raw_score is None:
                        continue  # scored rows must have a number
                    try:
                        score = float(raw_score)
                    except (ValueError, TypeError):
                        continue

                benchmark_id = _match_benchmark(benchmark_name, benchmarks)
                if not benchmark_id:
                    benchmark_id = await _create_benchmark(db, benchmark_name, item)
                    benchmarks = await _load_benchmark_lookup(db)

                if score is not None and not await _score_in_range(db, benchmark_id, score):
                    continue

                # Compose a variant string for backwards-compat + DB uniqueness.
                # Structured fields (shot_count, method, language, training_state)
                # are stored in their own columns; `variant` is the legacy
                # composite key used by the existing uq_eval_result constraint.
                shot_count = item.get("shot_count")
                method = (item.get("method") or "").strip().lower() or None
                language = (item.get("language") or "").strip() or None
                training_state = (item.get("training_state") or "").strip().lower() or None
                model_name = (item.get("model_name") or "").strip() or None
                # v3 (Phase 5b): split and metric_path are first-class fields,
                # read from prose context by the extractor itself.
                split = (item.get("split") or "").strip().lower() or None
                metric_path = (item.get("metric_path") or "").strip().lower() or None

                legacy_variant_parts = []
                if shot_count is not None:
                    legacy_variant_parts.append(f"{shot_count}-shot")
                if method and method != "none":
                    legacy_variant_parts.append(method)
                if language and language != "English":
                    legacy_variant_parts.append(language)
                if training_state and training_state != "unknown":
                    legacy_variant_parts.append(training_state)
                if split:
                    legacy_variant_parts.append(split)
                if metric_path:
                    legacy_variant_parts.append(metric_path)
                variant = ", ".join(legacy_variant_parts) if legacy_variant_parts else "default"

                # Idempotent insert via ON CONFLICT DO NOTHING — handles concurrent
                # extractions, retried jobs, and duplicate rows from the same model
                # output without rolling back the whole transaction. Returns the
                # new id, or None if the conflict was suppressed.
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                ins = pg_insert(EvalResult).values(
                    document_version_id=version_id,
                    benchmark_id=benchmark_id,
                    generation_id=generation_id,
                    score=score,
                    variant=variant,
                    model_name=model_name,
                    state=state,
                    shot_count=shot_count if isinstance(shot_count, int) else None,
                    method=method,
                    language=language,
                    training_state=training_state,
                    split=split,
                    metric_path=metric_path,
                    extraction_protocol_version=EXTRACTION_PROTOCOL_VERSION,
                    score_details={
                        "raw_text": item.get("context", ""),
                        "metric": item.get("metric", ""),
                        "model_name": item.get("model_name", ""),
                    },
                    extraction_confidence=0.85,
                    is_self_reported=True,
                    source_type="model_card",
                ).on_conflict_do_nothing(constraint="uq_eval_result").returning(EvalResult.id)
                ins_result = await db.execute(ins)
                if ins_result.first():
                    count += 1
                else:
                    skipped_dup += 1

            run.status = "completed"
            run.evals_extracted = count
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            print(f"[extractor] extracted {count} evals (skipped {skipped_dup} dup) from version {version_id} (gen={generation_id})", flush=True)
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


def _normalize_bench_key(s: str) -> str:
    """Aggressive normalization for benchmark-name matching.

    Collapses spacing, punctuation, and case so that "BIG-Bench Hard",
    "big_bench_hard", "BigBenchHard", and "bigbench-hard" all reduce to
    the same key. Eliminates the primary driver of benchmark_definitions
    bloat (Claude-emitted spelling variants landing as new rows).
    """
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


async def _load_benchmark_lookup(db: AsyncSession) -> dict:
    from packages.db.models import BenchmarkDefinition
    result = await db.execute(select(BenchmarkDefinition))
    benchmarks = result.scalars().all()
    lookup = {}
    for b in benchmarks:
        # Keep both literal-lowercase and aggressive-normalized entries so
        # the fast path stays fast and we still catch spelling variants.
        lookup[b.slug.lower()] = b.id
        lookup[b.name.lower()] = b.id
        lookup[_normalize_bench_key(b.slug)] = b.id
        lookup[_normalize_bench_key(b.name)] = b.id
        if b.aliases:
            for alias in b.aliases:
                lookup[alias.lower()] = b.id
                lookup[_normalize_bench_key(alias)] = b.id
    return lookup


def _match_benchmark(name: str, lookup: dict) -> int | None:
    key = name.lower().strip()
    if key in lookup:
        return lookup[key]
    slug = _slugify(name)
    if slug in lookup:
        return lookup[slug]
    # Normalized fallback catches variants like "BIG-Bench Hard" vs
    # "big_bench_hard" that literal matching misses.
    norm = _normalize_bench_key(name)
    if norm and norm in lookup:
        return lookup[norm]
    return None


async def _create_benchmark(db: AsyncSession, name: str, item: dict) -> int:
    """Idempotent benchmark upsert. If the slug already exists (from a prior
    extraction of any doc), reuse its id rather than raising UniqueViolationError
    and rolling back the whole eval transaction.
    """
    from packages.db.models import BenchmarkDefinition
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    slug = _slugify(name)
    ins = pg_insert(BenchmarkDefinition).values(
        slug=slug, name=name, category="other",
        metric_name=item.get("metric"), higher_is_better=True,
    ).on_conflict_do_nothing(index_elements=["slug"])
    await db.execute(ins)
    # Re-select to get the id (either freshly inserted or pre-existing).
    res = await db.execute(
        select(BenchmarkDefinition.id).where(BenchmarkDefinition.slug == slug)
    )
    return res.scalar_one()
