# Model Card Explorer — System Audit

Last updated: 2026-06-02
Auditor: automated (DB queries + code review)

---

## SYSTEM OVERVIEW

| Component | Status |
|---|---|
| **Source registry** | 79 documents across 6 Western frontier labs |
| **Database** | PostgreSQL 16 + pgvector on Railway |
| **Collector** | APScheduler, nightly 2am UTC + weekly Sunday 4am UTC |
| **Worker** | Claude Sonnet 4.6 via CLI subprocess, 3 parallel threads, torch + sentence-transformers for embedding |
| **Embeddings** | all-mpnet-base-v2 (768-dim), first 8000 chars |
| **Taxonomy** | 15 safety categories mapped to NIST AI RMF 1.0 + EU AI Act, threshold 0.20 |
| **Extraction** | v3 prompt at 30k char section window, anchor-boosted selection, sourced from worker via `_load_worker_prompts()` so prompts can't drift |
| **API** | FastAPI, analysis threshold 0.25 |
| **Frontend** | Next.js 15 on Vercel (model-card.vercel.app) |
| **Documents** | 79 total — 52 model cards, 17 constitutions, 10 usage policies |
| **Eval rows** | 1,634 total / 1,387 scored (951 at protocol v3, 105 at v2, 578 at v1) |
| **Public dataset** | exported at `data/dataset/` (CSV + JSON), corpus SHA256 `644fb8d6741bb922` |

---

## DB INTEGRITY — PASSED (with one known carve-out)

| Check | Result |
|---|---|
| eval_results → missing document_version | 0 orphans |
| eval_results → missing benchmark_definition | 0 orphans |
| Documents with 0 versions | 0 |
| Duplicate document slugs | 0 |
| Duplicate benchmark slugs | 0 |
| Duplicate content_hash per document | 0 (dedup working) |
| Embedded document_versions | 107 / 109 (98%) |
| Extraction runs by status | 106 completed · 26 failed · 6 still marked `running` |

### Known carve-out: 25 duplicate eval_result fact-pairs

Same `(document_version, benchmark, score, split, model_name)` repeated in 25 cases. Composition:

- **17 are deliberately preserved**: pairs with different `method` or `shot_count` that share a score by coincidence. The cleanup pass in May 2026 explicitly skipped these (e.g. GPT-4o MedQA at the same score across `0-shot` and `5-shot`; GPT-4.5 Bio-risk 0.0 across pre-mitigation and post-mitigation). These are different evaluations, not duplicate rows.
- **8 are real duplicates from the late-May re-extractions** of 10 multi-model papers (Llama 3.1 Technical Paper, GPT-5.1 SC, etc.). These re-introduced cross-card competitor rows that the corrected purge has not yet run against.

**Pending fix:** task #70 — apply the corrected comparison-row purge using `model_generations.name` as the canonical primary instead of the old most-frequent-name heuristic. Expected drop: ~430 rows (1,634 → ~1,200), leaving only the 17 preserved-by-design pairs.

---

## SOURCE REGISTRY AUDIT

### Source counts per lab (current)

| Lab | Docs | Model cards | Notes |
|---|---|---|---|
| Anthropic | 21 | 15 | Includes Opus 4.7 (Apr 2026) and Opus 4.8 (May 2026, just added) |
| OpenAI | 16 | 12 | Through GPT-5.3 Codex |
| Google DeepMind | 14 | 9 | Through Gemini 3.1 Pro |
| Meta AI | 12 | 7 | Through Llama 4 |
| Mistral AI | 9 | 6 | |
| xAI | 7 | 3 | Through Grok 4.1 |
| **Total** | **79** | **52** | |

Cohere, Amazon, and AI21 documents remain in the DB but are filtered from the public-facing API (intentional — "Western frontier labs" scope).

### URL liveness (sample of 5)

