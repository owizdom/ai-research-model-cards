# modelcards.net — public dataset

A snapshot of the modelcards.net evaluation corpus, exported as flat
CSV and typed JSON files. Five tables, no nesting, joinable on slug
columns.

- **Snapshot date:** 2026-06-28
- **Corpus SHA256:** `b6277fcba8e898811b3d57d0768602f06ebf30bbc80f0c3c008f9dc3bf172230`
- **License:** CC-BY 4.0 (data extracted from public model cards;
  attribution to modelcards.net + original lab)

## Files

| file | rows | what's in it |
|---|---|---|
| `eval_results.csv` / `.json` | 1742 | every (model, benchmark) scored row — the fact table |
| `benchmarks.csv` / `.json`   | 652 | benchmark definitions, categories, and policy notes |
| `models.csv` / `.json`       | 56 | canonical model generations linked to their cards |
| `labs.csv` / `.json`         | 6 | lab metadata and brand color |
| `documents.csv` / `.json`    | 82 | model card identity (titles, source URLs, word counts) |

## Schema

### eval_results

The fact table. One row per scored evaluation in our corpus.

| column | type | notes |
|---|---|---|
| id | int | internal row id |
| model_name | str | the model name as reported in the source card |
| model_generation_slug | str \| null | canonical generation slug from `models.csv` |
| lab_slug | str | foreign key into `labs.csv` |
| document_slug | str | foreign key into `documents.csv` |
| benchmark_slug | str | foreign key into `benchmarks.csv` |
| benchmark_name | str | display name |
| benchmark_category | str | e.g. coding, reasoning, multimodal, safety |
| split | str \| null | sub-task within benchmark (verified, diamond, etc.) |
| score | float \| null | numeric score; null when state != "scored" |
| state | str | "scored", "mentioned", or "cited" |
| method | str \| null | sampling/prompting method (CoT, extended-thinking, etc.) |
| shot_count | int \| null | 0 for zero-shot, 5 for 5-shot, etc. |
| training_state | str \| null | "pretrained", "instruction-tuned", "RLHF", etc. |
| language | str \| null | for multilingual benchmarks |
| metric_path | str \| null | the scoring rule (accuracy, f1, pass_at_1, etc.) |
| variant | str | the canonical variant key built from above fields |
| is_self_reported | bool | true if the lab's own card; false if third-party |
| extraction_protocol_version | int | extraction-pipeline version that produced the row |
| source_type | str | model_card / paper / leaderboard |

### benchmarks

Benchmark definitions plus EvalCards-style policy notes when present.

| column | type | notes |
|---|---|---|
| slug | str | canonical slug |
| name | str | display name |
| category | str | high-level grouping |
| metric_unit | str | e.g. "%", "elo", "f1" |
| policy_note | json | { measures, caveat, intended_for, how_to_read, topic_tags, sources } |

### models, labs, documents

Self-explanatory. Use the slugs to join into `eval_results`.

## Loading

Python (pandas):
```python
import pandas as pd
evals = pd.read_csv("eval_results.csv")
labs  = pd.read_csv("labs.csv")
df    = evals.merge(labs.add_prefix("lab_"), left_on="lab_slug", right_on="lab_slug")
```

R:
```r
evals <- read.csv("eval_results.csv")
labs  <- read.csv("labs.csv")
df    <- merge(evals, labs, by = "lab_slug")
```

SQL (DuckDB, against the CSVs directly):
```sql
SELECT b.name AS benchmark, AVG(e.score) AS avg_score
FROM 'eval_results.csv' e
JOIN 'benchmarks.csv' b ON e.benchmark_slug = b.slug
WHERE e.state = 'scored' AND b.category = 'coding'
GROUP BY 1 ORDER BY 2 DESC;
```

## Provenance

Every row in `eval_results` traces back to a specific model card via
`document_slug`. The source URL for each card is in `documents.csv`.
Scores have not been re-run by us — they're extracted from the labs'
own published cards. Multi-source comparisons can be reconstructed by
filtering `eval_results` on (benchmark_slug, model_name) and grouping
by `document_slug`.

## Caveats

- 96.5% of (model, benchmark) triples are missing at least one
  reproducibility field (per the EvalCards 2 paper finding, which
  applies to our corpus as well).
- 98.2% of (model, benchmark) pairs are reported by only one party.
  Cross-source validation is rare.
- Score normalization is light: values ≤ 1.0 are kept as fractions,
  values > 1.0 are kept as percentages. Reader should check `metric_unit`
  in `benchmarks.csv`.
- Some older Anthropic and Llama cards have sparse benchmark coverage;
  the corpus over-represents English-language frontier evals.

## Citation

If you use this dataset, please cite as:

> modelcards.net evaluation corpus, snapshot 2026-06-28, corpus sha256
> b6277fcba8e898811b3d57d0768602f06ebf30bbc80f0c3c008f9dc3bf172230. Available at modelcards.net.

And cite the upstream model cards individually using the URLs in
`documents.csv`.
