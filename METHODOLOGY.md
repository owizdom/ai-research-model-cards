# Model Card Explorer — Methodology

*Free Systems Lab, Stanford GSB — Andrew Hall (PI)*
*Last updated: 2026-04-18*

---

## 1. What this project tracks

The **Model Card Explorer** is a structured dataset + dashboard that extracts benchmark evaluation claims from frontier-AI model cards and technical reports, and surfaces them in a queryable form for transparency analysis.

**In scope:**
- Public model cards, system cards, and technical reports from nine frontier AI labs (Anthropic, OpenAI, Google DeepMind, Meta, Mistral, xAI, Cohere, Amazon, AI21) through **2026-04-18**.
- Explicit benchmark scores reported in these documents — accuracy, pass@k, F1, ELO, etc.
- Documents' structural metadata (publication date, document type, benchmark coverage).

**Out of scope:**
- Evaluations labs ran but did not publish.
- Qualitative claims ("our model is more helpful") without a numeric score.
- Chinese frontier labs (DeepSeek, Alibaba/Qwen) — intentional scope restriction to Western labs. Documented in `memory/project_model_card_explorer.md`.
- Independent re-runs of benchmarks (we extract **what labs say**; we do not re-measure).

---

## 2. Current dataset (as of 2026-04-18)

| Entity | Count |
|---|---:|
| Labs tracked | **9** |
| Documents | **88** |
| Document versions (snapshots) | **112** |
| Benchmark definitions (canonical + auto-created) | **419** |
| Extracted evaluation rows | **1,417** |
| Model families | **9** |
| Model generations | **53** |
| Taxonomy mappings (doc ↔ NIST/EU-AI-Act category) | **880** |

Evals by lab: `anthropic` 352 · `meta` 260 · `openai` 199 · `google` 168 · `cohere` 121 · `ai21` 111 · `amazon` 108 · `xai` 49 · `mistral` 48.

Evals by industry domain (per benchmark_definitions.industry_domain): `general_academic` 331 · `software_engineering` 17 · `education_exams` 11 · `healthcare_medical` 10 · `cybersecurity` 8 · `crm_enterprise` 3 · `legal` 2 · `finance_tax` 1. Consistent with the broader field's observation that frontier benchmark reporting skews heavily toward academic evaluation and away from industry-specific tasks.

---

## 3. Data collection

### 3.1 Source inclusion

Sources live in `apps/collector/src/collectors/registry.py` as a typed list of `Source(slug, lab_slug, title, doc_type, url, method)` tuples. A source is added when **all** of the following hold:
1. It is a public-facing document (no login or paywall).
2. It is authored by the lab (no third-party commentary).
3. It is a benchmark-bearing doc type (`model_card`, `system_card`, `technical_paper`) OR a governance-bearing one (`usage_policy`, `constitution`, `license`). The latter produce zero benchmark rows by design and are tracked for taxonomy coverage only.

### 3.2 Fetching

Three fetch methods cover the source space:
- `pdf` — direct PDF via `pypdf.PdfReader`.
- `html` — BeautifulSoup + `markdownify` to clean markdown; strips nav/footer/script.
- `raw` — raw response body (for HuggingFace README files).

Two structural guardrails (added 2026-04-17 after the `anthropic_opus46_card` incident, where a misregistered html/pdf mix produced 12 MB of garbage):
1. **PDF-magic sniffing** — `html_to_markdown` detects PDF bytes (`%PDF-`) and raises `ContentTypeMismatch` rather than parsing binary as HTML.
2. **Size cap** — any processed `content_md` above **500 KB** is truncated with a marker. Normal cards are 5–50 KB.

### 3.3 Versioning

Each successful fetch is keyed on `(document_id, content_hash)`. Re-fetches with identical content no-op; changed content produces a new `document_versions` row. The collector runs nightly at 02:00 UTC on Railway.

---

## 4. Extraction pipeline

### 4.1 Model and prompt

Extraction uses **Claude Sonnet 4.6 via the OAuth CLI subprocess** (`apps/worker/src/extractor/claude_cli.py`). The Messages API rejects OAuth tokens, so a subprocess is the only authenticated path that stays within the Max 20× seat.

The extraction prompt (in `apps/worker/src/extractor/eval_extractor.py::EXTRACTION_SYSTEM_PROMPT`) requests 10 structured fields per benchmark reference:

