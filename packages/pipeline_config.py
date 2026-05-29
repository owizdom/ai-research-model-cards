"""Single source of truth for cross-cutting pipeline constants.

If a value is read in more than one module — a threshold, a window size, a
timeout — it lives here. Modules import; they do not redefine. This file
is `from __future__ import annotations`-free intentionally because it's
pure constants.

Background: an audit on 2026-05-16 found "coverage threshold" defined in
five different places with three different values. Constants below replace
those scattered literals. See ARCHITECTURE.md §"Threshold philosophy" for
the rationale behind each number.
"""

# ── Coverage / similarity thresholds ─────────────────────────────────────────
# Used by the embedder write path and the API analysis endpoints.

TAXONOMY_SIMILARITY_FLOOR: float = 0.20
"""Embedder rejects (doc_version, category) mappings whose cosine similarity
falls below this. Below this point the match is noise. Read by
apps/worker/src/embedder/pipeline.py."""

COVERAGE_ANALYSIS_THRESHOLD: float = 0.25
"""Default cutoff in the /api/v1/analysis/intersection endpoint for "is this
category covered". Callers can override via query param. Empirically the
boundary between dim mentions and meaningful prose."""

COVERAGE_BAND_STRONG: float = 0.50
"""Export grade A — the lab has detailed, dedicated policy on this topic."""

COVERAGE_BAND_MODERATE: float = 0.35
"""Export grade B — the lab addresses this topic meaningfully."""

COVERAGE_BAND_WEAK: float = 0.20
"""Export grade C — brief mention, not a focused policy. Matches the
embedder's insertion floor so anything that exists in the DB grades C or
above."""


# ── Extraction pipeline ──────────────────────────────────────────────────────

EXTRACTION_PROTOCOL_VERSION: int = 3
"""Bump when the extractor's output shape changes in a way that makes old
rows non-comparable. Old rows stay; new rows insert under the new version
so the UI can filter. v3 (2026-05-29): adds explicit `split` and
`metric_path` fields read from prose context (paper Section 3.2 hierarchy)
and switches the default extractor model to Opus 4.7 for richer extraction
of sub-task structure that Sonnet 4.6 historically flattened into the
variant string."""

WINDOW_SIZE_DEFAULT: int = 30_000
"""Char budget the section selector passes to the Claude CLI per extraction
call. Larger = more recall, slower CLI, higher timeout risk."""

LONG_DOC_THRESHOLD: int = 80_000
"""Above this content length, _extract_eval_sections splits the budget
across a top-half window and a bottom-half window. Catches capability tables
that sit at char 350k+ in long system cards (Opus 4.7 was 423k chars; its
capability summary was at 368k)."""

ANCHOR_BOOST: int = 10
"""Score bonus a block gets when it contains a canonical capability-table
marker ("Capability evaluation summary", "SWE-bench Verified", etc.) or a
numbered section header. Large enough to outweigh keyword-density wins from
narrative-dense safety prose."""

CLI_RETRY_ATTEMPTS: int = 4
"""Number of attempts the extractor makes against the Claude CLI subprocess
before giving up. Used only for the rate-limit/quota/budget error class."""

CLI_RETRY_BASE_BACKOFF_S: int = 30
"""Base sleep between retries; multiplied by attempt number for linear
backoff. 30, 60, 90, 120s — total wait ~5 min before final failure."""

CLI_TIMEOUT_DEFAULT_S: float = 1200.0
"""Default Claude CLI subprocess timeout. Overridable per-call via the
CLAUDE_CLI_TIMEOUT_S env var. 600s was insufficient on Llama 3.1 / Opus 4.7;
1200s is the working default with env override for unusual cards."""


# ── Operational ─────────────────────────────────────────────────────────────

STUCK_RUN_THRESHOLD_MIN: int = 25
"""extraction_runs rows in 'running' for longer than this are reaped (flipped
to 'failed') by the scheduled job in apps/collector/src/scheduler/jobs.py
and by POST /api/v1/admin/reap-stuck-runs."""

IDLE_TXN_TIMEOUT_MS: int = 1_800_000
"""Postgres `idle_in_transaction_session_timeout` set on the worker's async
engine. A worker that crashes mid-extraction leaves its connection 'idle in
transaction' holding the advisory lock; Postgres aborts the txn after this
many ms, releasing the lock without manual pg_terminate_backend. 30 min."""

READ_WPM: int = 230
"""Words per minute used by the /api/v1/documents/{id}/content endpoint to
estimate read_minutes for the UI. 230 ≈ research-prose pace."""


# ── HTTP / Redis transport ───────────────────────────────────────────────────

HTTP_TIMEOUT_DEFAULT_S: float = 30.0
"""Per-request timeout for single-shot HTTP calls: an HTML page fetch, a
Wayback snapshot pull, a CDX metadata query. Tight enough that a stuck
upstream doesn't pin a collector slot, generous enough to survive normal
latency to slow CDNs."""

HTTP_TIMEOUT_BULK_S: float = 60.0
"""Client-level timeout for bulk/heavy downloads — the fetch_all client that
walks every Source, the history-collection client, PDF downloads (which can
be 5–10 MB for long system cards). PDFs in particular need the headroom."""

REDIS_BLPOP_TIMEOUT_S: int = 5
"""Blocking pop interval for the worker's embed/extract queues. Shorter =
more responsive shutdown, more idle wakeups; longer = laggier shutdown.
5s is the working compromise. Read by apps/worker/src/main.py."""
