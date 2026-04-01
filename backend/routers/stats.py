from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter(tags=["stats"])

@router.get("/api/v1/stats/pnl")
async def get_pnl_stats(
    days: int = 60,
    db: AsyncSession = Depends(get_db)
):
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
        WHERE run_date >= :since_date AND portfolio_kind = 'top_cap'
        GROUP BY recommendation
        ORDER BY recommendation
    """), {"since_date": since_date})
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]

@router.get("/api/v1/stats/accuracy")
async def get_accuracy_stats(
    db: AsyncSession = Depends(get_db)
):
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
        GROUP BY recommendation
        ORDER BY recommendation
    """))
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]
