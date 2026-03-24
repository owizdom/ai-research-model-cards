# Model Card Explorer

Explore and compare AI model cards, safety evaluations, and governance data across major AI labs. Extract structured benchmark data from cards and track how disclosure practices evolve over time.

## What it does

**Document collection**
- Fetches model cards, system prompts, usage policies, and safety frameworks from OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, Cohere, xAI, Amazon, and AI21
- Tracks changes over time via content-hash deduplication
- Pulls historical snapshots from the Wayback Machine (CDX API)
- Runs nightly at 2am UTC; full history sweep every Sunday at 4am

**Safety coverage analysis**
- Embeds every document version with `all-mpnet-base-v2` (768-dim, local, no API calls)
- Maps documents to 15 safety taxonomy categories via cosine similarity
- Computes a lab x category coverage matrix — which labs cover which topics, who covers everything, who covers nothing

**Eval extraction**
- LLM-based extraction of benchmark results from model cards (MMLU, HumanEval, GSM8K, etc.)
- Structured storage of scores, variants, and metrics per benchmark
- Model family and generation tracking for cross-generation comparison
- Over-time trend analysis of eval disclosure practices

## Architecture

```
apps/
  api/        FastAPI — REST API, coverage queries, eval data
  collector/  APScheduler — document fetching + Wayback Machine history
  worker/     Embedding pipeline + eval extraction (CPU-heavy, isolated)
  web/        Next.js 15 — document browser, coverage heatmap, eval explorer

packages/
  db/         Shared SQLAlchemy models, Alembic migrations, pgvector

data/
  taxonomy/       15 safety categories (YAML)
  benchmarks/     Known benchmark definitions (YAML)
  model_families/ Model family and generation mappings (YAML)

infra/
  compose/    Docker Compose (base + dev overlay)

scripts/
  seed_db.py       Seeds taxonomy, benchmarks, model families
  extract_evals.py Triggers eval extraction on existing cards
  migrate.sh       Runs Alembic migrations
  dev_setup.sh     Full local bootstrap
```

## Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 + pgvector |
| Cache / Queues | Redis 7 |
| API | FastAPI + SQLAlchemy async |
| Embeddings | sentence-transformers `all-mpnet-base-v2` (local) |
| Eval extraction | Claude Sonnet via litellm |
| Scheduling | APScheduler |
| Frontend | Next.js 15, TanStack Query, Tailwind CSS |

## Quickstart

```bash
# 1. Clone and copy env
cp .env.example .env
# Fill in API keys (ANTHROPIC_API_KEY for eval extraction)

# 2. Bootstrap (starts DB + Redis via Docker, migrates, seeds)
make setup

# 3. Run all services with hot reload
make dev
```

Services:
- **Web UI**: http://localhost:3000
- **API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

## API endpoints

```
GET  /api/v1/labs                          List labs
GET  /api/v1/labs/{slug}/documents         Documents for a lab
GET  /api/v1/documents                     All documents (filter: lab, doc_type, search)
GET  /api/v1/documents/{id}                Document detail + version history
GET  /api/v1/analysis/intersection         Coverage matrix (lab x safety category)
GET  /api/v1/evals/benchmarks              List known benchmarks
GET  /api/v1/evals/results                 Eval results (filter: document, generation, benchmark)
GET  /api/v1/evals/results/by-document/{id}  All evals from a document
GET  /api/v1/evals/compare/generations     Compare evals across model generations
GET  /api/v1/evals/timeline                Eval count over time per lab
GET  /api/v1/families                      List model families
GET  /api/v1/families/{slug}               Family detail with generations
POST /api/v1/evals/extract/{version_id}    Trigger eval extraction
```

## Tracked sources

| Lab | Documents |
|---|---|
| OpenAI | System cards (GPT-4, 4o, 4.5, 5), model spec, preparedness framework |
| Anthropic | Model cards (Claude 3, 3.5, 4, 4.5), usage policy, responsible scaling policy |
| Google DeepMind | Gemini technical reports, prohibited use policy, frontier safety framework |
| Meta AI | Llama model cards (3, 3.1, 3.3), acceptable use policy, Purple Llama |
| Mistral AI | Model cards, usage policy, guardrailing docs |
| xAI | Grok 4 card, risk framework, usage policy |
| Cohere | Usage guidelines, Command R+ card |
| Amazon | Bedrock responsible ML, docs |
| AI21 | Terms, Jamba card |
