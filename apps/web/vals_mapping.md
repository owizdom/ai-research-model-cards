# vals.ai to Model Card Explorer Mapping

Generated: 2026-04-17
Target files: `vals_data.json` (raw capture), this file (mapping + cross-checks).
Note: `/tmp` was not writable in this session (permission denied). These files are written
under `apps/web/` alongside the data pipeline; copy to `/tmp` with `cp` if downstream
tools expect that path.

## Capture summary

- **Total rows captured**: 34 (27 with a numeric score; 7 rank-only rows where vals.ai
  surfaced a position but the SERP excerpt did not include the raw number).
- **Benchmarks discovered on vals.ai**: 13 leaderboards across composite, finance, tax,
  legal, knowledge, reasoning, coding, math, and education domains.
- **Models covered**: Claude 3 Opus, Claude 3 Haiku, Claude Opus 4.5/4.6/4.7 (thinking +
  non-thinking), Claude Sonnet 4.5/4.6 (thinking + non-thinking), Claude Haiku 4.5
  (Thinking), GPT-4, GPT-4o Mini, GPT-5, GPT-5.2, OpenAI o3, Gemini 2.5 Pro Exp,
  Gemini 3 Pro (11/25), Gemini 3.1 Pro Preview (02/26), Gemini 3 Flash Preview,
  Llama 3.3 70B, Grok 4, MiniMax M2.5, Gemma 4 31B IT, Muse Spark.
- **API availability**: vals.ai does not advertise a public REST API; no `/api/`,
  `/docs`, `/swagger`, or `/openapi` path reachable from the site. Their Github org
  `vals-ai` hosts dataset/harness code (`finance-agent`, `ioi-agent`) and the
  dataset is also mirrored on Hugging Face and Zenodo, but there is no served
  scoring endpoint. Integration path is HTML scraping or, for Finance Agent,
  re-running the open-source harness locally.
- **Capture caveat**: This session had `WebFetch` and `Bash` denied by permission
  policy, so scores were sourced from Google SERP excerpts of vals.ai pages rather
  than DOM scrapes. All numbers are exact quotes from those excerpts and every
  record in `vals_data.json` carries a `source_url` pointing at the canonical
  vals.ai page. A follow-up pass with WebFetch enabled should upgrade any
  `score: null, rank: N` rows to real numbers.

## Benchmark-level mapping to `benchmark_definitions.yaml`

| vals.ai slug            | vals.ai name              | Our canonical slug (from `benchmark_definitions.yaml`) | Confidence | Notes                                                                                    |
|-------------------------|---------------------------|--------------------------------------------------------|------------|------------------------------------------------------------------------------------------|
| `mmlu_pro`              | MMLU-Pro                  | `mmlu_pro`                                             | high       | Exact match. Same TIGER-Lab dataset, accuracy metric, % unit.                            |
| `gpqa`                  | GPQA (Diamond)            | `gpqa`                                                 | high       | Our slug aliases include "GPQA Diamond"; vals.ai uses the Diamond 198-question subset.   |
| `swebench`              | SWE-bench (Verified)      | `swe_bench`                                            | high       | Our aliases include "SWE-bench Verified"; vals.ai uses the 500-task verified set.        |
| `aime`                  | AIME 2025                 | `aime`                                                 | high       | Our aliases include "AIME 2024/2025".                                                    |
| `finance_agent`         | Finance Agent v1.1        | NO MATCH (out of scope)                                | n/a        | Not in our ontology. Candidate to add as new slug `finance_agent` (category: finance).   |
| `corp_fin_v2`           | CorpFin (v2)              | NO MATCH                                               | n/a        | Candidate: `corp_fin` (category: finance, description: credit-agreement long-doc QA).    |
| `tax_eval`              | TaxEval                   | NO MATCH                                               | n/a        | Candidate: `tax_eval` (category: tax).                                                   |
| `legal_bench`           | LegalBench                | NO MATCH                                               | n/a        | Candidate: `legal_bench` (category: legal).                                              |
| `case_law_v2`           | CaseLaw (v2)              | NO MATCH                                               | n/a        | Candidate: `case_law` (category: legal).                                                 |
| `sage`                  | SAGE                      | NO MATCH                                               | n/a        | Candidate: `sage` (category: education/math).                                            |
| `vals_index`            | Vals Index                | NO MATCH (composite)                                   | n/a        | Composite of other benchmarks; don't add as a separate definition, store as derived.     |
| `vals_multimodal_index` | Vals Multimodal Index     | NO MATCH (composite)                                   | n/a        | Same — derived metric.                                                                   |
| `vlair`                 | Vals Legal AI Report      | NO MATCH (report)                                      | n/a        | Editorial bundle rather than a benchmark.                                                |

**Coverage verdict**: Of the 13 vals.ai leaderboards, 4 map directly to our existing
canonical benchmarks (MMLU-Pro, GPQA, SWE-bench, AIME). The other 9 are
vertical-specific (finance, legal, tax, education) or composite — all valuable
signal that our current ontology does not yet include. Recommend adding 6 new
`benchmark_definitions.yaml` entries: `finance_agent`, `corp_fin`, `tax_eval`,
`legal_bench`, `case_law`, `sage`.

## Model-name normalization

