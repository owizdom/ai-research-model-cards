#!/usr/bin/env python3
"""Compute canonical corpus stats from the live DB into data/stats.json.

This is the single place the corpus counts come from. The prose docs
(README, METHODOLOGY, ARCHITECTURE) are hand-synced to this file; regenerate
after any corpus change so the numbers in those docs stop drifting:

  python3 scripts/compute_stats.py

Read-only. Prints a summary and writes data/stats.json. Does not touch the
docs and does not write to the DB.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
OUT = ROOT / "data" / "stats.json"

# Labs that appear in earlier snapshots / older docs but are not in the
# current corpus. Kept explicit so "9 labs" history isn't silently erased.
RETIRED_LABS = ["cohere", "amazon", "ai21"]


def scalar(cur, sql):
    cur.execute(sql)
    row = cur.fetchone()
    return row[0] if row else None


def kv(cur, sql):
    cur.execute(sql)
    return {("(none)" if k is None else str(k)): v for k, v in cur.fetchall()}


def main():
    conn = psycopg2.connect(DB_URL)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30s'")

    corpus = {
        "labs": scalar(cur, "SELECT COUNT(*) FROM labs"),
        "documents": scalar(cur, "SELECT COUNT(*) FROM documents"),
        "document_versions": scalar(cur, "SELECT COUNT(*) FROM document_versions"),
        "benchmarks": scalar(cur, "SELECT COUNT(*) FROM benchmark_definitions"),
        "benchmarks_curated": scalar(cur, "SELECT COUNT(*) FROM benchmark_definitions WHERE category <> 'other'"),
        "benchmarks_auto_created": scalar(cur, "SELECT COUNT(*) FROM benchmark_definitions WHERE category = 'other'"),
        "benchmarks_with_evals": scalar(cur, "SELECT COUNT(DISTINCT benchmark_id) FROM eval_results"),
        "benchmarks_with_policy_note": scalar(cur, "SELECT COUNT(*) FROM benchmark_definitions WHERE policy_note IS NOT NULL"),
        "evals": scalar(cur, "SELECT COUNT(*) FROM eval_results"),
        "evals_scored": scalar(cur, "SELECT COUNT(*) FROM eval_results WHERE state='scored'"),
        "evals_mentioned": scalar(cur, "SELECT COUNT(*) FROM eval_results WHERE state='mentioned'"),
        "evals_cited": scalar(cur, "SELECT COUNT(*) FROM eval_results WHERE state='cited'"),
        "model_families": scalar(cur, "SELECT COUNT(*) FROM model_families"),
        "model_generations": scalar(cur, "SELECT COUNT(*) FROM model_generations"),
        "taxonomy_categories": scalar(cur, "SELECT COUNT(*) FROM taxonomy_categories"),
        "taxonomy_mappings": scalar(cur, "SELECT COUNT(*) FROM document_taxonomy_mappings"),
    }

    docs_by_type = kv(cur, "SELECT doc_type, COUNT(*) FROM documents GROUP BY 1 ORDER BY 2 DESC")
    docs_by_lab = kv(cur, """
        SELECT l.slug, COUNT(d.id) FROM labs l
        LEFT JOIN documents d ON d.lab_id = l.id GROUP BY l.slug ORDER BY 2 DESC""")
    evals_by_lab = kv(cur, """
        SELECT l.slug, COUNT(*) FROM eval_results er
        JOIN document_versions dv ON dv.id = er.document_version_id
        JOIN documents d ON d.id = dv.document_id
        JOIN labs l ON l.id = d.lab_id GROUP BY l.slug ORDER BY 2 DESC""")
    evals_by_state = kv(cur, "SELECT state, COUNT(*) FROM eval_results GROUP BY 1 ORDER BY 2 DESC")
    evals_by_protocol = kv(cur, "SELECT extraction_protocol_version, COUNT(*) FROM eval_results GROUP BY 1 ORDER BY 1")
    evals_by_domain = kv(cur, """
        SELECT bd.industry_domain, COUNT(*) FROM eval_results er
        JOIN benchmark_definitions bd ON bd.id = er.benchmark_id
        GROUP BY 1 ORDER BY 2 DESC""")
    extractor_models = kv(cur, """
        SELECT model_used, COUNT(*) FROM extraction_runs
        WHERE status='completed' AND COALESCE(evals_extracted,0) > 0
        GROUP BY 1 ORDER BY 2 DESC""")

    # Raw (NOT family-collapsed) single-lab fragmentation, as a sanity anchor.
    # The site headline (276/311) uses family-collapsed names via the
    # /api/v1/evals/fragmentation endpoint; that collapse is not reproduced here.
    cur.execute("""
        SELECT SUM(CASE WHEN labs=1 THEN 1 ELSE 0 END), COUNT(*)
        FROM (SELECT er.benchmark_id, COUNT(DISTINCT d.lab_id) AS labs
              FROM eval_results er
              JOIN document_versions dv ON dv.id = er.document_version_id
              JOIN documents d ON d.id = dv.document_id
              GROUP BY er.benchmark_id) t""")
    single_lab, bench_with_evals = cur.fetchone()
    snapshot = scalar(cur, "SELECT MAX(extracted_at) FROM eval_results")

    cur.close()
    conn.close()

    current_labs = sorted(docs_by_lab.keys())
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "live Railway DB (read-only)",
        "data_snapshot": snapshot.isoformat() if snapshot else None,
        "scope": {
            "current_labs": current_labs,
            "retired_labs": RETIRED_LABS,
            "note": "cohere/amazon/ai21 appear in earlier snapshots and older "
                    "docs but are not in the current corpus. The current DB is "
                    f"{corpus['labs']} labs.",
        },
        "corpus": corpus,
        "documents_by_type": docs_by_type,
        "documents_by_lab": docs_by_lab,
        "evals_by_lab": evals_by_lab,
        "evals_by_state": evals_by_state,
        "evals_by_protocol_version": evals_by_protocol,
        "evals_by_industry_domain": evals_by_domain,
        "extractor_models_in_prod": extractor_models,
        "fragmentation_raw": {
            "benchmarks_with_evals": bench_with_evals,
            "single_lab": single_lab,
            "single_lab_pct": round(single_lab / bench_with_evals, 4) if bench_with_evals else None,
            "note": "Raw, not family-collapsed. Site headline uses family-collapsed "
                    "names (276/311) via /api/v1/evals/fragmentation.",
        },
    }

    OUT.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"wrote {OUT}\n")
    print(f"snapshot: {stats['data_snapshot']}")
    print(f"labs={corpus['labs']} docs={corpus['documents']} versions={corpus['document_versions']} "
          f"benchmarks={corpus['benchmarks']} (with_evals={corpus['benchmarks_with_evals']}, "
          f"policy_notes={corpus['benchmarks_with_policy_note']})")
    print(f"evals={corpus['evals']} (scored={corpus['evals_scored']}, "
          f"mentioned={corpus['evals_mentioned']}, cited={corpus['evals_cited']})")
    print(f"families={corpus['model_families']} generations={corpus['model_generations']} "
          f"taxonomy_categories={corpus['taxonomy_categories']} taxonomy_mappings={corpus['taxonomy_mappings']}")
    print(f"docs_by_type={docs_by_type}")
    print(f"evals_by_lab={evals_by_lab}")
    print(f"evals_by_domain={evals_by_domain}")
    print(f"extractor_models={extractor_models}")
    print(f"raw single-lab: {single_lab}/{bench_with_evals} = {stats['fragmentation_raw']['single_lab_pct']}")


if __name__ == "__main__":
    main()