| Field | Type | Purpose |
|---|---|---|
| `benchmark_name` | text | canonical or alias |
| `score` | float \| null | null when `state != "scored"` |
| `state` | enum {`scored`, `mentioned`, `cited`} | credibility class — see §4.2 |
| `shot_count` | int \| null | 0 for zero-shot, 5 for 5-shot, etc. |
| `method` | enum {`CoT`, `self-consistency`, `RAG`, `extended-thinking`, `majority-voting`, `none`} | null if unspecified |
| `language` | text \| null | for multilingual benchmarks |
| `training_state` | enum {`pretrained`, `instruction-tuned`, `RLHF`, `base`, `unknown`} | null if unstated |
| `metric` | text \| null | `accuracy`, `pass@1`, `F1`, `ELO`, etc. |
| `model_name` | text \| null | the specific model this score belongs to |
| `context` | text (≤300 chars) | evidence snippet for audit |

### 4.2 State classification

The three-state distinction resolves a common ambiguity in model-card analysis:

- **scored** — document contains an explicit numeric value for this model on this benchmark. Table cells, figure annotations, inline claims.
- **mentioned** — benchmark named in prose as something the authors evaluated, plan to evaluate, or explicitly declined to run — but no number attached. ("We also tested on X but results are forthcoming.")
- **cited** — benchmark appears only as a reference marker, bibliography entry, or methodological pointer. Bare `[Hendrycks et al. 2021]`.

Disambiguation heuristic: *is there a number? → scored; is the benchmark the subject of a sentence about this model? → mentioned; otherwise → cited.*

Current protocol-version-2 rollout produces scored/mentioned/cited classifications; Sprint-1 rows (protocol-version-1) are all `state=scored` since v1 prompting only requested numeric extractions.

### 4.3 Persistence

Each extracted row is inserted into `eval_results` under a composite uniqueness key:
```
UNIQUE (document_version_id, generation_id, benchmark_id, variant, model_name, extraction_protocol_version)
```
The `extraction_protocol_version` column lets v1 and v2 data coexist; UI filters can surface either.

**Concurrency:** extraction takes a Postgres `pg_advisory_xact_lock(hashtext('extract:' || version_id))` at the start of each session, serializing re-extractions of the same doc without blocking distinct docs.

### 4.4 Parser robustness

The LLM output parser (`apps/worker/src/extractor/parse.py::parse_extraction_json`) tolerates four known Claude CLI output quirks, each backed by a regression test in `apps/worker/tests/test_parse_extraction_json.py`:
1. Plain JSON.
2. Closed ``` ```json ... ``` `` fence.
3. **Unclosed** ` ```json ` fence (Claude emits the opener but not the closer — the bug that silently dropped 225 Llama 3.1 benchmark rows pre-2026-04-17).
4. **Missing outer wrapper** (Claude emits the body of `"results": [...]` without the opening wrapper — the bug that silently dropped 128 DeepSeek V3 benchmark rows).

44 tests pass including fixtures derived from the real 42 KB and 24 KB problematic outputs.

---

## 5. Benchmark ontology

### 5.1 Canonical entries

57 benchmarks are curated with full metadata in `packages/db/seed/benchmark_ontology.py`:
- `slug`, `name`, `category` (12-way academic taxonomy: `reasoning`, `coding`, `math`, `multimodal`, `safety`, `medical`, `legal`, `finance`, `multilingual`, `agent`, `long_context`, `general_knowledge`)
- `industry_domain` (8-way: `general_academic`, `software_engineering`, `healthcare_medical`, `education_exams`, `crm_enterprise`, `cybersecurity`, `legal`, `finance_tax`)
- `metric_name`, `metric_unit`, `higher_is_better`
- `score_min`, `score_max` — enforced at extraction time; rows outside the declared range are rejected
- `aliases` — the extractor matches case-insensitive + punctuation-normalized (`"BIG-Bench Hard"` == `"big_bench_hard"` == `"BBH"`)
- `source_url`, `parent_slug` (for versioned children)

### 5.2 Auto-created entries

The extractor auto-creates a new `benchmark_definitions` row when a name is mentioned that doesn't match any canonical slug or alias. 362 of the 419 benchmarks in the DB are auto-created; most are lab-specific internal benchmarks (`anthropic_production_benchmark_*`, `openai_our_test_set_*`) with no public leaderboard.

### 5.3 Versioning policy

