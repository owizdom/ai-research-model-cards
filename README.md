<p align="center">
  <h1 align="center">Model Card Explorer</h1>
  <p align="center">
    The open research platform for AI model governance data.
    <br />
    <a href="https://freesystems.substack.com/">Free Systems Lab</a>
  </p>
</p>

---

Model Card Explorer collects, versions, and analyzes model cards and safety documentation from 9 major AI labs. It extracts structured benchmark data from each card and enables cross-lab, cross-generation comparisons — making it easy to see what companies disclose, what they don't, and how transparency is evolving over time.

## Features

### Document Collection
- Automated collection of model cards, usage policies, and safety frameworks from **OpenAI, Anthropic, Google DeepMind, Meta, Mistral, xAI, Cohere, Amazon,** and **AI21**
- Content-hash deduplication with full version history
- Historical snapshots via the Wayback Machine CDX API
- Nightly collection at 2am UTC; weekly history sweep Sundays at 4am

### Safety Coverage Analysis
- Semantic embedding of every document with `all-mpnet-base-v2` (768-dim, runs locally)
- Coverage mapping across 15 safety taxonomy categories (bias, child safety, dual-use, mental health, etc.)
- Lab-by-category heatmap showing who covers what — and where the industry has critical gaps

### Eval Extraction
- LLM-powered extraction of benchmark results from model cards (MMLU, HumanEval, GSM8K, SWE-bench, and more)
- Structured storage of scores, variants, and metrics per benchmark
- Model family and generation tracking (Claude 3 → 4, GPT-4 → 5, etc.)
- Per-card eval counts over time to track whether disclosure is increasing

### Model Family Comparison
- Cross-generation benchmark tables showing score progression
- Side-by-side comparison within families (e.g., all Claude generations)
- Delta tracking between consecutive generations

## Architecture

```
apps/
├── api/          FastAPI REST API — documents, coverage, evals, families
├── collector/    APScheduler — document fetching + Wayback Machine history
├── worker/       Embedding pipeline + LLM eval extraction
└── web/          Next.js 15 — interactive dashboard and explorer

packages/
└── db/           SQLAlchemy models, Alembic migrations, pgvector

data/
├── taxonomy/         15 safety categories (YAML)
├── benchmarks/       Benchmark definitions (YAML)
└── model_families/   Model family + generation mappings (YAML)

infra/
└── compose/      Docker Compose (base + dev overlay)
```

**Data flow:**
```
Collector → Redis (embed_jobs) → Worker embeds + maps taxonomy
                                        ↓
                                 Redis (extract_jobs) → Worker extracts evals via LLM
                                        ↓
                                   PostgreSQL ← API ← Next.js frontend
```

## Tech Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 + pgvector |
| Queues | Redis 7 |
| API | FastAPI, SQLAlchemy async, Pydantic |
| Embeddings | sentence-transformers (`all-mpnet-base-v2`, local) |
| Eval Extraction | litellm (Groq, Gemini, or Claude) |
| Scheduling | APScheduler |
| Frontend | Next.js 15, React 19, Recharts, Tailwind CSS |
| Typography | DM Sans + Source Serif 4 |

## Getting Started

### Prerequisites
- Docker & Docker Compose
- At least one LLM API key for eval extraction (Groq, Gemini, or Anthropic)

### Setup

```bash
# Clone
git clone https://github.com/owizdom/ai-research-model-cards.git
cd ai-research-model-cards

# Configure environment
cp .env.example .env
# Add your API keys to .env

# Bootstrap (DB + Redis + migrations + seed data)
make setup

# Start all services with hot reload
make dev
```

### Services

| Service | URL |
|---|---|
| Web UI | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

### Common Commands

```bash
make setup        # First-time setup
make dev          # All services with hot reload
make migrate      # Run Alembic migrations
make seed         # Re-seed taxonomy, benchmarks, model families
make down         # Stop everything
```

## API Reference

### Documents & Labs
```
GET  /api/v1/labs                              List all tracked labs
GET  /api/v1/labs/{slug}                       Lab detail with documents
GET  /api/v1/documents                         List documents (filter: lab, doc_type, search)
GET  /api/v1/documents/{id}                    Document with version history
GET  /api/v1/documents/{id}/diff               Diff two document versions
```

### Coverage Analysis
```
GET  /api/v1/analysis/intersection             Lab × category coverage matrix
GET  /api/v1/analysis/intersection/temporal     Coverage convergence over time
```

### Eval Data
```
GET  /api/v1/evals/benchmarks                  List known benchmarks
GET  /api/v1/evals/results                     Query eval results (filter by lab, doc, benchmark)
GET  /api/v1/evals/results/by-document/{id}    All evals extracted from a document
GET  /api/v1/evals/compare/generations         Compare benchmarks across model generations
GET  /api/v1/evals/per-card                    Per-card eval counts with dates
GET  /api/v1/evals/timeline                    Eval count over time per lab
GET  /api/v1/evals/depth                       Eval counts by category × lab
POST /api/v1/evals/extract/{version_id}        Trigger extraction for a document version
```

### Model Families
```
GET  /api/v1/families                          List model families
GET  /api/v1/families/{slug}                   Family detail with generations and eval counts
```

## Tracked Sources

| Lab | Count | Documents |
|---|---|---|
| **Anthropic** | 11 | Claude 3/3.5/4/4.5 system cards, usage policy, RSP, constitutional AI |
| **OpenAI** | 9 | GPT-4/4o/4.5/5 system cards, model spec, preparedness framework |
| **Google DeepMind** | 7 | Gemini 1.0/1.5 reports, AI principles, frontier safety framework |
| **Meta AI** | 9 | Llama 3/3.1/3.3 cards, Purple Llama, Llama Guard cards |
| **Mistral AI** | 5 | Mixtral/7B cards, usage policy, guardrailing, moderation |
| **xAI** | 5 | Grok 4 card, risk framework, API docs, usage policy |
| **Cohere** | 3 | Command R+ card, responsible use, terms |
| **Amazon** | 2 | Bedrock responsible ML, documentation |
| **AI21** | 2 | Jamba card, terms |

## Database Schema

**Core tables:** `labs`, `documents`, `document_versions`, `taxonomy_categories`, `document_taxonomy_mappings`

**Eval tables:** `benchmark_definitions`, `eval_results`, `extraction_runs`, `model_families`, `model_generations`, `external_eval_sources`

All document versions store 768-dim embeddings via pgvector for semantic similarity search.

## Contributing

This project is open source. Contributions welcome — see the [GitHub repo](https://github.com/owizdom/ai-research-model-cards).

**Adding a new source:** Edit `apps/collector/src/collectors/registry.py` — add a `Source` entry.

**Adding a benchmark:** Edit `data/benchmarks/benchmark_definitions.yaml`, then `make seed`.

**Adding a model family:** Edit `data/model_families/families.yaml`, then `make seed`.

## License

MIT

---

<p align="center">
  Built by <a href="https://freesystems.substack.com/">Free Systems Lab</a>
</p>
