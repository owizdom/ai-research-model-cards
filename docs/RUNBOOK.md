# Operator Runbook — Model Card Explorer

This is the single canonical doc for maintaining the live pipeline. If you find
yourself doing something not described here, add it.

---

## Adding a new model card

You have a freshly published system card. End-to-end target: **<10 minutes**,
zero manual SQL.

### 1. Register the source

Edit `apps/collector/src/collectors/registry.py`. Add one `Source(...)` line in
the right lab block, in version order:

```python
Source("anthropic_opus47_card",  "anthropic", "Claude Opus 4.7 System Card",
       "model_card", "https://anthropic.com/claude-opus-4-7-system-card", "pdf"),
```

URL style: prefer the lab's stable shortlink (e.g. `anthropic.com/claude-…-system-card`)
over the CDN hash URL (`www-cdn.anthropic.com/<sha>.pdf`). The shortlink is
maintained; CDN hashes rotate silently.

### 2. Register the generation

Edit `data/model_families/families.yaml`. Add under the matching family:

```yaml
- slug: claude-opus-4.7
  name: Claude Opus 4.7
  version_label: "4.7-opus"
  release_date: 2026-04-16
  document_slug: anthropic_opus47_card
```

`document_slug` MUST match the Source slug.

### 3. Sanity-check the PDF parses

Don't trust a URL blindly — confirm the PDF downloads and pypdf can read it:

```bash
python3 -c "
import asyncio, httpx
from io import BytesIO
from pypdf import PdfReader

async def go():
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as c:
        r = await c.get('<your-source-url>')
    pages = len(PdfReader(BytesIO(r.content)).pages)
    print(f'{len(r.content):,} bytes, {pages} pages, ct={r.headers.get(\"content-type\")}')
asyncio.run(go())"
```

Expect `application/pdf` and >0 pages.

### 4. Ingest immediately (don't wait for the nightly cron)

```bash
cd ~/Desktop/ai-research-model-cards
railway link        # one-time, links the project; pick the abundant-reverence project
python3 scripts/ingest_one.py anthropic_opus47_card
```

`scripts/ingest_one.py` reads Railway DB+Redis URLs from `.env`. If you don't
have `.env` populated, run `railway variables --service Postgres --kv` and
`railway variables --service Redis --kv` to grab the public-proxy URLs and
construct `DATABASE_URL` + `REDIS_URL` in `.env` (gitignored).

Expected output:

```
┃ fetching anthropic_opus47_card
  parsed:       ~62,000 words / ~423,000 chars
  ✓ NEW version stored, embed_jobs queued
```

### 5. Seed the new generation row

```bash
python3 scripts/seed_db.py
```

Idempotent. Expect `Seeded: 0 taxonomy categories, 0 benchmarks, 1 families/generations`
(or more if `families.yaml` had other unsynced additions).

### 6. Watch the worker process it

Railway's worker auto-picks up `embed_jobs` from Redis, embeds → maps taxonomy
→ enqueues an `extract_jobs` job → runs Claude CLI → writes eval rows. Watch:

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  https://modest-playfulness-production.up.railway.app/api/v1/admin/health | jq
```

Expected progression over ~5 min:
- `extract_jobs` queue: 1 → 0 (worker picked it up)
- `in_flight_runs`: 0 → 1 → 0
- `recent_runs[0]` flips from `running` → `completed` with `evals` ≥ 20

### 7. Verify in the API

```bash
curl -s "$API/api/v1/families/claude" | jq '.generations[] | select(.slug=="claude-opus-4.7")'
```

Expect `eval_count > 0` and `document_id` set.

---

## Troubleshooting

### Extraction stuck > 25 min

Three possibilities:
1. **Wrong content window picked** — keyword density landed on safety prose, not the capability table. Run a targeted re-extraction:

   ```bash
   python3 scripts/extract_one.py --doc-id <N> --anchor "Capability evaluation summary"
   ```

   The `--anchor` flag forces the 30k window to start at the named text. Anchors that work for Anthropic system cards: `"Capability evaluation summary"`, `"SWE-bench Verified"`, `"GPQA Diamond"`. For OpenAI: `"Benchmark results"`, `"Performance overview"`.

2. **CLI subprocess hanging on Anthropic API** — kick the reaper and retry:

   ```bash
   curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" $API/api/v1/admin/reap-stuck-runs
   curl -X POST $API/api/v1/evals/extract/<version_id>     # re-enqueue
   ```

3. **Zombie Postgres connection** — worker crashed mid-flight, lock held forever. The scheduled reaper handles this in 10 min; force it now with:

   ```bash
   curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" $API/api/v1/admin/kill-zombie-connections
   ```

### Queue not draining

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" $API/api/v1/admin/queues
```