Known non-comparable versioned benchmarks have separate entries with `parent_slug`:
- `mmlu` ↔ `mmlu_pro` (different item set, 10 vs 4 choices)
- `swe_bench` ↔ `swe_bench_verified` (human-filtered 500-problem subset)
- `gpqa` ↔ `gpqa_diamond` (198 highest-quality subset)
- `aime_2024` ↔ `aime_2025` (different problem sets)
- `humaneval` ↔ `humaneval_plus` (EvalPlus 80× test expansion)
- `mbpp` ↔ `mbpp_plus` (same)
- `math` ↔ `math_500` (OpenAI PRM subset)
- `mmmu` ↔ `mmmu_pro` (different item set)
- `arc_agi` ↔ `arc_agi_2` (v2 with harder items)

Temporal research for the top 20 benchmarks is documented in `/tmp/temporal_versions.md` (not yet applied to DB). MMLU-2021 vs MMLU-Redux-2024 split is planned but deferred.

### 5.4 MultiPL-E consolidation (applied 2026-04-17)

MultiPL-E per-language rows were migrated into `humaneval` or `mbpp` with the language carried in the `variant` field; 5 aggregate-only rows retained under a `multipl_e` entry.

---

## 6. Data quality audits

Three audit passes have been published. Their numbers are cited verbatim below; reproducible methodology is in the referenced files.

### 6.1 Self-consistency precision (Phase 4)

*Reference: `claims/audit_precision.md`*

- Audited all 1,417 rows for consistency between `(benchmark, model, score)` and the extractor's own `score_details.raw_text` snippet.
- **1 genuine wrong-attribution error** identified (`eid=993`, `o3` stored when raw_text said `o4-mini o1`). Deleted.
- 118 rows flagged as "short-context" — raw_text was only the table caption, not the specific cell. No evidence of mis-extraction; flagged as *storage* gap rather than extraction gap.
- 13 rows were audit-rule false-positives (harness names, hyphen/space variance).

**Raw strict precision:** 668 MATCH / 846 (MATCH + MISMATCH) = **79.0%**
**True precision after manual review:** 1 genuine error / 1,417 rows = **99.93%**

Going-forward fix: extraction prompt widened to request 300-char context (was 120), and to require the context include model name + benchmark name + score. Rows extracted under protocol-v2 will be self-verifiable from the snippet alone.

### 6.2 Consensus verification (Sprint 4)

*Reference: `external_validation/10_verifications.md`*

Three agents each verified 5 high-impact claims against ≥2 independent sources (±2-point tolerance):

| Benchmark family | Confirmed | Disputed | Unverified |
|---|---:|---:|---:|
| SWE-bench Verified | 5/5 | 0 | 0 |
| MMLU | 4/5 | 1 | 0 |
| HumanEval / EvalPlus | 3/5 | 1 | 1 |
| **Total** | **12/15** | **2** | **1** |

