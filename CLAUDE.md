# Project instructions — Model Card Explorer

Notes for Claude Code sessions in this repo. Read once, then proceed.

## Repo conventions

- **Branch:** `main`. No long-lived feature branches.
- **Commit attribution:** never add `Co-Authored-By: Claude` or "Generated with Claude Code". Plain messages.
- **Commit messages:** lowercase short subject, body wrapped at ~80 chars, focus on *why* not *what*. See recent commits for the style.
- **Python:** Docker runtime is 3.11+, but local maintainer Python may be 3.9 (Apple CommandLineTools). Top every worker/collector file with `from __future__ import annotations` so PEP 604 `str | None` etc. doesn't trip 3.9 imports.
- **TypeScript:** strict mode is on but loosely respected at the API boundary — see `ARCHITECTURE.md` §"API↔TS shape mismatch".

## Where things live

- `apps/api/` — FastAPI public surface + `/admin/*`.
- `apps/collector/` — APScheduler service: fetches nightly, runs stuck-run reaper every 10 min.
- `apps/worker/` — embed + extract threads, BLPOP off Redis.
- `apps/web/` — Next.js dashboard (deployed on Vercel, not Railway).
- `packages/db/` — SQLAlchemy models + Alembic migrations + shared engine.
- `packages/pipeline_config.py` — **single source of truth** for cross-cutting constants. If you find a magic number used in 2+ files, move it here.
- `scripts/` — operator CLIs (`ingest_one.py`, `extract_one.py`, `seed_db.py`).
- `charts/` — research-only chart generators. Not in any runtime path.
- `docs/RUNBOOK.md` — ops procedures.
- `ARCHITECTURE.md` — data flow + design.

## Live deployments

- **API (Railway):** `https://modest-playfulness-production.up.railway.app/api/v1/`
- **Web (Vercel):** `https://model-card.vercel.app`
- **Worker service name on Railway:** `refreshing-vitality`
- **Collector service name on Railway:** `positive-charisma`
- **API service name on Railway:** `modest-playfulness`

Don't invent URLs or service names. If in doubt, `railway link` then `railway service`.

## Operational entry points

- **Add a source:** edit `apps/collector/src/collectors/registry.py` + `data/model_families/families.yaml`, then `scripts/ingest_one.py <slug>` + `scripts/seed_db.py`. Full walkthrough in `docs/RUNBOOK.md`.
- **Force extraction on a stuck doc:** `scripts/extract_one.py --doc-id <N>` with `--anchor`, `--window-size`, `--timeout-s`, `--dry-run` flags.
- **Local dev:** `make setup`, `make dev`. Compose files in `infra/compose/`.
- **Migrations:** `make migrate` (Alembic).
- **Seed:** `make seed` or `scripts/seed_db.py` (idempotent).

## Recent operational lessons (don't undo these)

These are scars from real incidents. Each fix is in the current code; don't accidentally regress them.

1. **All extraction inserts use `ON CONFLICT DO NOTHING`.** A duplicate `benchmark_definitions.slug` would otherwise roll back the whole transaction mid-flight. Don't reintroduce SELECT-then-INSERT.
2. **Section selector has anchor boost + two-window split.** Long cards (>80k chars) put their capability table at char 350k+, past the keyword-dense safety prose. Don't simplify the selector without re-checking against Opus 4.7 (doc id 972) — and don't change scoring without running `apps/worker/tests/test_eval_extractor.py`.
3. **Postgres `idle_in_transaction_session_timeout=30min` is set on the worker engine.** This releases the advisory lock when a worker crashes mid-extraction, so the next thread isn't blocked. Don't remove it.
4. **`reap_stuck_runs()` flips long-running rows to `failed` every 10 min** (scheduled in `apps/collector/src/scheduler/runner.py`). It pairs with the Postgres timeout above — Postgres clears the lock; the reaper clears the user-visible status. Don't add a third recovery path; fix one of these two if it's broken.
5. **Claude CLI subprocess timeout is `1200s` default, env-overridable.** 600s was insufficient on Llama 3.1 and Opus 4.7 (both 60k+ word cards). If you bump it again, update `pipeline_config.CLI_TIMEOUT_DEFAULT_S` not a local literal.
6. **API admin endpoints require `X-Admin-Token`.** When the env var is unset, endpoints return 503 (not 401) so misconfigured envs aren't anonymously pokeable.

## Things to ask the user before doing

- **Layout restructure** (apps/+packages/ → flat). User wants this eventually but it's a separate big PR; don't volunteer it.
- **Adding new tracked labs.** Scope is "Western frontier labs" by design — Cohere/Amazon/AI21 are tracked in DB but filtered from the public API.
- **Bumping `EXTRACTION_PROTOCOL_VERSION`.** Old rows stay forever once a version is in use; this is a permanent decision.
- **Pushing to `main`.** User-initiated only. Don't push commits unless they asked.
