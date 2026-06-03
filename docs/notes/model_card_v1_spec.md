# Pokemon-style model card — v1 spec

Designing the two-sided model card for modelcards.net. Built on what
EvalCards 2 (NeurIPS 2026) tells us is missing in current cards, what
4 of our own respondents told us they actually use cards for, and what
we already have in the DB.

## What the inputs say

### EvalCards 2 (the framework)
- 5-level rollout for every score: Family → Composite → Benchmark → Split → Metric. Flat `(model, benchmark, score)` triples lose the structure.
- 4 interpretive signals per record: Reproducibility, Reporting Completeness, Provenance, Comparability. Surfaced as flags, not hidden.
- 2 reader modes: Policy (plain-language, decision-ready, default) and Research (technical depth, on opt-in).
- Empirical baseline on 5,498 models: 96.5% of triples miss a reproducibility field, 98.2% of (model, benchmark) pairs are reported by only one party, 51.9% of multi-org metric groups diverge above 5%. So the default reader is in a corpus that's mostly incomparable and mostly unreproducible.

### Our user survey (n=4)
- 75% of respondents use a card for research/benchmarking. 25% for deployment risks. Vendor selection and compliance got zero votes.
- Top missing info: training data provenance (50%), failure modes / edge cases (50%). Then agentic limits, fine-tuning behavior, cross-lab comparable benchmarks, deployment constraints.
- On the "89% of benchmarks come from only one lab" problem: 50/50 split between flag-when-unreliable and show-raw-per-lab. Nobody wanted hidden normalization.
- Wishlist (free text): real user queries / demos, threshold assessments with load-bearing explanations, tokens/sec, an easy way to rerun the evals.

### What we already have in the DB
- `documents` + `document_versions` (identity, source PDF, full content_md)
- `eval_results` (model_name, benchmark, score, split, method, training_state, shot_count, language, metric_path, state, extraction_protocol_version, is_self_reported)
- `benchmark_definitions.policy_note` (Measures / Caveat / Intended for / How to read — already populated for top benchmarks, matches Figure 3 of the paper)
- `divergentGroups` API (cross-card score disagreement flags)
- `model_generations` (canonical primary model per card)

## The card — two sides

The mental model is a Pokemon TCG card. Glanceable identity-plus-stats on the front. Methodology and fine print on the back. Front maps to Policy mode (always shown), back maps to Research mode (one click).

### FRONT — Policy mode, one screen, decision-ready

| zone | content | source |
|---|---|---|
| **Identity strip** | Model name (large) · lab + lab logo · generation slug · release date · context window · param count if known | `documents`, `model_generations` |
| **Type tags** | Categorical chips derived from benchmark coverage: `agentic`, `multimodal`, `coding`, `reasoning`, `long-context`, `safety` | `benchmark_definitions.category` aggregated per doc |
| **Top-line index** | One headline capability number, in the "Artificial Analysis Index" pattern (paper §A.1). e.g. weighted blend of MMLU + SWE-bench + MMMU since our own analysis showed those carry orthogonal information | new computed field |
| **Stat block (3–5 rows)** | Family-level rollout: e.g. "MATH-family 96.7", "SWE-bench-family 88.6", "HLE 57.9 with tools". One row per benchmark family, not per metric. Source-badge each (self-reported vs third-party). | `eval_results` aggregated up to Family per paper §3.2 |
| **Vitals strip** | tokens/sec · cost per 1M tokens · latency p50 / p95 | needs new ingestion (not in eval_results today) |
| **Reliability flags** | Four colored badges per the paper's signals: Reproducibility, Reporting Completeness, Provenance, Comparability. Each is a 0–100 score with a color band. Click expands the per-field breakdown. | computed from `eval_results.method/training_state/shot_count/language/metric_path` populated-ness + `divergence` API |
| **Practical demo** | 1–2 sample prompts with the model's example outputs. Direct response to "real user queries / practical demos" survey wish. | manually curated for v1, later ingested from lab demos / model gallery |
| **One-line takeaway** | Plain-language "what this model is for, in a sentence" — boils the Policy Note's "Intended for" + "How to read" into a single sentence | manual write per card or LLM-summarized |