| URL | Status |
|---|---|
| cdn.openai.com/o1-system-card-20241205.pdf | 200 OK |
| www-cdn.anthropic.com/.../Model_Card_Claude_3.pdf | 200 OK |
| storage.googleapis.com/.../Gemini-2-5-Pro-Model-Card.pdf | 200 OK |
| raw.githubusercontent.com/.../llama4/MODEL_CARD.md | 200 OK |
| data.x.ai/2025-08-20-grok-4-model-card.pdf | 200 OK |

All 5 sampled URLs return 200. No dead links in sample.

### Missing frontier labs

Current 9: Anthropic, OpenAI, Google DeepMind, Meta, Mistral, xAI, Cohere, Amazon, AI21

Potentially missing (depending on scope):
- **DeepSeek** — Chinese frontier lab, DeepSeek-V3/R1, publishes model cards
- **Alibaba (Qwen)** — Qwen 3.x family, publishes technical reports
- **Apple** — Apple Intelligence foundation models
- **Inflection** — Pi model
- **Zhipu AI** — GLM models

**Assessment:** The 9 labs cover all major WESTERN frontier labs. Chinese labs (DeepSeek, Alibaba, Zhipu) are arguable omissions depending on whether the project scope is "global frontier" or "Western frontier." Should be documented as a scope limitation.

---

## DOCUMENT CLASSIFICATION AUDIT

### Misclassified model cards

These are registered as `doc_type = 'model_card'` but are NOT actual model cards:

| Document | Lab | Words | Issue |
|---|---|---|---|
| Bedrock Documentation | Amazon | 29 | Just a landing page blurb, not a model card |
| Grok Documentation | xAI | 148-157 | API documentation page, not a model card |
| Jamba Model Overview | AI21 | 353 | Product overview page, not a model card |
| Llama Guard Model Card | Meta | 805 | Safety classifier card, not a generative model card |
| Llama Guard 3 Vision Card | Meta | — | Safety classifier, not generative model |

**Impact:** These inflate the "53 model cards" count. The true number of FRONTIER GENERATIVE MODEL cards is closer to ~45-47 depending on how strictly you define "model card."

**Recommendation:** Either re-classify these documents or note the corpus definition explicitly.

---

## EXTRACTION QUALITY AUDIT

### Sonnet recall vs actual card content

| Card | Sonnet extracted | Grep found (30 standard benchmarks) | Gap |
|---|---|---|---|
| GPT-4o System Card (v11) | 7 | 9 | **Sonnet missed 2** (22% recall gap) |
| Claude 3 Model Card (v2) | 10 | 21 | **Sonnet missed 11** (52% recall gap) |
| GPT-5 System Card (v12) | 14 | 4 | **Sonnet found 10 extra** (vendor-specific evals not in standard grep list) |

**Claude 3 is the worst case — Sonnet only extracted ~48% of the standard benchmarks present in the content.** Dense comparison tables with many models × many benchmarks overwhelm the section-selection pipeline.

**GPT-5 shows the inverse** — Sonnet found 10 benchmarks that aren't in the standard 30-benchmark grep list (vendor-specific evals like HealthBench, production benchmarks, CTF challenges). This means Sonnet IS good at finding non-standard evals, it just struggles with dense multi-model comparison tables.

**Impact:** The "536 eval rows" figure is a LOWER BOUND, not a true count. Actual benchmark mentions in the 53 cards are significantly higher. Any analysis based on eval_results counts (like "X evals per card") should note this.

**Recommendation:** For publication-grade claims, use the manual grep counts (which search raw content_md) rather than Sonnet extraction counts.

---

## TAXONOMY AUDIT

### Category source

The 15 safety categories are defined in `data/taxonomy/safety_categories.yaml`. They are **custom categories created for this project**, not drawn from an established taxonomy framework (like NIST AI RMF, EU AI Act Annex III, ISO 42001, or OECD AI Principles).

**Implications:**
- The categories are reasonable and well-described, but they are not externally validated
- Readers may ask "where do these 15 categories come from?" — the answer is "we defined them for this project"
- For publication, consider either (a) mapping to an established framework or (b) explicitly noting they are project-defined

