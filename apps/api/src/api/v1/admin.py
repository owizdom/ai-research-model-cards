"""Operator surface for the extraction pipeline.

Exposes pipeline health (queue depths, stuck runs, zombie connections) and two
recovery actions (reap stuck runs, kill zombie connections) so a maintainer
can diagnose + remediate without SSH-ing into Postgres.

Auth: gated on the ADMIN_TOKEN env var via the X-Admin-Token header. If
ADMIN_TOKEN is unset, all endpoints return 503 to avoid anonymous access on
misconfigured environments.
"""
import os
from typing import Optional

import redis
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.deps import get_db


router = APIRouter()


def require_admin(x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token")):
    """Token-header gate. Returns 503 if ADMIN_TOKEN is unset (safer than 401)."""
    if not settings.ADMIN_TOKEN:
        raise HTTPException(503, "admin endpoints disabled (ADMIN_TOKEN unset)")
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(401, "bad admin token")


def _redis():
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


@router.get("/queues", dependencies=[Depends(require_admin)])
async def queues():
    """Redis queue depths. Cheap; can be polled from a status page."""
    r = _redis()
    return {
        "embed_jobs": r.llen("embed_jobs"),
        "extract_jobs": r.llen("extract_jobs"),
    }


@router.get("/runs", dependencies=[Depends(require_admin)])
async def list_runs(
    status: Optional[str] = Query(None, description="running|completed|failed"),
    limit: int = Query(20, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Recent extraction_runs, newest first. Surfaces stuck runs at a glance."""
    where = "WHERE status = :status" if status else ""
    params = {"limit": limit}
    if status:
        params["status"] = status
    result = await db.execute(text(f"""
        SELECT er.id, er.document_version_id, er.status, er.model_used,
               er.evals_extracted, er.started_at, er.completed_at,
               LEFT(COALESCE(er.error, ''), 200) AS err,
               EXTRACT(EPOCH FROM (NOW() - er.started_at))::int AS age_s,
               d.title AS doc_title, l.slug AS lab
        FROM extraction_runs er
        JOIN document_versions dv ON dv.id = er.document_version_id
        JOIN documents d ON d.id = dv.document_id
        LEFT JOIN labs l ON l.id = d.lab_id
        {where}
        ORDER BY er.started_at DESC
        LIMIT :limit
    """), params)
    return [
        {
            "id": r.id,
            "document_version_id": r.document_version_id,
            "status": r.status,
            "model_used": r.model_used,
            "evals_extracted": r.evals_extracted,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "age_s": r.age_s,
            "lab": r.lab,
            "doc_title": r.doc_title,
            "error": r.err or None,
        }
        for r in result.fetchall()
    ]


@router.get("/health", dependencies=[Depends(require_admin)])
async def health(db: AsyncSession = Depends(get_db)):
    """One-shot pipeline-health snapshot for status pages + cron probes."""
    r = _redis()
    queues = {"embed_jobs": r.llen("embed_jobs"), "extract_jobs": r.llen("extract_jobs")}

    # Stuck runs: status='running' older than 25 min (the reaper threshold).
    stuck = (await db.execute(text("""
        SELECT COUNT(*) FROM extraction_runs
        WHERE status = 'running'
          AND started_at < NOW() - INTERVAL '25 minutes'
    """))).scalar()

    # In-flight runs (any 'running', regardless of age).
    in_flight = (await db.execute(text("""
        SELECT COUNT(*) FROM extraction_runs WHERE status = 'running'
    """))).scalar()

    # Zombie connections: holding an advisory lock AND idle-in-transaction
    # for more than 5 min. These block new extractions until killed.
    zombie = (await db.execute(text("""
        SELECT COUNT(*) FROM pg_stat_activity a
        WHERE a.state = 'idle in transaction'
          AND EXTRACT(EPOCH FROM (NOW() - a.state_change)) > 300
          AND a.pid IN (
              SELECT pid FROM pg_locks WHERE locktype = 'advisory' AND granted = true
          )
    """))).scalar()

    # Last 5 runs for context.
    recent = (await db.execute(text("""
        SELECT id, document_version_id, status, evals_extracted,
               EXTRACT(EPOCH FROM (NOW() - started_at))::int AS age_s
        FROM extraction_runs ORDER BY started_at DESC LIMIT 5
    """))).fetchall()

    return {
        "queues": queues,
        "in_flight_runs": in_flight,
        "stuck_runs": stuck,
        "zombie_connections": zombie,
        "recent_runs": [
            {"id": r.id, "v": r.document_version_id, "status": r.status,
             "evals": r.evals_extracted, "age_s": r.age_s}
            for r in recent
        ],
    }


@router.post("/reap-stuck-runs", dependencies=[Depends(require_admin)])
async def reap_stuck_runs(db: AsyncSession = Depends(get_db)):
    """Trigger the reaper on-demand. Same SQL as the scheduled job."""
    result = await db.execute(text("""
        UPDATE extraction_runs
        SET status = 'failed',
            error = COALESCE(error, '') || ' [reaped: exceeded 25 min runtime]',
            completed_at = NOW()
        WHERE status = 'running'
          AND started_at < NOW() - INTERVAL '25 minutes'
        RETURNING id, document_version_id
    """))
    rows = result.fetchall()
    await db.commit()
    return {"reaped": len(rows), "run_ids": [r.id for r in rows]}


@router.post("/kill-zombie-connections", dependencies=[Depends(require_admin)])
async def kill_zombie_connections(db: AsyncSession = Depends(get_db)):
    """Terminate any backend pid holding an advisory lock + idle-in-transaction
    for > 5 min. Postgres normally handles this via idle_in_transaction_session_timeout
    (30 min) but this endpoint exists for faster manual remediation.
    """
    pids = (await db.execute(text("""
        SELECT a.pid FROM pg_stat_activity a
        WHERE a.state = 'idle in transaction'
          AND EXTRACT(EPOCH FROM (NOW() - a.state_change)) > 300
          AND a.pid IN (
              SELECT pid FROM pg_locks WHERE locktype = 'advisory' AND granted = true
          )
    """))).scalars().all()

    killed = []
    for pid in pids:
        ok = (await db.execute(text("SELECT pg_terminate_backend(:pid)"),
                                {"pid": pid})).scalar()
        if ok:
            killed.append(pid)
    await db.commit()
    return {"killed": killed, "count": len(killed)}
