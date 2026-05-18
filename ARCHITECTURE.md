# Architecture

This is the orientation doc. Read this **before** `README.md` if you've never touched the repo, or `docs/RUNBOOK.md` if you're about to add a card. Should take 10–15 minutes to absorb the whole thing.

---

## The data flow

```
   ┌────────────────────┐    nightly 02:00 UTC + manual scripts/ingest_one.py
   │   Source registry  │
   │  (collector/...)   │──────────────────────────────────────────┐
   └────────────────────┘                                          │
                                                                   ▼
                                                          ┌──────────────────┐
                                                          │   PDF/HTML/raw   │
                                                          │ fetch + parse +  │
                                                          │ size-cap (500KB) │
                                                          └────────┬─────────┘
                                                                   │ content_md
                                                                   ▼
                              ┌──────────────────────────────────────────────┐
                              │  documents + document_versions (Postgres)    │
                              │  content-hash deduped per document           │
                              └────────────────┬─────────────────────────────┘
                                               │ rpush embed_jobs
                                               ▼
                                  ┌──────────────────────────┐
                                  │  Redis embed_jobs queue  │
                                  └────────────┬─────────────┘
                                               │ worker embed thread
                                               ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │  apps/worker/src/embedder/pipeline.py                              │
   │   1. mpnet 768-dim embedding (first 8k chars)                       │
   │   2. cosine vs each TaxonomyCategory; sim ≥ 0.20 → mapping inserted │
   │   3. if doc_type == "model_card", rpush extract_jobs                │
   └────────────────────────────┬───────────────────────────────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │  Redis extract_jobs (×3) │
                  └────────────┬─────────────┘
                               │ worker extract threads (EXTRACT_WORKERS=3)
                               ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │  apps/worker/src/extractor/eval_extractor.py                       │
   │   1. pg_advisory_xact_lock(hashtext("extract:" + version_id))      │
   │   2. _extract_eval_sections() → 30 KB content window                │
   │      (anchor-boost + two-window split for >80k docs)                │
   │   3. Claude Sonnet 4.6 via `claude -p` subprocess (timeout 1200s)   │
   │   4. parse_extraction_json() — tolerant of 4 CLI output quirks     │
   │   5. ON CONFLICT DO NOTHING insert into eval_results                │
   │   6. UPDATE extraction_runs status='completed'                     │
   └────────────────────────────┬───────────────────────────────────────┘
                                │
                                ▼
                  ┌────────────────────────────┐         ┌──────────────────────┐
                  │   eval_results (Postgres)  │ ◄────── │  FastAPI (apps/api)  │
                  └────────────────────────────┘         └──────────┬───────────┘
                                                                    │
                                                                    ▼
                                                         ┌──────────────────────┐
                                                         │  Next.js (apps/web)  │
                                                         └──────────────────────┘
```

Hot paths in this order: **register a source → ingest one → embed → extract → land in DB → render**. Every layer has an idempotent re-entry point so a partial failure doesn't poison the next run.

---

## What lives where

| Top-level dir | Purpose |
|---|---|
| `apps/api/` | FastAPI service — public API + `/admin/*` operator surface. Reads-only from DB; never owns extraction. |
| `apps/collector/` | APScheduler service — fetches source URLs nightly, manages Wayback history, runs the stuck-run reaper. |
| `apps/worker/` | Async workers (embed + extract) consuming Redis queues. The only service that writes `eval_results`. |
| `apps/web/` | Next.js 15 dashboard. Reads the FastAPI surface; doesn't talk to DB or Redis directly. |
| `packages/db/` | SQLAlchemy async models + Alembic migrations + the shared engine/session. Used by all three Python services. |
| `packages/pipeline_config.py` | **Single source of truth** for cross-cutting constants — thresholds, timeouts, window sizes. See "Threshold philosophy" below. |
| `scripts/` | Operator CLIs (`ingest_one.py`, `extract_one.py`, `seed_db.py`, `dev_setup.sh`, `migrate.sh`). All invocable manually; some are also wired into `Makefile`. |
| `charts/` | Research-only chart generators for blog posts / papers. Never invoked by the running system. |
| `data/` | Seed YAML files for taxonomy, benchmarks, model families. Read by `scripts/seed_db.py`. |
| `claims/`, `external_validation/`, `docs/notes/` | Research outputs (audits, cross-checks, scratch notes). Markdown only. |
| `infra/compose/` | Docker Compose configs for local dev. |
| `docs/` | Maintainer docs (`RUNBOOK.md` for ops, `notes/` for research scratch). |

**Why apps + packages?** Python monorepo idiom — `packages/` is for code shared between services; `apps/` is per-service entry points. A flat layout would be simpler; it's on the roadmap as a separate restructure PR. For now: if it's used in two services, it belongs in `packages/`.

---

## Threshold philosophy

Every cross-cutting constant lives in [`packages/pipeline_config.py`](packages/pipeline_config.py). One docstring per constant explains what it does. The headline numbers:

| Constant | Value | What it controls |
|---|---:|---|
| `TAXONOMY_SIMILARITY_FLOOR` | 0.20 | Embedder inserts a mapping only at or above this cosine. Below = noise. |
| `COVERAGE_ANALYSIS_THRESHOLD` | 0.25 | Default for `/api/v1/analysis/intersection`; "is this category covered" yes/no. |
| `COVERAGE_BAND_STRONG` | 0.50 | CSV export grade A. |
| `COVERAGE_BAND_MODERATE` | 0.35 | CSV export grade B. |
| `COVERAGE_BAND_WEAK` | 0.20 | CSV export grade C — matches the embedder's insert floor, so everything in the DB grades at least C. |
| `WINDOW_SIZE_DEFAULT` | 30 000 | Chars sent to the Claude CLI per extraction. |
| `LONG_DOC_THRESHOLD` | 80 000 | Above this, `_extract_eval_sections` splits the budget into a front-half + back-half window. |
| `ANCHOR_BOOST` | 10 | Score added to a block that contains a capability-table anchor. Large enough to outweigh keyword-density wins from narrative-dense safety prose. |
| `CLI_TIMEOUT_DEFAULT_S` | 1200 | Default Claude CLI subprocess timeout, overridable via `CLAUDE_CLI_TIMEOUT_S` env. |
| `STUCK_RUN_THRESHOLD_MIN` | 25 | `extraction_runs` rows in `running` state past this are reaped. |
| `IDLE_TXN_TIMEOUT_MS` | 1 800 000 | Postgres-side orphan-transaction abort (30 min). |

Before the audit on 2026-05-16 these were scattered across 5+ files with 3 different values for "coverage threshold" alone. If you find a magic number that ought to be here, move it.

---

## Extraction protocol versioning

`EXTRACTION_PROTOCOL_VERSION = 2` (in `pipeline_config`).

Why a version field at all: the extractor's output schema has changed over time (sprint 1 = scored-only rows with 4 fields; sprint 2 = scored/mentioned/cited + 10 fields including state, shot_count, method). Old rows are still useful but can't be compared apples-to-apples with new ones. The version field lets v1 + v2 rows coexist; the `uq_eval_result` unique constraint includes `extraction_protocol_version` so a re-extraction under the new protocol doesn't collide with old rows.

When to bump:
- The output JSON gains or loses required fields.
- The state classifier semantics change.
- Score-range validation rules change.

When **not** to bump:
- Prompt tweaks that don't change the schema.
- Bug fixes in parsing.
- Changes to the section selector (just re-extract).

Bumping is a migration-light op: change the constant, re-run extraction. Old rows stay in the DB tagged with their version.

---

## Known gotchas

Three things that bit us and aren't bugs per se — surface area worth knowing.

### 1. API↔TS shape mismatch on documents

The Python `/api/v1/documents` endpoint returns documents with a nested `{lab: {id, slug, name, ...}}` object and `updated_at`. The TypeScript `Document` type in `apps/web/src/lib/types.ts` expects flat `lab_slug`, `lab_name`, `latest_version_date`, `version_count` fields that the API doesn't send. The frontend is mostly fine at runtime (TS isn't strict, and components read what's actually there) but the type declarations are aspirational. **Tracked as a separate frontend pass; flagged here so nobody is surprised.**

(The sister problem — three labs.py routes using `response_model=dict` — was fixed on 2026-05-18; they now publish `LabSummary` / `LabDetail` / `LabCoveragePoint` in `apps/api/src/schemas/labs.py`.)

### 2. The 30 KB extraction window can miss the capability table

Long system cards (Opus 4.7 = 423k chars, Mythos = ~400k) push their canonical capability comparison table past char 350k. The keyword-density section selector can be fooled into picking the CBRN safety section when that section is keyword-denser than the comparison table. We mitigate this in three layers:

1. `ANCHOR_BOOST` (+10 to blocks containing "Capability evaluation summary", "SWE-bench Verified", etc.)
2. Two-window split for docs > `LONG_DOC_THRESHOLD` — half the budget goes to the front half, half to the back half.
3. `scripts/extract_one.py --anchor "<text>"` lets an operator force the window to start at a specific section heading when the automated selector still misses.

If you see `extraction_runs.evals_extracted` come back surprisingly low on a long card, that's the failure mode. Pin the symptom with a re-run via `extract_one.py --anchor`.

### 3. Cohere, Amazon, AI21 are tracked but not exposed

The DB has documents for nine labs. The live `/api/v1/labs` endpoint returns only six (Anthropic, OpenAI, Google, Meta, Mistral, xAI) because the public dashboard scope is "frontier Western labs." METHODOLOGY.md cites 9 labs / 88 docs / 1417 evals; the API surface shows 6 / ~77 / ~1200. Both are correct for their scope. If you change the lab filter, update both numbers.

---

## Where to look first when something breaks

| Symptom | First place to look |
|---|---|
| New card not appearing | `curl /api/v1/admin/health` — queue depths, stuck runs |
| Extraction landing 0 rows | Section selector picked wrong region → `scripts/extract_one.py --anchor` |
| Extraction stuck > 25 min | Reaper runs every 10 min OR `POST /api/v1/admin/reap-stuck-runs` |
| API returns 503 on admin | `ADMIN_TOKEN` env var unset on Railway |
| Zombie connections > 0 | `POST /api/v1/admin/kill-zombie-connections` OR wait 30 min for Postgres timeout |
| Local Python won't import worker code | Probably PEP 604 syntax; ensure `from __future__ import annotations` is at top |

Operational sequence (adding a card, troubleshooting a failure) lives in [`docs/RUNBOOK.md`](docs/RUNBOOK.md). This doc is "how it works"; that doc is "how to operate it."
