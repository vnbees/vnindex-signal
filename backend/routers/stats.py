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
            ROUND(AVG(pnl_d1), 2) AS avg_pnl_d1,
            ROUND(AVG(pnl_d5), 2) AS avg_pnl_d5,
            ROUND(AVG(pnl_d10), 2) AS avg_pnl_d10,
            ROUND(AVG(pnl_d20), 2) AS avg_pnl_d20,
            ROUND(AVG(latest_pnl_pct), 2) AS avg_latest_pnl
        FROM signal_pnl_summary
        WHERE run_date >= :since_date
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
            SUM(CASE WHEN pnl_d1 > 0 THEN 1 ELSE 0 END) AS win_d1,
            SUM(CASE WHEN pnl_d5 > 0 THEN 1 ELSE 0 END) AS win_d5,
            SUM(CASE WHEN pnl_d20 > 0 THEN 1 ELSE 0 END) AS win_d20,
            ROUND(100.0 * SUM(CASE WHEN pnl_d1 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d1), 0), 1) AS winrate_d1,
            ROUND(100.0 * SUM(CASE WHEN pnl_d5 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d5), 0), 1) AS winrate_d5,
            ROUND(100.0 * SUM(CASE WHEN pnl_d20 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d20), 0), 1) AS winrate_d20
        FROM signal_pnl_summary
        GROUP BY recommendation
        ORDER BY recommendation
    """))
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]
