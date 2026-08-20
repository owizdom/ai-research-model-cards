# Notes from instrumenting the model-card record

*A working memo from Free Systems Lab — preliminary observations from building an evaluation-reporting audit layer on top of our model-card corpus. May 2026.*

---

## Summary

Over the last several days we built three signals on top of [modelcards.net](https://modelcards.net) — plain-language Policy Notes per benchmark, per-row reproducibility flags, and cross-source divergence detection — modeled on the anonymized *Evaluation Cards* NeurIPS 2026 submission but implemented independently against our own corpus of model cards from nine frontier AI labs.

Three findings emerged. None of them are flattering to the reporting record.

## TL;DR

1. **0% of the 207 evaluation results we extracted from the Llama 3.1 technical paper are fully reproducible** on a four-axis sub-schema of shot count, prompting method, language, and training state. 35% disclose none of those four axes; 33% disclose only shot count. The reporting gap is not concentrated on one axis — it's structural across the whole methodology surface.

2. **Multi-source benchmark reporting is rare.** Of 963 distinct `(benchmark, model)` pairs in our corpus, only 22 (2.3%) are reported by two or more different model cards. The frontier-AI evaluation ecosystem is, in practice, a collection of single-source claims.

3. **When the same `(benchmark, model)` pair is reported by multiple sources, they often disagree.** 8 of 22 multi-source pairs (36%) diverge by more than 5 score points. The largest spread we surfaced is 28 points — `swe_bench` on Claude Opus 4.6, across two of Anthropic's own model cards.

---

## Method

We analyzed **51 model cards from six frontier labs**, collected between 2026-03-31 and 2026-05-15: Anthropic (Claude 2 through Opus 4.7), OpenAI (GPT-4 through GPT-5.5, plus o1/o3/Operator), Google DeepMind (Gemini 1.0 through 3.1 Pro), Meta (Llama 2 through 4 plus Llama Guard), Mistral (Mixtral, 7B, Large 2, Small 3, Codestral), and xAI (Grok 4 / 4 Fast / 4.1).

An LLM-driven extractor — Claude Sonnet 4.6, invoked via the `claude` CLI subprocess — reads each card and pulls structured evaluation results: benchmark name, score, model variant, methodology where disclosed. The full extraction has yielded **1,279 individual eval rows across 384 distinct benchmarks**.

To measure the reporting record, we built three signals adapted from EvaluationCards Section 4.2:

- **Reproducibility.** Per result: a binary check on each of four setup fields (shot_count, method, language, training_state). Aggregated as a 0–1 score per row and as a coverage rate per document.
- **Comparability / Divergence.** Group eval results by `(benchmark_slug, model_name)`; flag groups where ≥2 distinct documents disagree by more than 5 score points; surface which setup fields differ across the reports.
- **Plain-language Policy Notes.** Hand-authored narrative explainers per benchmark — *Measures*, *Caveat*, *Intended for*, *How to read* — modeled on the paper's Figure 3, currently shipped for the 10 most-reported benchmarks in our corpus.

All three are live as of 2026-05-29 at [modelcards.net](https://modelcards.net).

---

## Finding 1: The reproducibility gap is structural, not selective

EvaluationCards reports that 96.5% of `(model, benchmark, metric-path)` triples in their corpus lack at least one minimal reproducibility field. Their sub-schema is *sampling* parameters — temperature, max_tokens, harness. Ours is different: we check four *evaluation setup* fields — shot count, prompting method, evaluation language, model training state.

Distribution of reproducibility scores on a typical frontier-lab card (the Llama 3.1 technical paper, 207 extracted eval results):

| Reproducibility score | Rows | % | What it means |
|---|---:|---:|---|
| 0.00 | 73 | 35.3% | None of the four fields disclosed |
| 0.25 | 66 | 31.9% | Usually just shot count |
| 0.50 | 68 | 32.9% | Shot count + one more axis |
| 0.75 | 0 | 0.0% | — |
| 1.00 | 0 | 0.0% | All four fields disclosed |

**0% of rows are fully reproducible on this sub-schema.**

The convergence with the EvaluationCards paper's near-0% figure on a different sub-schema is the interesting part: the reporting gap is not concentrated on one axis. Model cards are sparse on the entire methodology surface, not selectively on one part. The paper picked sampling parameters because they're the strict minimum for re-execution; we picked evaluation setup because they're the strict minimum for *comparison*. Both come up empty.

---

## Finding 2: Multi-source reporting is rare

Across the 51 model cards, the extractor surfaced **963 unique `(benchmark, model)` pairs** — distinct combinations of a benchmark and a specific model on which that benchmark was run. Of those 963 pairs, **only 22 (2.3%) appear in two or more distinct documents.** The other 941 are single-source: one card, one score, no independent point of comparison.

The 22 multi-source pairs touch only 16 distinct benchmarks (the same benchmark often appears in multi-source coverage on more than one model). Put differently, only 59 of 1,279 eval rows in our corpus — under 5% — participate in any cross-document comparison at all.

This is directionally consistent with the EvaluationCards paper's Finding 3 (98.2% of pairs are single-party) but more skewed in our corpus — because we ingest only model cards, not third-party leaderboards. The 22 multi-source pairs are entirely produced by labs reporting on each other's models — e.g., the Llama 3.1 technical paper reporting on GPT-4 and Claude 3.5 Sonnet alongside Llama's own numbers.

There is no public third-party measurement infrastructure represented in our corpus. AISI, METR, and similar evaluation organizations exist; none of their results appear in any of the 51 model cards we've collected. Until external ingestion is wired in, "cross-party divergence" (the paper's first-party vs third-party axis) is structurally absent from this corpus.

---

## Finding 3: When sources do overlap, they disagree

Of the 22 multi-source `(benchmark, model)` pairs, 8 disagree by more than 5 score points. That's 36% — comparable in magnitude to the EvaluationCards paper's 51.9% on its larger corpus, despite our smaller and differently-collected dataset.

Top 8, sorted by spread:

| Benchmark | Model | Spread | Documents reporting |
|---|---|---:|---|
| `swe_bench` | Claude Opus 4.6 | **28.0** | 2 Anthropic cards |
| `math` | Gemini 1.5 Pro | 18.8 | 3 Google docs |
| `humaneval` | GPT-3.5 Turbo | 13.3 | Llama 3.1 paper + 1 other |
| `humaneval` | Claude 3.5 Sonnet | 9.7 | Google + Meta reporting on Anthropic |
| `bbq` | Claude Sonnet 4.6 | 9.4 | 2 Anthropic cards |
| `osworld` | Claude Mythos Preview | 6.9 | 2 Anthropic cards |
| `mmlu` | Llama 3 8B | 6.3 | 2 docs |
| `mmlu` | GPT-4o | 6.0 | OpenAI + Meta reporting on OpenAI |

Three of these warrant particular attention:

**`swe_bench` × Claude Opus 4.6, 28-point spread within Anthropic's own documents.** A single lab, reporting the same model on the de-facto frontier coding benchmark, twice, with a 28-point gap. The most likely explanation is that one report uses `swe_bench_verified` (the curated 500-task subset) and the other uses the full `swe_bench` — but the model card text doesn't always make this distinction explicit, and the labels aren't apples-to-apples. This is the kind of cross-report inconsistency that makes leaderboard claims hard to compare even *within* a single lab.

**`humaneval` × Claude 3.5 Sonnet, 9.7 points between Google and Meta.** Two third-party labs measuring an Anthropic model and reaching different numbers. This is the first cross-lab divergence we've been able to surface in any of our data — and it's on the de-facto reference coding benchmark.

**`mmlu` × GPT-4o, 6.0 points across non-OpenAI labs reporting on an OpenAI model.** Suggests the "MMLU" label hides setup or sub-task differences that the labs interpret differently. The MMLU vs MMLU-Pro distinction is reasonably well-disclosed in the field; this divergence is on plain MMLU, the one benchmark most labs agree to publish.

For 5 of these 8 groups, our pipeline can now name the setup axis that explains the disagreement — shot count, prompting method. For the other 3, the legacy variant string differs but our four-column schema can't represent the difference. The disagreement is either a split (subset of the benchmark) or a metric (different scoring rule applied to the same benchmark), neither of which currently has a structured home in our data model.

---

## Methodological note: a class of "divergence" that wasn't

Our first implementation of the divergence signal flagged 80 groups exceeding the 5-point threshold — about 47% of multi-report pairs. On verification, **72 of those 80 were within-document sub-task flattening, not cross-document disagreement.**

A typical example: GPT-4.5's system card reports 10 sub-results of a single biological-risk benchmark — `{Ideation, Magnification, Formulation, Acquisition, Release}` × `{pre-mitigation, post-mitigation}`. Our extractor stored these as 10 separate eval rows under the same benchmark slug, with the same model name. The divergence query then treated those 10 sub-task scores as "10 competing measurements of the same benchmark" with a 59-point spread.

The fix — requiring ≥2 distinct source *documents* per group — dropped the count to 8 and made the signal meaningful. The pattern itself is a direct empirical case for the EvaluationCards paper's central structural proposal: until sub-tasks are first-class typed structure (the paper's "Split" level), any divergence signal will be noisy.

