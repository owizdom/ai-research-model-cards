"""Research Data Export — downloadable CSV datasets for academic research."""
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from packages.pipeline_config import (
    COVERAGE_BAND_MODERATE,
    COVERAGE_BAND_STRONG,
    COVERAGE_BAND_WEAK,
)
from src.core.deps import get_db

router = APIRouter()


def csv_response(filename: str, rows: list[dict]) -> StreamingResponse:
    if not rows:
        buf = io.StringIO("No data\n")
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/eval-results.csv")
async def export_eval_results(db: AsyncSession = Depends(get_db)):
    """Export all extracted eval results with model name, dates, and metrics."""
    result = await db.execute(text("""
        SELECT
            l.name AS lab,
            l.slug AS lab_slug,
            d.title AS document,
            d.doc_type,
            d.source_url,
            dv.version_date AS document_version_date,
            dv.id AS document_version_id,
            mg.name AS model_name,
            mg.slug AS model_slug,
            bd.name AS benchmark,
            bd.category AS benchmark_category,
            bd.metric_name,
            bd.metric_unit,
            er.score,
            er.variant,
            er.is_self_reported,
            er.source_type,
            er.extracted_at
        FROM eval_results er
        JOIN document_versions dv ON dv.id = er.document_version_id
        JOIN documents d ON d.id = dv.document_id
        JOIN labs l ON l.id = d.lab_id
        JOIN benchmark_definitions bd ON bd.id = er.benchmark_id
        LEFT JOIN model_generations mg ON mg.id = er.generation_id
        ORDER BY l.name, d.title, bd.name
    """))
    rows = [dict(r._mapping) for r in result.fetchall()]
    return csv_response("model-card-eval-results.csv", rows)


@router.get("/taxonomy-coverage.csv")
async def export_taxonomy_coverage(db: AsyncSession = Depends(get_db)):
    """Export per-lab x per-safety-category coverage scores."""
    result = await db.execute(text("""
        SELECT
            l.name AS lab,
            l.slug AS lab_slug,
            tc.name AS safety_category,
            ROUND(MAX(dtm.similarity_score)::numeric, 3) AS embedding_similarity,
            CASE
                WHEN MAX(dtm.similarity_score) >= """ + str(COVERAGE_BAND_STRONG) + """ THEN 'A'
                WHEN MAX(dtm.similarity_score) >= """ + str(COVERAGE_BAND_MODERATE) + """ THEN 'B'
                WHEN MAX(dtm.similarity_score) >= """ + str(COVERAGE_BAND_WEAK) + """ THEN 'C'
                ELSE '-'
            END AS grade
        FROM labs l
        CROSS JOIN taxonomy_categories tc
        LEFT JOIN document_taxonomy_mappings dtm ON dtm.taxonomy_category_id = tc.id
        LEFT JOIN document_versions dv ON dv.id = dtm.document_version_id
        LEFT JOIN documents d ON d.id = dv.document_id AND d.lab_id = l.id
        GROUP BY l.name, l.slug, tc.name
        ORDER BY l.name, tc.name
    """))
    rows = [dict(r._mapping) for r in result.fetchall()]
    return csv_response("model-card-taxonomy-coverage.csv", rows)


@router.get("/benchmark-coverage.csv")
async def export_benchmark_coverage(db: AsyncSession = Depends(get_db)):
    """Export per-lab benchmark mention matrix (1/0 format for econometric tools)."""

    BENCHMARKS = [
        "MMLU", "GPQA", "MATH", "GSM8K", "HumanEval", "MBPP", "SWE-bench",
        "MMMU", "BBH", "ARC", "HellaSwag", "WinoGrande", "IFEval", "AIME",
        "BBQ", "ToxiGen", "XSTest", "TruthfulQA", "RealToxicityPrompts",
        "MedQA", "PubMedQA", "MedMCQA", "HealthBench", "USMLE",
        "LegalBench", "CUAD", "FinQA",
        "MGSM", "FLORES", "XNLI", "MMMLU",
        "TriviaQA", "Natural Questions", "FEVER",
        "ChartQA", "DocVQA", "MathVista", "LiveCodeBench", "BrowseComp",
    ]

    # Some benchmarks have aliases (e.g., BBH = "BIG-Bench Hard")
    ALIASES = {
        "BBH": "BBH|BIG-Bench.Hard",
        "ARC": "ARC|ARC-Challenge",
        "SWE-bench": "SWE-bench|SWE.bench",
    }

    bench_cases = []
    for bench in BENCHMARKS:
        safe = bench.replace("'", "''")
        pattern = ALIASES.get(bench, safe)
        bench_cases.append(
            f"CASE WHEN lab_content ~* '\\m({pattern})\\M' THEN 1 ELSE 0 END AS \"{safe}\""
        )

    cols = ", ".join(bench_cases)

    result = await db.execute(text(f"""
        WITH lab_content AS (
            SELECT l.slug AS lab_slug, l.name AS lab_name,
                   string_agg(dv.content_md, ' ') AS lab_content
            FROM labs l
            JOIN documents d ON d.lab_id = l.id
            JOIN document_versions dv ON dv.document_id = d.id
            WHERE d.doc_type = 'model_card' AND dv.content_md IS NOT NULL
              AND LENGTH(dv.content_md) < 500000
            GROUP BY l.slug, l.name
        )
        SELECT lab_slug, lab_name, {cols}
        FROM lab_content
        ORDER BY lab_name
    """))

    rows = [dict(r._mapping) for r in result.fetchall()]
    return csv_response("model-card-benchmark-coverage.csv", rows)


