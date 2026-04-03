import csv
import io
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter(tags=["export"])

@router.get("/api/v1/export/csv")
async def export_csv(
    from_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    conditions = ["portfolio_kind = 'top_cap'"]
    params: dict = {}
    if from_date:
        conditions.append("run_date >= :from_date")
        params["from_date"] = from_date
    where = "WHERE " + " AND ".join(conditions)

    result = await db.execute(text(f"""
        SELECT run_date, symbol, recommendation, score_total,
               price_close_signal_date, price_open_t1, has_corporate_action,
               pnl_d3, latest_pnl_pct
        FROM signal_pnl_summary
        {where}
        ORDER BY run_date DESC, score_total DESC
    """), params)
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["run_date", "symbol", "recommendation", "score_total",
                     "price_close", "price_open_t1", "has_corp_action",
                     "pnl_d3", "latest_pnl"])
    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=signals_export.csv"}
    )
