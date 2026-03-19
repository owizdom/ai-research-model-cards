from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.deps import get_db
from src.schemas.analysis import DriftResult, AsymmetryResult, SlantSummary

router = APIRouter()


@router.get("", response_model=SlantSummary)
async def slant_summary(
    model_slug: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    model_f = f"AND ss.model_slug = '{model_slug}'" if model_slug else ""
    cat_f = f"AND pd.category = '{category}'" if category else ""

    model_sql = text(f"""
        SELECT ss.model_slug, AVG(ss.composite_slant) as mean_slant,
               STDDEV(ss.composite_slant) as std_slant, COUNT(*) as n_samples
        FROM slant_scores ss
        JOIN probe_responses pr ON pr.id = ss.response_id
        JOIN probe_definitions pd ON pd.id = pr.probe_id
        WHERE ss.composite_slant IS NOT NULL {model_f} {cat_f}
        GROUP BY ss.model_slug ORDER BY mean_slant DESC
    """)
    probe_sql = text(f"""
        SELECT pd.probe_key, pd.category, ss.model_slug, AVG(ss.composite_slant) as mean_slant
        FROM slant_scores ss
        JOIN probe_responses pr ON pr.id = ss.response_id
        JOIN probe_definitions pd ON pd.id = pr.probe_id
        WHERE ss.composite_slant IS NOT NULL {model_f} {cat_f}
        GROUP BY pd.probe_key, pd.category, ss.model_slug
        ORDER BY pd.category, pd.probe_key
    """)
    mr = await db.execute(model_sql)
    pr = await db.execute(probe_sql)

    model_scores = [
        {"model_slug": r.model_slug, "mean_composite_slant": round(float(r.mean_slant or 0), 4),
         "std": round(float(r.std_slant or 0), 4), "n_samples": r.n_samples}
        for r in mr.fetchall()
    ]
    probe_map: dict = {}
    for r in pr.fetchall():
        if r.probe_key not in probe_map:
            probe_map[r.probe_key] = {"probe_key": r.probe_key, "category": r.category, "mean_slant_by_model": {}}
        probe_map[r.probe_key]["mean_slant_by_model"][r.model_slug] = round(float(r.mean_slant or 0), 4)

    return SlantSummary(model_scores=model_scores, probe_scores=list(probe_map.values()))


@router.get("/drift", response_model=list[DriftResult])
async def slant_drift(db: AsyncSession = Depends(get_db)):
    pairs = await db.execute(text("""
        SELECT ss.model_slug, ss.probe_id, COUNT(*) as n
        FROM slant_scores ss WHERE ss.composite_slant IS NOT NULL
        GROUP BY ss.model_slug, ss.probe_id HAVING COUNT(*) >= 5
    """))
    results = []
    import numpy as np
    for row in pairs.fetchall():
        series = await db.execute(text("""
            SELECT ss.composite_slant, pr.recorded_at::date as d
            FROM slant_scores ss JOIN probe_responses pr ON pr.id = ss.response_id
            WHERE ss.model_slug = :m AND ss.probe_id = :p AND ss.composite_slant IS NOT NULL
            ORDER BY pr.recorded_at
        """), {"m": row.model_slug, "p": row.probe_id})
        rows = series.fetchall()
        scores = [float(r.composite_slant) for r in rows]
        dates = [r.d.isoformat() for r in rows]
        mean_s, std_s = float(np.mean(scores)), float(np.std(scores))
        try:
            import pymannkendall as mk
            mk_r = mk.original_test(scores)
            trend, p_val, tau = mk_r.trend, float(mk_r.p), float(mk_r.Tau)
        except Exception:
            trend, p_val, tau = "no trend", 1.0, 0.0
        direction = "liberal" if mean_s > 0.15 else ("conservative" if mean_s < -0.15 else "neutral")
        results.append(DriftResult(
            model_slug=row.model_slug, probe_id=row.probe_id, n_samples=len(rows),
            mean_slant=round(mean_s, 4), std_slant=round(std_s, 4),
            trend=trend, p_value=round(p_val, 4), tau=round(tau, 4),
            is_significant=p_val < 0.05, direction=direction,
            time_series=[{"date": d, "composite_slant": s} for d, s in zip(dates, scores)],
        ))
    results.sort(key=lambda x: (x.is_significant, abs(x.mean_slant)), reverse=True)
    return results


@router.get("/asymmetry", response_model=list[AsymmetryResult])
async def slant_asymmetry(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT ss.model_slug,
               AVG(ss.composite_slant) FILTER (WHERE pd.probe_key = 'trump-2024-assessment') as trump_slant,
               AVG(ss.composite_slant) FILTER (WHERE pd.probe_key = 'biden-2024-assessment') as biden_slant
        FROM slant_scores ss
        JOIN probe_responses pr ON pr.id = ss.response_id
        JOIN probe_definitions pd ON pd.id = pr.probe_id
        WHERE pd.probe_key IN ('trump-2024-assessment','biden-2024-assessment')
        GROUP BY ss.model_slug HAVING COUNT(DISTINCT pd.probe_key) = 2
    """))
    out = []
    for r in result.fetchall():
        if r.trump_slant is None or r.biden_slant is None:
            continue
        trump, biden = float(r.trump_slant), float(r.biden_slant)
        asym = abs(trump - biden)
        interp = (f"More liberal on Trump ({trump:+.2f}) than Biden ({biden:+.2f})" if trump > biden
                  else f"More liberal on Biden ({biden:+.2f}) than Trump ({trump:+.2f})")
        out.append(AsymmetryResult(
            model_slug=r.model_slug, probe_a_key="trump-2024-assessment",
            probe_b_key="biden-2024-assessment",
            trump_slant=round(trump, 4), biden_slant=round(biden, 4),
            asymmetry_score=round(asym, 4), interpretation=interp,
        ))
    out.sort(key=lambda x: x.asymmetry_score, reverse=True)
    return out