@router.get("/codebook.csv")
async def export_codebook(db: AsyncSession = Depends(get_db)):
    """Data dictionary for all exported CSV files."""
    codebook = [
        {"file": "eval-results.csv", "column": "lab", "type": "string", "description": "AI lab name"},
        {"file": "eval-results.csv", "column": "lab_slug", "type": "string", "description": "Lab identifier (lowercase, URL-safe)"},
        {"file": "eval-results.csv", "column": "document", "type": "string", "description": "Model card or system card title"},
        {"file": "eval-results.csv", "column": "doc_type", "type": "string", "description": "Document type: model_card, constitution, usage_policy"},
        {"file": "eval-results.csv", "column": "source_url", "type": "url", "description": "Original URL of the model card"},
        {"file": "eval-results.csv", "column": "document_version_date", "type": "date", "description": "Date the document version was collected (may differ from publication date)"},
        {"file": "eval-results.csv", "column": "document_version_id", "type": "integer", "description": "Internal version ID for reproducibility"},
        {"file": "eval-results.csv", "column": "model_name", "type": "string", "description": "Specific model name if linked to a generation (e.g., Claude 3 Opus). NULL if not linked."},
        {"file": "eval-results.csv", "column": "benchmark", "type": "string", "description": "Benchmark name as extracted from the model card"},
        {"file": "eval-results.csv", "column": "benchmark_category", "type": "string", "description": "Benchmark category: knowledge, reasoning, coding, math, safety, vision, etc."},
        {"file": "eval-results.csv", "column": "metric_name", "type": "string", "description": "Metric type (accuracy, pass@1, elo, etc.). NULL if not defined."},
        {"file": "eval-results.csv", "column": "metric_unit", "type": "string", "description": "Metric unit (%, points, etc.). NULL if not defined."},
        {"file": "eval-results.csv", "column": "score", "type": "float", "description": "Benchmark score as extracted. Units vary by benchmark."},
        {"file": "eval-results.csv", "column": "variant", "type": "string", "description": "Benchmark variant or evaluation setting (e.g., 5-shot, 0-shot CoT, pass@1)"},
        {"file": "eval-results.csv", "column": "is_self_reported", "type": "boolean", "description": "Whether the score was self-reported by the lab (always True in this dataset)"},
        {"file": "eval-results.csv", "column": "source_type", "type": "string", "description": "Source of the eval: model_card"},
        {"file": "eval-results.csv", "column": "extracted_at", "type": "datetime", "description": "When our pipeline extracted this score (NOT the publication date)"},
        {"file": "taxonomy-coverage.csv", "column": "embedding_similarity", "type": "float", "description": "Cosine similarity between document embedding and safety category embedding (all-mpnet-base-v2, first 8000 chars). NOT an evaluation score."},
        {"file": "taxonomy-coverage.csv", "column": "grade", "type": "string", "description": "A (>0.50), B (0.35-0.50), C (0.20-0.35), - (<0.20). Based on embedding similarity, not human judgment."},
        {"file": "benchmark-coverage.csv", "column": "[benchmark columns]", "type": "integer", "description": "1 = benchmark name appears in at least one model card from this lab (word-boundary regex match). 0 = not found. Aggregated across all model cards per lab. Documents over 500KB excluded."},
    ]
    return csv_response("codebook.csv", codebook)