### BACK — Research mode, expandable

| zone | content | source |
|---|---|---|
| **Full eval table** | Every row at full Family → Composite → Benchmark → Split → Metric path. Methodology fields (temperature, max_tokens, prompt template, shot count, judge model). Source attribution. Divergence flag when cross-card disagreement exists | `eval_results` joined with `benchmark_definitions` |
| **Training data provenance** | Cutoff date · disclosed sources · contamination notices · what's known to be excluded | new extraction (currently in card text, not in schema) — survey gap #1 |
| **Failure modes / edge cases** | Known weaknesses, edge cases the lab disclosed, red-team findings if released | new extraction from "limitations" sections — survey gap #2 |
| **Threshold assessments** | For safety-critical benchmarks (CBRN, biorisk, agentic-uplift): the threshold, what crossing it means, which result is load-bearing for the lab's decision | partial via `benchmark_definitions.policy_note.caveat`, needs explicit threshold field |
| **Reproducibility recipe** | Link to eval harness · docker / pip command · seed · prompt template | `eval_results.method` + new harness-link field |
| **Cross-source comparison** | For (model, benchmark) pairs reported by ≥2 sources: show all of them, flag divergence ≥5% per paper | `divergentGroups` API (already wired) |
| **Citation + provenance** | Source PDF · paper(s) the benchmark is from · dataset license · lab contact | `documents.source_url` + `benchmark_definitions.policy_note.sources` |

## What V1 ships with vs what's flagged "needs work"

Built today (have the data):
- Identity strip
- Type tags from category aggregation
- Stat block at Family-level
- Source badge per row
- Reliability flags 1, 3, 4 (Reproducibility, Provenance, Comparability) — all computable from existing eval_results columns
- Full back-side eval table
- Cross-source comparison (already wired)
- One-line takeaway (manual writing, ~50 cards)

Needs ingestion work (will show "—" or "missing" placeholder for v1):
- Vitals strip — tokens/sec, cost, latency. Not in cards, has to come from lab pricing pages or third parties like Artificial Analysis.
- Practical demos — needs curation per card, no automated source.
- Training data provenance — present in many cards as prose, needs a structured-extraction pass to pull cutoff date + sources into the schema.
- Failure modes — same as above.
- Reproducibility recipe — most cards don't include a harness link. Make the field exist, populate where we can find it.
- Threshold assessments — `policy_note.caveat` partially covers this, but the load-bearing-result framing needs a new field.

Honest principle from the paper, worth restating: show what's missing rather than papering over it. The reliability flags exist to make absence visible. If a card has no training data provenance, the front-side flag should say so in red, not be hidden.

## Design constraints

- Front fits on one mobile-portrait screen without scroll. If it doesn't, cut the stat block to 3 rows.
- Back is scrollable but every zone has a clear heading anchor.
- Every score on the front is clickable — opens the back-side eval row that produced it. No orphan numbers.
- Cross-source comparison stays visible by default on the back. Hiding it defeats the paper's argument and our project's reason for existing.
- Reliability flags are colored but the color is always backed by a number a reader can read. No emoji-only signals.

## Build order for v1

1. Compute and render the 4 reliability flags. This is the strongest signal in the whole card and uses data we already have.
2. Stat block at Family-level rollout. Aggregate `eval_results` up to `benchmark_definitions.family_slug` (need to add this column if not present).
3. Front-side identity strip + type tags.
4. Back-side full eval table (use existing `EvalTable` mostly as-is).
5. Cross-source comparison panel on the back.
6. Vitals strip (placeholder for now, hook up when ingestion exists).
7. Demo strip + training-data + failure-modes — these need new ingestion work, ship behind a feature flag and start populating Anthropic cards first since their cards are the longest and most structured.