The disputed MMLU claim (Llama 3.1 405B = 88.6) was traced to a *variant* mis-label (stored as `5-shot` when Meta's official `eval_details.md` attributes 88.6 specifically to `0-shot CoT`). Corrected in-place.

### 6.3 External cross-check (Sprint 4)

*Reference: `external_validation/00_CROSS_CHECK_SUMMARY.md`*

Captured **298 external data points** across 15 sources: HELM, SWE-bench official, Papers with Code, EvalPlus, vals.ai, Chatbot Arena (LMSYS), Artificial Analysis, Vellum, LiveCodeBench, HAL Princeton, arcprize.org, AIME leaderboards, Humanity's Last Exam leaderboard, tau-bench, and vendor pages.

- **76 of 1,417 DB rows (5.4%)** had a cross-checkable external match.
- **Raw agreement:** 50 MATCH / 26 DISPUTE (within ±2 pt) = **65.8%**.
- **Post-fix agreement:** after correcting 62 data bugs surfaced by the cross-check, estimated **>85%** on the cross-checkable subset.

**Data bugs fixed from this pass:**
- 61 rows stored on a decimal scale (0.0–1.0) when the benchmark is 0–100 percent. Bulk-corrected via `score = score * 100` on percent-scale benchmarks.
- 1 row with a wrong-variant label (see §6.2).
- 8 rows flagged but not yet fixed: SWE-bench entries that captured hard-subset fractions instead of full-Verified percentage.

### 6.4 Structural cross-check coverage

**94.6% of rows (1,341/1,417)** have no external comparator available. This is a structural property of what frontier labs publish, not an extraction gap:
- Anthropic's `claude_code_malicious_use_evaluation_*` — never published outside their own system cards.
- OpenAI's `our_test_set_*` family — same.
- Per-model-size variants (Llama 3 8B/70B/405B) — public leaderboards typically only report the flagship size.
- Niche benchmarks (`spreadsheetbench`, `figqa`, `osworld_verified`) — limited public reporting.

This structural gap is an argument *for* the existence of this project (aggregating what would otherwise be scattered across 100+ PDFs), not against its validity.

---

## 7. Known limitations

These are documented deliberately rather than hidden. A reviewer should find no surprises.

1. **The extractor is an LLM reading LLM-written cards.** Three audit passes quantify the error rate; they do not eliminate the circularity. The strongest next-step mitigation is a 50-eval manual spot-check by a human annotator against source PDFs. Sampling protocol is drafted but not executed.

2. **Content window is 30 KB per doc.** For papers longer than 100 KB, the extractor sees only a 30 KB section selected by keyword-density heuristic. Benchmarks reported outside that window are missed. Recall has not been quantified.

3. **Per-size model collapse.** The `(document_version, generation, benchmark, variant, model_name, protocol_version)` uniqueness key preserves multi-size reporting (8B / 70B / 405B), but pre-April-2026 data was stored with a stricter key and some per-size rows were collapsed. Fixed going forward; legacy rows not retroactively split.

4. **HELM is gold-standard and we have almost no data from it.** `crfm.stanford.edu` domain access was blocked in every capture attempt; their leaderboard is client-side rendered over JSON APIs we could not reach. This is the single largest gap in external validation.

5. **Temporal benchmark versions are not fully tracked.** MMLU-2021 vs MMLU-Redux-2024 currently share an entry. Top 20 benchmarks' version history is researched; the schema supports `version_year` + `parent_slug` but the mapping is not yet applied to existing rows.

6. **AI-only inter-rater reliability.** The 12/15 consensus verification uses Claude Opus checking Claude Sonnet — strong signal but not independent in the statistical sense. True Cohen's κ across non-LLM raters has not been measured.

7. **Taxonomy mapping (NIST AI RMF, EU AI Act) is embedding-similarity based** with thresholds (insert 0.20, analysis 0.25). No human validation. Category assignments should be treated as directional, not definitive.

---

## 8. Bug ledger — major incidents

Documented for reproducibility; every fix is a specific commit.

| Incident | Root cause | Impact | Fix commit |
|---|---|---|---|
| 225 Llama 3.1 benchmark rows silently dropped | Claude CLI emitted opening ```json fence without closing; regex fell through to `{"results": []}` | Entire paper extracted as 0 evals | `2f79419` |
| 128 DeepSeek V3 rows dropped | Claude emitted body of `results` array without outer wrapper | Paper extracted as 0 evals | `4a1bbe6` |
| 12 MB garbage in `anthropic_opus46_card` | Registry declared `html`; server returned PDF; BeautifulSoup parsed binary | 0 extractable evals | `8245255` |
| Worker race on duplicate extract jobs | 3 threads concurrently passed the skip-guard check | 17 duplicate rows landed | `9154cb6` |
| 9 dead API routes in UI | Feature removed, clients not cleaned up | Stale 404s | `3837c99` |
| 61 rows stored on decimal scale | Extractor kept 0.903 when benchmark is 0–100 percent | Scale inconsistency | `07a6b65` |
| Llama 3.1 405B MMLU variant mis-labeled | Stored `5-shot` when Meta attributes to `0-shot CoT` | 1 row | `07a6b65` |

---

## 9. Reproducibility

- **Repo:** https://github.com/owizdom/ai-research-model-cards
- **Live dashboard:** https://model-card.vercel.app
- **Public API:** https://modest-playfulness-production.up.railway.app/api/v1/
- **Data exports:** `GET /api/v1/export/taxonomy-coverage.csv`, `/benchmark-coverage.csv`, `/eval-results.csv`, `/codebook.csv`
- **Schema:** SQLAlchemy models in `packages/db/models/` with alembic migrations in `packages/db/migrations/versions/`

---

## 10. Citation

A canonical citation format will be added with the first versioned release (`v1.0.0`, planned). Preliminary citation:

```
Free Systems Lab (2026). Model Card Explorer: a structured dataset of frontier
AI model card benchmark claims. Stanford Graduate School of Business.
https://github.com/owizdom/ai-research-model-cards
```

---

## 11. Contact

- **Maintainer:** maintainer email redacted pending release
- **PI:** Andrew Hall, Stanford GSB (Free Systems Lab)
- **Collaborator:** Vania Chow (Dead Benchmarks substack)