This is the most important methodological takeaway from the work so far. **Measurement infrastructure that doesn't model splits will overcount divergence, in proportion to how aggressively the extractor flattens.**

---

## What the un-parseable variants tell us about schema

Our eval rows carry a free-form `variant` string in addition to four structured columns. 408 rows in our corpus have a non-default variant string with all four structured columns null. We wrote a parser that handles every variant pattern appearing four or more times in the corpus.

Of 769 candidate rows the parser examined:

- 36 had structured fields the parser could confidently fill — mostly shot_count and method.
- 341 already had the relevant structured column populated alongside the variant string.
- **392 had variant strings the parser could not map** — and on review, none of these are setup fields.

That 392-row negative space looks like this:

- Sub-task names — `"Magnification, pre-mitigation"`, `"Acquisition, post-mitigation"`
- Benchmark subsets — `"USAMO 2026"`, `"hard"`, `"overall"`
- Eval modes — `"ambiguous"`, `"disambiguated"`, `"side-by-side"`
- Metric names — `"pass@1"`, `"win rate vs Claude 3.5 Sonnet"`
- Mitigation states — `"without mitigations"`, `"without safeguards"`
- Tool-use modes — `"with tools"`, `"no tools"`

Six categories, none of which our current four-column schema can represent. They get stashed in `variant` because there's nowhere else to put them, and become invisible to any signal that operates on the structured columns.

