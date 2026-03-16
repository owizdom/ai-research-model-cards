# AI Policy Intelligence

Track policy documents, model cards, and system prompts from major AI labs. Analyze coverage overlap across safety categories and monitor political slant in model outputs over time.

## What it does

**Document collection**
- Fetches model cards, system prompts, usage policies, and safety frameworks from OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, Cohere, and xAI
- Tracks changes over time via content-hash deduplication
- Pulls historical snapshots from the Wayback Machine (CDX API)
- Runs nightly at 2am UTC; full history sweep every Sunday at 4am

**Intersection analysis**
- Embeds every document version with `all-mpnet-base-v2` (768-dim, local, no API calls)
- Maps documents to 15 safety taxonomy categories via cosine similarity
- Computes a lab × category coverage matrix — which labs cover which topics, who covers everything, who covers nothing, what's unique to one lab

**Political slant monitoring**
- 25 probes across elections, immigration, guns, climate, foreign policy, healthcare, criminal justice, and tech policy
- Runs each probe against 10+ models (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro, Llama 3 70B, Mistral Large, Command R+, Grok, and more) via litellm
- Composite slant score (3 methods):
  - **50%** — Embedding cosine similarity vs liberal/conservative/neutral anchor centroids
  - **30%** — Political valence lexicon (~70 terms with [-1, 1] scores)
  - **20%** — Moral Foundations Dictionary (care, fairness, loyalty, authority, purity)
- Mann-Kendall trend test to detect drift over time
- Trump/Biden asymmetry score per model

## Architecture

```
apps/
  api/        FastAPI — REST API, intersection queries, slant analysis
  collector/  APScheduler — document fetching + Wayback Machine history
  worker/     Embedding pipeline + probe runner (CPU-heavy, isolated)
  web/        Next.js 15 — document browser, intersection heatmap, slant dashboard

packages/
  db/         Shared SQLAlchemy models, Alembic migrations, pgvector

data/
  probes/     25 political probes (YAML)
  taxonomy/   15 safety categories (YAML)
  anchors/    Liberal/conservative/neutral anchor sentences + valence lexicon

infra/
  compose/    Docker Compose (base + dev overlay)

scripts/
  seed_db.py  Seeds taxonomy, probes, AI models
  migrate.sh  Runs Alembic migrations (creates venv automatically)
  dev_setup.sh  Full local bootstrap
```

Services communicate via Redis job queues:
- `embed_jobs` — collector → worker (after new document version stored)
- `probe_runs` — API → worker (after probe run triggered)

## Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 + pgvector |
| Cache / Queues | Redis 7 |
| API | FastAPI + SQLAlchemy async |
| Embeddings | sentence-transformers `all-mpnet-base-v2` (local) |
| LLM calls | litellm (unified async client) |
| Scheduling | APScheduler |
| Frontend | Next.js 15, TanStack Query, Tailwind CSS |

## Quickstart

```bash
# 1. Clone and copy env
cp .env.example .env
# Fill in API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)

# 2. Bootstrap (starts DB + Redis via Docker, migrates, seeds)
make setup

# 3. Run all services with hot reload
make dev
```

Services:
- **Web UI**: http://localhost:3000
- **API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

## Common commands

```bash
make setup        # First-time setup (DB + Redis + migrate + seed)
make dev          # All 4 services with hot reload
make migrate      # Run Alembic migrations
make seed         # Re-seed taxonomy / probes / models
make collect      # Trigger a one-off collection run
make logs         # Tail all service logs
make down         # Stop everything
```

## API endpoints

```
GET  /api/v1/labs                          List labs
GET  /api/v1/labs/{slug}/documents         Documents for a lab
GET  /api/v1/documents                     All documents (filter: lab, doc_type, search)
GET  /api/v1/documents/{id}                Document detail + version history
GET  /api/v1/analysis/intersection         Coverage matrix (lab × safety category)
GET  /api/v1/analysis/slant/summary        Slant summary per model
GET  /api/v1/analysis/slant/series         Slant time series (model + optional probe)
GET  /api/v1/probes                        List probes
POST /api/v1/probes/runs                   Trigger a probe run
```

## Tracked sources

| Lab | Documents |
|---|---|
| OpenAI | System card, usage policies, model spec, preparedness framework |
| Anthropic | Model card, usage policy, responsible scaling policy, Claude's constitution |
| Google DeepMind | Gemini system card, prohibited use policy, frontier safety framework |
| Meta AI | Llama system card, acceptable use policy, responsible use guide |
| Mistral AI | Terms of service, usage policy |
| Cohere | Usage guidelines |
| xAI | Usage policy |

## Adding a new source

Edit `apps/collector/src/collectors/registry.py` — add a `Source` entry to `SOURCES`. Set `track_history=True` to enable Wayback Machine snapshots.

## Adding a new probe

Edit `data/probes/probes.yaml`, then run `make seed`.

## Notes on slant scoring

Scores range from **-1 (conservative)** to **+1 (liberal)**. Scores between -0.3 and +0.3 are classified as neutral. The composite score is an interpretive tool, not a definitive measurement — treat it as directional signal, not ground truth.
