from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from database import get_db
from models.signal import Signal, AnalysisRun, ApiKey, AuditLog
from schemas.signal_input import SignalBatchInput
from schemas.signal_output import SignalListItem, SignalDetail, RunListItem
from services.signal_service import upsert_signals
from services.auth import verify_api_key

router = APIRouter(tags=["signals"])

@router.post("/api/v1/signals")
async def write_signals(
    payload: SignalBatchInput,
    db: AsyncSession = Depends(get_db),
    api_key_id: int = Depends(verify_api_key)
):
    return await upsert_signals(db, payload, api_key_id)

@router.get("/api/v1/runs")
async def list_runs(
    limit: int = 30,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AnalysisRun).order_by(AnalysisRun.run_date.desc()).limit(limit).offset(offset)
    )
    runs = result.scalars().all()
    items = []
    for run in runs:
        count_result = await db.execute(
            select(func.count()).where(Signal.run_id == run.id)
        )
        count = count_result.scalar_one()
        items.append(RunListItem(
            id=run.id,
            run_date=run.run_date,
            top_n=run.top_n,
            hold_days=run.hold_days,
            signal_count=count
        ))
    return items

@router.get("/api/v1/signals/{run_date}")
async def get_signals_for_date(
    run_date: date,
    recommendation: Optional[str] = None,
    sort_by: str = "score_total",
    order: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    allowed_sort_columns = {
        "score_total": Signal.score_total,
        "symbol": Signal.symbol,
        "market_cap_bil": Signal.market_cap_bil,
    }
    sort_col = allowed_sort_columns.get(sort_by, Signal.score_total)
    sort_dir = "DESC" if order.lower() == "desc" else "ASC"

    result = await db.execute(
        select(Signal).join(AnalysisRun).where(
            Signal.run_date == run_date,
            *([Signal.recommendation == recommendation] if recommendation else [])
        ).order_by(
            sort_col.desc() if sort_dir == "DESC" else sort_col.asc()
        )
    )
    signals = result.scalars().all()

    # Get PnL data from materialized view
    pnl_result = await db.execute(
        text("SELECT signal_id, pnl_d3, pnl_d10, pnl_d20, latest_pnl_pct FROM signal_pnl_summary WHERE run_date = :run_date"),
        {"run_date": run_date}
    )
    pnl_map = {row.signal_id: row for row in pnl_result.fetchall()}

    items = []
    for s in signals:
        pnl = pnl_map.get(s.id)
        items.append(SignalListItem(
            id=s.id,
            run_date=s.run_date,
            symbol=s.symbol,
            status=s.status,
            score_financial=s.score_financial,
            score_seasonal=s.score_seasonal,
            score_technical=s.score_technical,
            score_cashflow=s.score_cashflow,
            score_total=s.score_total,
            recommendation=s.recommendation,
            signal_type=s.signal_type,
            price_close_signal_date=s.price_close_signal_date,
            price_open_t1=s.price_open_t1,
            market_cap_bil=s.market_cap_bil,
            has_corporate_action=s.has_corporate_action or False,
            pnl_d3=pnl.pnl_d3 if pnl else None,
            pnl_d10=pnl.pnl_d10 if pnl else None,
            pnl_d20=pnl.pnl_d20 if pnl else None,
            latest_pnl_pct=pnl.latest_pnl_pct if pnl else None,
        ))
    return items

@router.get("/api/v1/signals/{run_date}/{symbol}")
async def get_signal_detail(
    run_date: date,
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Signal).where(
            Signal.run_date == run_date,
            Signal.symbol == symbol.upper()
        )
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    pnl_result = await db.execute(
        text("SELECT pnl_d3, pnl_d10, pnl_d20, latest_pnl_pct FROM signal_pnl_summary WHERE run_date = :run_date AND symbol = :symbol"),
        {"run_date": run_date, "symbol": symbol.upper()}
    )
    pnl = pnl_result.fetchone()

    return SignalDetail(
        id=signal.id,
        run_date=signal.run_date,
        symbol=signal.symbol,
        status=signal.status,
        score_financial=signal.score_financial,
        score_seasonal=signal.score_seasonal,
        score_technical=signal.score_technical,
        score_cashflow=signal.score_cashflow,
        score_total=signal.score_total,
        recommendation=signal.recommendation,
        signal_type=signal.signal_type,
        price_close_signal_date=signal.price_close_signal_date,
        price_open_t1=signal.price_open_t1,
        market_cap_bil=signal.market_cap_bil,
        has_corporate_action=signal.has_corporate_action or False,
        detail_financial=signal.detail_financial,
        detail_technical=signal.detail_technical,
        detail_cashflow=signal.detail_cashflow,
        detail_seasonal=signal.detail_seasonal,
        pnl_d3=pnl.pnl_d3 if pnl else None,
        pnl_d10=pnl.pnl_d10 if pnl else None,
        pnl_d20=pnl.pnl_d20 if pnl else None,
        latest_pnl_pct=pnl.latest_pnl_pct if pnl else None,
    )