In aggregate, the 392 unmapped variant rows are the strongest single argument for the EvaluationCards paper's 5-level rollout hierarchy. Our schema models four axes of setup. The corpus needs at least four more — splits, metrics, eval modes, mitigation states — before evaluation comparison can be done on the right unit.

---

## Limits

A few caveats worth surfacing on this set of findings:

- **Single-corpus, English-language, frontier-lab.** The 51 model cards are heavily skewed to US/UK labs and English-language benchmarks. We don't know whether the same patterns hold for smaller models or non-English coverage.
- **No third-party ingestion.** Until AISI, METR, or independent evaluation results are wired in, "cross-party divergence" is structurally absent — only intra-corpus variants exist.
- **The 5-point threshold is arbitrary.** We followed the paper's choice; it makes sense on percentage benchmarks but isn't obviously the right threshold on Elo-scaled or pass@k benchmarks. None of our top-8 divergences would change qualitatively at a 3- or 7-point threshold; the broader corpus-rate finding is more sensitive.
- **Sub-task flattening is mitigated, not eliminated.** Our fix requires ≥2 distinct documents per group, which excludes the worst false positives, but our schema still cannot distinguish "MMLU full" from "MMLU sub-set X" if both are labelled "MMLU" by source cards. Until the 5-level hierarchy lands, every aggregate divergence number should be read as an upper bound on the genuine signal.

---

## What's next

The most consequential next phase is the 5-level rollout hierarchy from EvaluationCards Section 3.2 — separating *Family / Composite / Benchmark / Split / Metric* into typed structure so divergence and reproducibility can fire on the right unit of comparison. Until that lands, the 8 cross-document divergences above are this corpus's strongest signal, and the 392 unmapped variant strings are the strongest argument for moving the schema forward.

After that, the missing ingredient is external evaluation data — AISI, METR, the UK AISI's long-form-tasks results, the Apollo evaluation reports. Once any of those are wired in alongside the model-card extractions, the `cross_party_divergent` count stops being structurally zero and the question becomes empirical instead of architectural.

---

*Free Systems Lab, 2026-05-29. The platform is live at [modelcards.net](https://modelcards.net); regeneration scripts and the EvalCards-aligned extractor are in the [ai-research-model-cards](https://github.com/owizdom/ai-research-model-cards) repository.*
