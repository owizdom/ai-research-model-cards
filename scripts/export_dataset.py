#!/usr/bin/env python3
"""Export the modelcards.net corpus as a self-contained public dataset.

Pulls from the Railway DB and writes CSV + JSON for five tables:
  - eval_results: every (model, benchmark) scored row (the core fact table)
  - benchmarks:   benchmark definitions + policy notes
  - models:       canonical model_generations
  - labs:         lab metadata + brand color
  - documents:    model card identity (no content_md — too heavy)

Output goes to data/dataset/. A README.md is generated alongside.
A SHA256 fingerprint of the concatenated CSVs is recorded in the README
so consumers can verify their copy matches a known snapshot.

Usage:
  python3 scripts/export_dataset.py                  # writes to data/dataset/
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
OUT = ROOT / "data" / "dataset"
OUT.mkdir(parents=True, exist_ok=True)


QUERIES = {
    "eval_results": """
        SELECT er.id,
               er.model_name,
               mg.slug   AS model_generation_slug,
               l.slug    AS lab_slug,
               d.slug    AS document_slug,
               bd.slug   AS benchmark_slug,
               bd.name   AS benchmark_name,
               bd.category AS benchmark_category,
               er.split,
               er.score,
               er.state,
               er.method,
               er.shot_count,
               er.training_state,
               er.language,
               er.metric_path,
               er.variant,
               er.is_self_reported,
               er.extraction_protocol_version,
               er.source_type
        FROM eval_results er
        JOIN benchmark_definitions bd ON bd.id = er.benchmark_id
        JOIN document_versions dv     ON dv.id = er.document_version_id
        JOIN documents d              ON d.id  = dv.document_id
        JOIN labs l                   ON l.id  = d.lab_id
        LEFT JOIN model_generations mg ON mg.id = er.generation_id
        ORDER BY er.id
    """,
    "benchmarks": """
        SELECT slug, name, category, metric_unit, policy_note
        FROM benchmark_definitions
        ORDER BY slug
    """,
    "models": """
        SELECT mg.slug, mg.name, mg.version_label, l.slug AS lab_slug,
               mg.release_date, d.slug AS document_slug
        FROM model_generations mg
        JOIN documents d ON d.id = mg.document_id
        JOIN labs l      ON l.id = d.lab_id
        ORDER BY mg.release_date NULLS LAST, mg.slug
    """,
    "labs": """
        SELECT slug, name, color_hex, website
        FROM labs
        ORDER BY slug
    """,
    "documents": """
        SELECT d.slug, d.title, d.doc_type, l.slug AS lab_slug, d.source_url,
               d.updated_at,
               (SELECT word_count FROM document_versions
                WHERE document_id = d.id ORDER BY version_date DESC LIMIT 1) AS word_count_latest
        FROM documents d
        JOIN labs l ON l.id = d.lab_id
        ORDER BY d.slug
    """,
}


def export_table(name: str, query: str, cur) -> tuple[int, str]:
    cur.execute(query)
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()

    # CSV
    csv_path = OUT / f"{name}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([
                json.dumps(v, default=str) if isinstance(v, (dict, list)) else
                (v if v is not None else "")
                for v in r
            ])

    # JSON (typed)
    json_path = OUT / f"{name}.json"
    json_rows = []
    for r in rows:
        d = {}
        for k, v in zip(cols, r):
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            else:
                d[k] = v
        json_rows.append(d)
    with json_path.open("w") as f:
        json.dump(json_rows, f, indent=2, default=str)

    # Fingerprint
    h = hashlib.sha256(csv_path.read_bytes()).hexdigest()[:16]
    return len(rows), h


def main():
    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        stats = {}
        for name, query in QUERIES.items():
            n, h = export_table(name, query, cur)
            stats[name] = (n, h)
            print(f"  {name:15s}  {n:>5d} rows  sha256:{h}")

    # Concatenated fingerprint over all CSVs (stable order)
    concat = hashlib.sha256()
    for name in QUERIES.keys():
        concat.update((OUT / f"{name}.csv").read_bytes())
    corpus_hash = concat.hexdigest()
    print(f"\ncorpus sha256: {corpus_hash}")

    # Write README
    today = datetime.now(timezone.utc).date().isoformat()
    readme = OUT / "README.md"
    readme.write_text(README_TEMPLATE.format(
        date=today,
        corpus_hash=corpus_hash,
        rows_eval=stats["eval_results"][0],
        rows_bench=stats["benchmarks"][0],
        rows_models=stats["models"][0],
        rows_labs=stats["labs"][0],
        rows_docs=stats["documents"][0],
    ))
    print(f"\nwrote {readme}")


README_TEMPLATE = """# modelcards.net — public dataset

A snapshot of the modelcards.net evaluation corpus, exported as flat
CSV and typed JSON files. Five tables, no nesting, joinable on slug
columns.

- **Snapshot date:** {date}
- **Corpus SHA256:** `{corpus_hash}`
- **License:** CC-BY 4.0 (data extracted from public model cards;
  attribution to modelcards.net + original lab)

## Files

| file | rows | what's in it |
|---|---|---|
| `eval_results.csv` / `.json` | {rows_eval} | every (model, benchmark) scored row — the fact table |
| `benchmarks.csv` / `.json`   | {rows_bench} | benchmark definitions, categories, and policy notes |
| `models.csv` / `.json`       | {rows_models} | canonical model generations linked to their cards |
| `labs.csv` / `.json`         | {rows_labs} | lab metadata and brand color |
| `documents.csv` / `.json`    | {rows_docs} | model card identity (titles, source URLs, word counts) |

## Schema

### eval_results

The fact table. One row per scored evaluation in our corpus.

| column | type | notes |
|---|---|---|
| id | int | internal row id |
| model_name | str | the model name as reported in the source card |
| model_generation_slug | str \\| null | canonical generation slug from `models.csv` |
| lab_slug | str | foreign key into `labs.csv` |
| document_slug | str | foreign key into `documents.csv` |
| benchmark_slug | str | foreign key into `benchmarks.csv` |
| benchmark_name | str | display name |
| benchmark_category | str | e.g. coding, reasoning, multimodal, safety |
| split | str \\| null | sub-task within benchmark (verified, diamond, etc.) |
| score | float \\| null | numeric score; null when state != "scored" |
| state | str | "scored", "mentioned", or "cited" |
| method | str \\| null | sampling/prompting method (CoT, extended-thinking, etc.) |
| shot_count | int \\| null | 0 for zero-shot, 5 for 5-shot, etc. |
| training_state | str \\| null | "pretrained", "instruction-tuned", "RLHF", etc. |
| language | str \\| null | for multilingual benchmarks |
| metric_path | str \\| null | the scoring rule (accuracy, f1, pass_at_1, etc.) |
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
| policy_note | json | {{ measures, caveat, intended_for, how_to_read, topic_tags, sources }} |

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

> modelcards.net evaluation corpus, snapshot {date}, corpus sha256
> {corpus_hash}. Available at modelcards.net.

And cite the upstream model cards individually using the URLs in
`documents.csv`.
"""


if __name__ == "__main__":
    main()