If `extract_jobs > 0` but `in_flight_runs == 0` for >2 min, the worker is dead. Check `railway logs --service refreshing-vitality`. Most common cause: deploy failed and worker container didn't come up. Re-trigger deploy from Railway dashboard.

### "Section anchor not found" when running extract_one

Open the doc in the UI (`/documents/<id>`) and look at the section headings the parser actually extracted. Use one of those verbatim as `--anchor`.

### Extracting wrong section despite the new selector

The two-window split kicks in only for docs > 80k chars. For shorter docs that still confuse the selector, force anchor:

```bash
python3 scripts/extract_one.py --doc-id <N> --anchor "<verbatim heading from doc>"
```

### Doc fetch fails (size cap, content-type mismatch, etc.)

Check `apps/collector/src/collectors/base.py` log output. Common fixes:
- Source URL serves PDF but registry says `"html"` → flip the method
- Doc > 500 KB → it's truncated with a marker; usually fine but extraction recall drops
- Source URL 404s → find the new URL on the lab's `/system-cards` or `/news` page

---

## Reading the metrics (`/api/v1/admin/health`)

```json
{
  "queues": {"embed_jobs": 0, "extract_jobs": 0},
  "in_flight_runs": 0,
  "stuck_runs": 0,
  "zombie_connections": 0,
  "recent_runs": [...]
}
```

| Field | Healthy | Action threshold |
|---|---|---|
| `queues.embed_jobs` | 0–2 | >5 for >10min → worker dead |
| `queues.extract_jobs` | 0–3 | >5 for >10min → worker dead OR all 3 extract threads busy |
| `in_flight_runs` | 0–3 (= EXTRACT_WORKERS) | >3 → schema drift, check logs |
| `stuck_runs` | 0 | ≥1 → reaper not running; check scheduler logs |
| `zombie_connections` | 0 | ≥1 → call `/kill-zombie-connections`, investigate worker crash |

---

## Useful endpoints

| URL | Purpose |
|---|---|
| `GET /api/v1/admin/health` | Single-shot pipeline status |
| `GET /api/v1/admin/queues` | Just the Redis queue depths (cheap) |
| `GET /api/v1/admin/runs?status=running` | Active extractions |
| `POST /api/v1/admin/reap-stuck-runs` | Flip stale runs to `failed` |
| `POST /api/v1/admin/kill-zombie-connections` | Terminate orphan PG connections |
| `POST /api/v1/evals/extract/{version_id}` | Re-enqueue extraction for a version |

All `/admin/*` endpoints require `X-Admin-Token: $ADMIN_TOKEN`.

---

## Architecture quick-reference

```
SOURCES (registry.py)
    │ collect_current() (cron 02:00 UTC)
    ▼
DocumentVersion (Postgres) ──rpush──> embed_jobs (Redis)
    │ worker embed thread
    ▼
embedding + taxonomy mappings ──rpush──> extract_jobs (Redis)
    │ worker extract threads (×3)
    ▼ Claude Sonnet 4.6 via CLI subprocess
eval_results (Postgres) ←── API ←── Frontend
```

Self-healing layer (added 2026-05):
- `idle_in_transaction_session_timeout=30min` on the worker's DB engine
- `reap_stuck_runs` APScheduler job every 10 min
- `INSERT … ON CONFLICT DO NOTHING` on all extraction writes

---

## When to escalate

Open a GitHub issue with the `pipeline` label if:
- Stuck runs > 0 persist after `/reap-stuck-runs` (means scheduler's broken)
- Zombie connections > 0 persist after `/kill-zombie-connections` (means session timeout's not applied — restart worker)
- Same doc fails extraction 3 times in a row with no env changes (means a real code bug, not transient)
