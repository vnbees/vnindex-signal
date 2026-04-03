from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter(tags=["stats"])



def _price_filter_clause(price_min: Optional[float], price_max: Optional[float]) -> tuple[str, dict]:
    """Build price filter WHERE clause and params — only include non-None values."""
    clauses, params = [], {}
    if price_min is not None:
        clauses.append("price_close_signal_date >= :price_min")
        params["price_min"] = price_min
    if price_max is not None:
        clauses.append("price_close_signal_date <= :price_max")
        params["price_max"] = price_max
    sql = (" AND " + " AND ".join(clauses)) if clauses else ""
    return sql, params


@router.get("/api/v1/stats/pnl")
async def get_pnl_stats(
    days: int = 60,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    symbol: Optional[str] = None,
    portfolio_kind: str = "top_cap",
    db: AsyncSession = Depends(get_db)
):
    try:
        since_date = date.today() - timedelta(days=days)
        price_sql, price_params = _price_filter_clause(price_min, price_max)
        symbol_sql = ""
        params = {"since_date": since_date, "portfolio_kind": portfolio_kind, **price_params}
        if symbol and symbol.strip():
            symbol_sql = " AND symbol ILIKE :symbol "
            params["symbol"] = f"%{symbol.strip().upper()}%"
        result = await db.execute(text(f"""
            SELECT
                recommendation,
                COUNT(*) AS total,
                ROUND(AVG(pnl_d3), 2) AS avg_pnl_d3,
                ROUND(AVG(latest_pnl_pct), 2) AS avg_latest_pnl
            FROM signal_pnl_summary
            WHERE run_date >= :since_date
              AND portfolio_kind = :portfolio_kind
              {price_sql}
              {symbol_sql}
            GROUP BY recommendation
            ORDER BY recommendation
        """), params)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/v1/stats/accuracy")
async def get_accuracy_stats(
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    symbol: Optional[str] = None,
    portfolio_kind: str = "top_cap",
    db: AsyncSession = Depends(get_db)
):
    try:
        price_sql, price_params = _price_filter_clause(price_min, price_max)
        symbol_sql = ""
        params = {"portfolio_kind": portfolio_kind, **price_params}
        if symbol and symbol.strip():
            symbol_sql = " AND symbol ILIKE :symbol "
            params["symbol"] = f"%{symbol.strip().upper()}%"
        result = await db.execute(text(f"""
            SELECT
                recommendation,
                COUNT(*) AS total,
                SUM(CASE WHEN pnl_d3 > 0 THEN 1 ELSE 0 END) AS win_d3,
                ROUND(100.0 * SUM(CASE WHEN pnl_d3 > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(pnl_d3), 0), 1) AS winrate_d3
            FROM signal_pnl_summary
            WHERE portfolio_kind = :portfolio_kind
              {price_sql}
              {symbol_sql}
            GROUP BY recommendation
            ORDER BY recommendation
        """), params)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})