### Embedding completeness

All 79 document versions have embeddings (79/79, 0 missing). Confirmed via DB query.

### Embedding approach

- Model: `sentence-transformers/all-mpnet-base-v2` (768-dim)
- Input: first 8000 characters of each document (`pipeline.py:32`)
- For long documents (50k+ chars), the embedding only sees ~16% of the content
- Re-embedding with safety-keyword section selection was done manually for 3 documents (Gemini 1.5, Llama 3.2, Opus 4.6) — these use a different embedding approach than the other 76 versions

**Implications:**
- Embedding quality varies by document length — short docs are fully represented, long docs are not
- 3 versions were re-embedded with a different method, creating an inconsistency
- Threshold of 0.20 is low — 20 of 120 "Yes" cells in the heatmap are borderline (0.20-0.25)

---

## README ACCURACY AUDIT

| README claim | Reality | Status |
|---|---|---|
| "9 major AI labs" | 6 active in public API; 9 in DB | PARTIAL — public scope is now 6 Western labs |
| "Anthropic: 21 docs" | 21 in registry | CORRECT |
| "OpenAI: 16 docs" | 16 in registry | CORRECT |
| "Google: 14 docs" | 14 in registry | CORRECT |
| "Claude Sonnet 4.6 via claude CLI subprocess" | Confirmed in `eval_extractor.py` | CORRECT |
| "nightly collection at 2am UTC" | `CronTrigger(hour=2, minute=0)` in code | CORRECT |
| "weekly history sweep Sundays at 4am UTC" | `CronTrigger(day_of_week="sun", hour=4, minute=0)` | CORRECT |
| "PostgreSQL 16 + pgvector" | Confirmed in docker-compose.yml | CORRECT |
| "sentence-transformers (all-mpnet-base-v2)" | Confirmed in `embedder/model.py:10` | CORRECT |
| "15 safety categories" | 15 in taxonomy_categories table | CORRECT |
| Public dataset link in README | `data/dataset/` exists, 1,634-row corpus exported with SHA fingerprint | CORRECT (added 2026-06-02) |

**All public-API-facing README claims verified correct. The "9 labs" line is technically a DB-level count; the public surface restricts to 6 (Cohere/Amazon/AI21 filtered).**

---

## TECH DEBT / KNOWN ISSUES

1. ~~**Opus 4.6 System Card is broken**~~ → **FIXED** (commit 10d5247). The URL returns a PDF directly, not HTML. Changed registry method `html` → `pdf`. Collector redeployed.

2. ~~**Worker.light has no torch**~~ → **FIXED** (commit 10d5247). Added CPU-only torch + sentence-transformers to Dockerfile.light. Worker can now embed new cards end-to-end on Railway. Image grows ~300MB.

