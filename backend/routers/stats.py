from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
import traceback

router = APIRouter(tags=["stats"])


@router.get("/api/v1/stats/debug")
async def stats_debug(db: AsyncSession = Depends(get_db)):
    """Temporary debug endpoint — check DB state."""
    out = {}
    for query, key in [
        ("SELECT COUNT(*) FROM signal_pnl_summary", "count_mv"),
        ("SELECT column_name FROM information_schema.columns WHERE table_name='signal_pnl_summary' ORDER BY ordinal_position", "mv_columns"),
        ("SELECT version FROM alembic_version", "alembic_version"),
        ("SELECT COUNT(*) FROM signals", "count_signals"),
    ]:
        try:
            r = await db.execute(text(query))
            out[key] = [list(row) for row in r.fetchall()]
        except Exception as e:
            out[key] = f"ERROR: {e}"
    return out


@router.get("/api/v1/stats/pnl")
async def get_pnl_stats(
    days: int = 60,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        since_date = date.today() - timedelta(days=days)
        result = await db.execute(text("""
            SELECT
                recommendation,
                COUNT(*) AS total,
                ROUND(AVG(pnl_d3), 2) AS avg_pnl_d3,
                ROUND(AVG(pnl_d10), 2) AS avg_pnl_d10,
                ROUND(AVG(pnl_d20), 2) AS avg_pnl_d20,
                ROUND(AVG(latest_pnl_pct), 2) AS avg_latest_pnl
            FROM signal_pnl_summary
            WHERE run_date >= :since_date
              AND portfolio_kind = 'top_cap'
              AND (:price_min IS NULL OR price_close_signal_date >= :price_min)
              AND (:price_max IS NULL OR price_close_signal_date <= :price_max)
            GROUP BY recommendation
            ORDER BY recommendation
        """), {"since_date": since_date, "price_min": price_min, "price_max": price_max})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "trace": traceback.format_exc()})


@router.get("/api/v1/stats/accuracy")
async def get_accuracy_stats(
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(text("""
            SELECT
                recommendation,
                COUNT(*) AS total,
                SUM(CASE WHEN pnl_d3 > 0 THEN 1 ELSE 0 END) AS win_d3,
                SUM(CASE WHEN pnl_d10 > 0 THEN 1 ELSE 0 END) AS win_d10,
                SUM(CASE WHEN pnl_d20 > 0 THEN 1 ELSE 0 END) AS win_d20,
                ROUND(100.0 * SUM(CASE WHEN pnl_d3 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d3), 0), 1) AS winrate_d3,
                ROUND(100.0 * SUM(CASE WHEN pnl_d10 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d10), 0), 1) AS winrate_d10,
                ROUND(100.0 * SUM(CASE WHEN pnl_d20 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d20), 0), 1) AS winrate_d20
            FROM signal_pnl_summary
            WHERE portfolio_kind = 'top_cap'
              AND (:price_min IS NULL OR price_close_signal_date >= :price_min)
              AND (:price_max IS NULL OR price_close_signal_date <= :price_max)
            GROUP BY recommendation
            ORDER BY recommendation
        """), {"price_min": price_min, "price_max": price_max})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "trace": traceback.format_exc()})