vals.ai uses family-suffix notation (e.g., `Claude Opus 4.6 (Thinking)`, `Gemini 3.1 Pro
Preview (02/26)`). Our canonical format needs a normalization pass:

- `Claude Opus 4.X (Thinking)` -> split into `model_family=claude-opus-4-X`, `variant=thinking`.
- `Gemini 3.1 Pro Preview (02/26)` -> `model_family=gemini-3-1-pro`, `variant=preview`,
  `release_date=2026-02`.
- Date-suffixed snapshots (`finance_agent-04-22-2025`) -> treat as run snapshots,
  not separate models.

This split lives in the extraction layer, not in the benchmark definitions.

## Five cross-checks: AGREEMENT with our data (anticipated)

These are the rows where vals.ai's number is the strongest candidate for
cross-validating Claude-extracted scores. For each, I list what vals.ai reports
and what we should check against our DB (the actual diff is a follow-up query
that requires Bash/psql access, which was denied in this session).

1. **MMLU-Pro, Claude Opus 4.6 (Thinking)** - vals.ai: **89.11%**.
   Provider model card should report ~89% on MMLU-Pro. If our extracted value
   for `claude-opus-4-6-thinking` on slug `mmlu_pro` is within [88.5, 89.5],
   counts as agreement.
2. **MMLU-Pro, Gemini 3 Pro (11/25)** - vals.ai: **90.10%**.
   Cross-check against Google's Gemini 3 Pro model card MMLU-Pro figure; expected
   band [89.5, 90.5].
3. **SWE-bench Verified, Claude Sonnet 4.6** - vals.ai: **79.6%**.
   Cross-check against Anthropic's Sonnet 4.6 card. Anthropic typically reports
   a bash-only or single-shot number in that range.
4. **SWE-bench Verified, GPT-5.2** - vals.ai: **80.0%**.
   Cross-check against OpenAI's GPT-5.2 card SWE-bench Verified figure.
5. **Finance Agent, OpenAI o3** - vals.ai: **48.3%** (Sep 2025 snapshot).
   If any provider card surfaces a finance-agent number for o3, this is the
   independent benchmark. Our DB likely has no finance_agent entry today, so
   this functions as a new external data point rather than a direct diff.

## Five potential DISAGREEMENTS / anomalies

1. **SWE-bench Verified internal disagreement.** vals.ai shows a cluster of
   top models all within 1.3 points (Claude Opus 4.5: 80.9%, Claude Opus 4.6:
   80.8%, Gemini 3.1 Pro: 80.6%, MiniMax M2.5: 80.2%, GPT-5.2: 80.0%). Provider
   cards for the same models often claim higher scores (frequently 82-85% for
   frontier Claude/GPT). Expect 2-5 point disagreement between vals.ai's
   standardized bash-only harness and self-reported lab numbers.
2. **MMLU-Pro, Claude Opus 4.5 (Thinking)** - two vals.ai sources give 89.5%
   (April 10 2026) vs 89.11% (April 16 2026 snapshot attributed to Opus 4.6
   Thinking). Possible version labeling drift; verify whether our DB has both
   Opus 4.5-Thinking and Opus 4.6-Thinking as distinct entities.
3. **TaxEval recent #1 = 77.68%** with an unnamed model, dethroning Claude
   Sonnet 4.6. Any provider self-report will be for a different snapshot and
   unlikely to match exactly.
4. **Finance Agent, OpenAI o3** - 46.8% (April 2025 snapshot) vs 48.3%
   (September 2025 snapshot). Same model, different harness version. Our
   ingestion must treat date_measured as a hard key to avoid falsely flagging
   these as contradictions.
5. **CorpFin v2 top model swap** - Gemini 2.5 Pro Exp was #1 on the
   2025-05-09 snapshot; Grok 4 was #1 on the 2025-09-08 snapshot. If our DB
   collapses snapshots into a single "latest" row, either of these flips will
   read as a disagreement vs a provider card claim. Recommend snapshot-level
   storage.

## Recommendations

1. **Extend `benchmark_definitions.yaml`** with 6 new slugs: `finance_agent`,
   `corp_fin`, `tax_eval`, `legal_bench`, `case_law`, `sage`. Category vocabulary
   needs `tax` and `education` added (currently we have finance/legal as informal
   values in vals.ai only).
2. **Build a `source` dimension** in the eval store so vals.ai, provider
   cards, and paper PDFs are distinguishable rows for the same (model, benchmark).
   Cross-checking is only meaningful if sources are kept separate.
3. **Snapshot-dated scores.** vals.ai reruns every benchmark periodically
   (`/benchmarks/<slug>-<MM-DD-YYYY>`). Preserve the date on each row.
4. **Re-run this capture with WebFetch enabled.** Seven rows currently have
   `score: null` (rank-only). A single pass of 13 WebFetch calls to each
   `/benchmarks/<slug>` page will promote those to real numbers and add
   another ~40-100 rows (each leaderboard has ~20-40 models).
5. **Prefer Finance Agent for cross-validation.** Because it ships with an
   open-source harness (https://github.com/vals-ai/finance-agent) and dataset,
   we can independently reproduce the score if we want a tight contradiction
   test — unlike purely scraped numbers.
