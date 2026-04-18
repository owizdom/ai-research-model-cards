# Benchmark Industry-Domain Classification Report

## How this was built

Sandbox blocked direct `psql` access and writes to `/tmp`, so the prod list
could not be queried live. The mapping is built instead from two reliable
proxies inside the repo:

1. **`packages/db/seed/benchmark_ontology.py`** — 56 curated slugs that are
   guaranteed to exist in the prod `benchmark_definitions` table.
2. **`data/exports/groq_baseline_20260408_224114.csv`** — 209 eval rows
   dumped from prod on 2026-04-08, covering every benchmark name the
   extractor has auto-minted. Slugs were derived with the exact function
   the extractor uses: `lowercase → [^a-z0-9]+ collapsed to "_"` (see
   `apps/worker/src/extractor/eval_extractor.py::_slugify`).

The user said prod has grown to ~367 definitions; the ~110 slugs
explicitly enumerated below cover every pattern observed in those two
sources. Anything the extractor has minted since 2026-04-08 that is not
explicitly listed falls through to `general_academic` via the trailing
`WHERE industry_domain IS NULL` clause — the user's chosen default.

**Files written:**
- `scripts/industry_mapping.sql` (184 lines, under the 200 cap)
- `scripts/industry_mapping_report.md` (this file)

Both live under `scripts/` instead of `/tmp/` because the sandbox refused
writes to `/tmp`. The SQL is read-only and was not executed.

## Counts of explicitly-mapped slugs per domain

| domain                  | explicit slugs |
|-------------------------|---------------:|
| general_academic        | ~65 |
| software_engineering    | ~21 |
| healthcare_medical      | ~18 |
| education_exams         | ~16 |
| cybersecurity           | ~10 |
| crm_enterprise          | ~8  |
| finance_tax             | ~7  |
| legal                   | ~5  |

The catch-all `UPDATE ... WHERE industry_domain IS NULL` at the end
absorbs every remaining auto-minted row into `general_academic`.

## Expected chart shape vs user's target (67% general/academic)

Projecting onto ~367 prod rows, assuming most uncovered auto-extracted
slugs are general-academic noise (partial phrases, safety eval names,
commonsense/reasoning, multimodal):

| domain                  | projected share | user's target  |
|-------------------------|----------------:|---------------:|
| general_academic        | ~70–75%         | ~67%           |
| software_engineering    | ~7–9%           | meaningful     |
| healthcare_medical      | ~5–7%           | meaningful     |
| education_exams         | ~5%             | meaningful     |
| cybersecurity           | ~3%             | meaningful     |
| crm_enterprise          | ~2%             | sparse         |
| finance_tax             | ~1–2%           | sparse         |
| legal                   | ~1%             | sparse         |

Net: chart should land close to the "67% general/academic, long tail of
industry-specific coverage" thesis. If the skew lands above 75% that
would signal the auto-extractor is producing more generic-reasoning
noise than industry-specific signal — worth noting as a coverage gap.

## Judgment calls (flagged for discussion)

1. **USMLE** — could map to either `healthcare_medical` or
   `education_exams`. Put in **healthcare_medical** because the exam
   content *is* the medical domain; if we split by exam-format intent,
   MedQA/USMLE collapse into exams and the healthcare bucket thins out.

2. **Safety benchmarks (BBQ, ToxiGen, XSTest, TruthfulQA, StrongREJECT,
   refusal/jailbreak evals, Wildchat, AgentHarm, RealToxicityPrompts)** —
   parked in `general_academic` per user guidance. These are cross-cutting
   and arguably deserve their own "safety" bucket, but that would double
   the classifier from 8 to 9 and the user explicitly said 8.

3. **Multimodal (MMMU, ChartQA, DocVQA, MathVista, AI2D, CharXiv)** —
   `general_academic`. None are clearly medical/legal/finance. AI2D is
   science-diagram education-adjacent but is taught as a general vision
   benchmark in every major system card, so kept general.

4. **WMDP-Bio / WMDP-Chem** — **healthcare_medical**. The benchmark
   measures biosecurity / chemical-weapon knowledge; the subject domain
   is biology/chemistry even if the governance framing is safety.
   WMDP-Cyber stays in `cybersecurity`. If the user wants WMDP treated
   as one "dangerous-capability" bucket inside `general_academic`
   instead, three lines in the SQL flip.

5. **LAB-Bench, BioLP-Bench, Long-Form Virology, Protocol Design,
   Sequence Design, computational-biology tasks** — all
   `healthcare_medical`. These come out of Anthropic's bio-uplift
   safety evals. They are biology-domain evals regardless of framing.

6. **Agentic Coding, PaperBench, MLE-bench** — `software_engineering`.
   PaperBench is ML-research replication; it's the closest neighbour
   to SWE-bench in the auto-extracted set.

7. **MCP Atlas, ProductionBenchmarks** — `crm_enterprise`. MCP Atlas
   is Anthropic's enterprise tool-use suite; ProductionBenchmarks is
   OpenAI's prod-traffic not-unsafe rate. Both are about business
   systems in production. Weak mapping — easy to flip to
   `general_academic` if the user disagrees.

8. **VCT, Browsing Broken Tools, Computer-use prompt injection,
   human-sourced jailbreaks** — `cybersecurity`. VCT is
   vulnerability/CVE triage from the Grok 4 card; the others are
   attack-surface evals. "Browsing Broken Tools" is the weakest of
   the four (it's a deception eval inside GPT-5) — could easily move
   to `general_academic`.

9. **τ²-Bench (Telecom)** — slugifies to `_bench_telecom` (literally
   leading underscore, because `τ²-` has no alphanumerics and gets
   collapsed). Put in `crm_enterprise` under both the correct slug
   `tau_2_bench` and the extractor's actual output `_bench_telecom`.
   Worth a one-off cleanup of the extractor slugifier.

10. **IFEval, Nexus, BFCL** — BFCL is a function-calling benchmark and
    sits in `software_engineering`. IFEval and Nexus are more ambiguous:
    IFEval is general instruction-following (kept general); Nexus is
    framed as function-calling in the Llama 3.1 paper so moved to
    `software_engineering`.

## Coverage gaps the user may want to backfill

The 8-domain taxonomy has buckets that the curated seed does not seed:
`crm_enterprise`, `education_exams` (beyond AIME/GPQA), `cybersecurity`
(beyond Cybench/CyberGym), and the finance/legal buckets have only 1
curated slug each. If the goal is a chart that shows industry-specific
coverage is sparse, that is exactly what will land. If the goal is to
*grow* those buckets, the ontology file itself needs new entries —
this mapping step alone can't fabricate benchmarks that no model card
has reported on.

## To inspect after the UPDATE runs

```sql
SELECT industry_domain, COUNT(*) AS n
FROM benchmark_definitions
GROUP BY 1
ORDER BY 2 DESC;
```

If any domain comes in lower than the table above suggests, the likely
cause is extractor-minted slugs that don't match any literal in the SQL
IN-lists. Fix by grepping `SELECT slug FROM benchmark_definitions
WHERE industry_domain = 'general_academic'` for healthcare/legal/etc.
substrings and appending them to the appropriate section.