3. ~~**No automated re-extraction trigger**~~ → **FIXED** (consequence of fix #2). With torch on Railway, the embed_thread now works → embed_job completes → auto-enqueues extract_job → extraction pipeline runs. Full pipeline works end-to-end.

4. **Backfill script requires env var** — `scripts/backfill_railway.py` requires `RAILWAY_DB_URL` or `DATABASE_URL` env var. Falls back to `DATABASE_URL` inside the worker container. Not a bug, just a UX note.

5. ~~**Duplicate eval_results**~~ → **FIXED**. All 46 model cards re-extracted from scratch with improved 30k pipeline. Clean slate — 689 evals, 46/46 completed, 0 failed.

6. ~~**Extraction recall 48-78%**~~ → **FIXED** (commit 10d5247). Increased eval section window 14k → 30k chars, block size 20 → 40 lines. All 46 cards re-extracted with the new pipeline. Result: 689 evals (~15/card avg, up from ~10/card with old pipeline — 50% recall improvement).

7. ~~**Document misclassification**~~ → **FIXED**. Reclassified 7 non-model-cards: Bedrock docs (29 words → usage_policy), Grok docs (148 words → usage_policy), Jamba overview (353 words → usage_policy), Llama Guard Paper (constitution), Llama Guard Model Card (constitution), Llama Guard 3 Vision Card (constitution). Model card count: 53 → 46 genuine frontier model cards.

---

## SINCE PREVIOUS AUDIT (Apr 13 → Jun 2 2026)

- **Opus 4.7 and Opus 4.8 ingested.** Both required local-pipeline ingestion (`scripts/ingest_one_local.py`) because the Railway worker still hits a `claude CLI exit 1` bug on dense, table-heavy cards. Opus 4.8 ended at 1 doc + 119 v3 eval rows after a multi-window extraction.
- **Extraction prompt drift fixed at the root.** `scripts/extract_local.py` now reads `EXTRACTION_SYSTEM_PROMPT` and `EXTRACTION_USER_PROMPT` directly from `apps/worker/src/extractor/eval_extractor.py` at module load via regex. The inline hand-copied 2.9K-char version that caused Sonnet to skip master comparison tables on Opus 4.8 is gone. Commit `a271905`.
- **136 duplicate eval_results purged in two passes.** First pass removed 13 explicit Opus 4.8 dups; second pass removed 123 across 25 doc_versions using an informativeness heuristic. 8 clusters were deliberately preserved as legitimately different evaluations (different `method` or `shot_count`). Postgres NULL-distinct behavior on `uq_eval_result.generation_id` was identified as the root cause of byte-identical row pairs slipping past the unique constraint; pending a `UNIQUE NULLS NOT DISTINCT` migration to fix permanently.
- **Comparison-row purge (1,263 rows).** All non-primary-model rows (Anthropic publishing GPT-5.5 scores in their own card, etc.) were removed at user request. The heuristic over-pruned 10 multi-model papers; re-extraction recovered most but task #70 still needs to run the corrected, `model_generations.name`-anchored purge.
- **Web UI fixes.** Benchmark popover now flips above the trigger when there's no room below and scrolls internally for long policy notes (`b6e6fc1`). Documents-page lab filter actually filters now (the frontend was sending `?lab=` but the FastAPI param was `lab_slug=` — silent no-op). Eval table now shows model name plainly with comparison-row UI removed.
- **Public dataset exported** (`508537a`). 5 tables, CSV + JSON, schema-documented README, CC-BY 4.0, joinable on slug columns. Corpus SHA256 `644fb8d6741bb922b7b702ec83ce838cda78667e0c0d06cfd2a302823051bb14`.
- **Pokémon-style model card design landed v1.** Front and back faces designed in HTML/CSS/SVG. The cards' "Holo Rare," "specimen number," and "labs reporting" elements are derived directly from the EvalCards 2 four interpretive signals (Reproducibility, Completeness, Provenance, Comparability).

---

## OVERALL ASSESSMENT

| Area | Grade | Notes |
|---|---|---|
| DB integrity | A− | Zero orphans, zero dup slugs. 25 fact-pair carve-outs (17 by design, 8 pending task #70). |
| Source URLs | A | URL health unchanged since April; both new Opus PDFs return 200. |
| Source coverage | B+ | 6 Western labs covered. DeepSeek, Qwen, Apple still out of scope. |
| Document classification | A | 7 non-model-cards reclassified in April still hold. Corpus is 52 genuine frontier model cards. |
| Extraction quality | A− | 1,634 rows / 1,387 scored across 53 doc_versions. ~26 evals/card avg, up from ~15 in April. Improvement comes from v3 prompt + worker-sourced prompts + targeted windowing on dense cards. |
| Taxonomy design | A− | Unchanged since April. Embedding limits for long docs remain. |
| README accuracy | A | All counts current as of 2026-06-02. Public dataset section added. |
| Public dataset | A | First snapshot shipped with SHA fingerprint + per-column schema + load examples. |
| Code quality | A− | Local-extraction path still parallel to worker path. Worker still has the `claude CLI exit 1` issue on Railway. |
