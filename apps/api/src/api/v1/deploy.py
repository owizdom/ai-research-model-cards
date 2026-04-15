"""Deployment Buyer View — sector-specific benchmark coverage per lab."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.deps import get_db

router = APIRouter()

SECTORS = {
    "healthcare": {
        "label": "Healthcare",
        "description": "Benchmarks for clinical decision support, medical QA, and health safety",
        "benchmarks": [
            {"name": "MedQA", "description": "US Medical Licensing Exam questions (USMLE-style)", "vals_url": "https://www.vals.ai/benchmarks/medqa"},
            {"name": "PubMedQA", "description": "Biomedical research question answering", "vals_url": None},
            {"name": "MedMCQA", "description": "Medical entrance exam multiple-choice questions", "vals_url": None},
            {"name": "HealthBench", "description": "OpenAI's health conversation evaluation (vendor-published)", "vals_url": None},
            {"name": "USMLE", "description": "United States Medical Licensing Examination references", "vals_url": None},
            {"name": "MMLU Clinical Knowledge", "description": "MMLU clinical knowledge subset", "vals_url": None},
        ],
    },
    "legal": {
        "label": "Legal",
        "description": "Benchmarks for legal reasoning, contract analysis, and compliance",
        "benchmarks": [
            {"name": "LegalBench", "description": "162 legal reasoning tasks from legal professionals", "vals_url": "https://www.vals.ai/benchmarks/legal_bench"},
            {"name": "CUAD", "description": "Contract Understanding Atticus Dataset — contract clause identification", "vals_url": None},
        ],
    },
    "finance": {
        "label": "Finance",
        "description": "Benchmarks for financial reasoning and quantitative analysis",
        "benchmarks": [
            {"name": "FinQA", "description": "Financial QA from S&P 500 earnings reports", "vals_url": None},
        ],
    },
    "government": {
        "label": "Government & Public Sector",
        "description": "Benchmarks for bias, multilingual support, factual accuracy, and content safety",
        "benchmarks": [
            {"name": "BBQ", "description": "Bias Benchmark for QA — social stereotyping across 9 categories", "vals_url": None},
            {"name": "TruthfulQA", "description": "Truthfulness and factual accuracy under adversarial prompting", "vals_url": None},
            {"name": "ToxiGen", "description": "Implicit toxic language generation across 13 demographic groups", "vals_url": None},
            {"name": "MGSM", "description": "Multilingual Grade School Math — reasoning across 10 languages", "vals_url": None},
            {"name": "FLORES", "description": "Machine translation benchmark across 200+ languages", "vals_url": None},
        ],
    },
    "education": {
        "label": "Education",
        "description": "Benchmarks for factual accuracy, safety around minors, and multilingual support in educational contexts",
        "benchmarks": [
            {"name": "TruthfulQA", "description": "Truthfulness and factual accuracy under adversarial prompting", "vals_url": None},
            {"name": "XSTest", "description": "Exaggerated safety — tests whether models over-refuse safe requests", "vals_url": None},
            {"name": "MGSM", "description": "Multilingual Grade School Math — reasoning across 10 languages", "vals_url": None},
            {"name": "MMLU", "description": "Massive Multitask Language Understanding — 57 academic subjects", "vals_url": None},
            {"name": "GSM8K", "description": "Grade school math — numerical reasoning baseline", "vals_url": None},
        ],
    },
}


@router.get("/sectors")
async def list_sectors():
    """List available deployment sectors."""
    return [
        {"slug": slug, "label": s["label"], "description": s["description"],
         "benchmark_count": len(s["benchmarks"])}
        for slug, s in SECTORS.items()
    ]


@router.get("/{sector}")
async def get_sector_coverage(sector: str, db: AsyncSession = Depends(get_db)):
    """Get per-lab benchmark coverage for a specific deployment sector."""
    if sector not in SECTORS:
        raise HTTPException(404, f"Unknown sector: {sector}. Available: {list(SECTORS.keys())}")

    sector_data = SECTORS[sector]
    benchmark_names = [b["name"] for b in sector_data["benchmarks"]]

    # Get all labs
    labs_result = await db.execute(text(
        "SELECT id, slug, name, color_hex FROM labs ORDER BY name"
    ))
    labs = [dict(r._mapping) for r in labs_result.fetchall()]

    # Batch: aggregate content per lab, then check each benchmark with server-side regex
    bench_cases = []
    for bench in benchmark_names:
        safe = bench.replace("'", "''")
        bench_cases.append(
            f"CASE WHEN lab_content ~* '\\m{safe}\\M' THEN '{safe}' END"
        )

    unnest_expr = ", ".join(bench_cases)

    result = await db.execute(text(f"""
        WITH lab_content AS (
            SELECT l.slug AS lab_slug, string_agg(dv.content_md, ' ') AS lab_content
            FROM labs l
            JOIN documents d ON d.lab_id = l.id
            JOIN document_versions dv ON dv.document_id = d.id
            WHERE d.doc_type = 'model_card' AND dv.content_md IS NOT NULL
              AND LENGTH(dv.content_md) < 500000
            GROUP BY l.slug
        )
        SELECT lab_slug, unnest(ARRAY[{unnest_expr}]) AS benchmark
        FROM lab_content
    """))

    # Build lab → set of found benchmarks
    lab_found = {}
    for row in result.fetchall():
        lab_slug, bench = row[0], row[1]
        if bench is not None:
            lab_found.setdefault(lab_slug, set()).add(bench)

    # Build the response
    lab_coverage = []
    for lab in labs:
        found = lab_found.get(lab["slug"], set())
        benchmarks_status = []
        for bench_info in sector_data["benchmarks"]:
            benchmarks_status.append({
                "name": bench_info["name"],
                "description": bench_info["description"],
                "reported": bench_info["name"] in found,
                "vals_url": bench_info.get("vals_url"),
            })
        lab_coverage.append({
            "slug": lab["slug"],
            "name": lab["name"],
            "color_hex": lab["color_hex"],
            "benchmarks": benchmarks_status,
            "reported_count": sum(1 for b in benchmarks_status if b["reported"]),
            "total_count": len(benchmarks_status),
        })

    # Sort: most coverage first
    lab_coverage.sort(key=lambda x: -x["reported_count"])

    # Summary stats
    labs_with_any = sum(1 for lc in lab_coverage if lc["reported_count"] > 0)

    return {
        "sector": sector,
        "label": sector_data["label"],
        "description": sector_data["description"],
        "benchmarks": sector_data["benchmarks"],
        "lab_coverage": lab_coverage,
        "summary": {
            "total_labs": len(labs),
            "labs_with_any_coverage": labs_with_any,
            "total_benchmarks": len(benchmark_names),
        },
    }
