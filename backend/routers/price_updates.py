from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel
from database import get_db
from models.signal import Signal, AnalysisRun, AuditLog
from models.price_tracking import PriceTracking
from schemas.signal_output import PendingPriceUpdate
from services.calendar_service import is_trading_day, trading_days_between, get_trading_days_needed
from services.pnl_service import calculate_pnl_pct, is_corporate_action
from services.auth import verify_api_key

router = APIRouter(tags=["price-updates"])

class PriceEntry(BaseModel):
    symbol: str
    price_open: Optional[Decimal] = None
    price_close: Optional[Decimal] = None

class PriceUpdateBatch(BaseModel):
    track_date: date
    prices: list[PriceEntry]
    skip_refresh: bool = False

@router.get("/api/v1/price-updates/pending")
async def get_pending_updates(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Return signals that need price tracking data."""
    result = await db.execute(
        select(Signal).where(Signal.status == "active").order_by(Signal.run_date.desc()).limit(limit)
    )
    signals = result.scalars().all()

    pending = []
    for signal in signals:
        track_dates = await get_trading_days_needed(db, signal.run_date, 20)

        # Check which dates already have data
        existing_result = await db.execute(
            select(PriceTracking.track_date).where(PriceTracking.signal_id == signal.id)
        )
        existing_dates = {row[0] for row in existing_result.fetchall()}

        needed = [d for d in track_dates if d not in existing_dates]
        if needed:
            pending.append(PendingPriceUpdate(
                signal_id=signal.id,
                symbol=signal.symbol,
                run_date=signal.run_date,
                track_dates_needed=needed,
                needs_price_open_t1=signal.price_open_t1 is None
            ))

    return pending

@router.post("/api/v1/price-updates")
async def update_prices(
    payload: PriceUpdateBatch,
    db: AsyncSession = Depends(get_db),
    api_key_id: int = Depends(verify_api_key)
):
    track_date = payload.track_date

    # Validate track_date is trading day
    if not await is_trading_day(db, track_date):
        raise HTTPException(status_code=400, detail="track_date is not a trading day")

    updated_count = 0
    errors = []

    for price_entry in payload.prices:
        symbol = price_entry.symbol.upper()
        try:
            # Find active signals for this symbol
            result = await db.execute(
                select(Signal).where(
                    Signal.symbol == symbol,
                    Signal.status == "active"
                )
            )
            signals = result.scalars().all()

            for signal in signals:
                # Calculate days_after using trading_calendar
                days_after = await trading_days_between(db, signal.run_date, track_date)
                if days_after <= 0:
                    continue

                # Populate price_open_t1 if days_after == 1
                if days_after == 1 and price_entry.price_open is not None:
                    signal.price_open_t1 = price_entry.price_open
                    await db.flush()

                # Calculate pnl
                pnl = calculate_pnl_pct(price_entry.price_close, signal.price_open_t1)
                corp_action = is_corporate_action(pnl)

                if corp_action:
                    signal.has_corporate_action = True
                    await db.flush()

                # Upsert price_tracking
                existing = await db.execute(
                    select(PriceTracking).where(
                        PriceTracking.signal_id == signal.id,
                        PriceTracking.track_date == track_date
                    )
                )
                pt = existing.scalar_one_or_none()

                if pt:
                    pt.price_close = price_entry.price_close
                    pt.pnl_pct = pnl
                else:
                    pt = PriceTracking(
                        signal_id=signal.id,
                        run_date=signal.run_date,
                        symbol=symbol,
                        track_date=track_date,
                        days_after=days_after,
                        price_close=price_entry.price_close,
                        pnl_pct=pnl
                    )
                    db.add(pt)

                updated_count += 1

        except Exception as e:
            errors.append({"symbol": symbol, "reason": str(e)})

    # Audit log
    db.add(AuditLog(
        action="price.update",
        api_key_id=api_key_id,
        details={"track_date": str(track_date), "updated": updated_count, "errors": len(errors)}
    ))
    await db.commit()

    # Refresh materialized view (unless skip_refresh=True for intermediate batches)
    if not payload.skip_refresh:
        try:
            await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY signal_pnl_summary"))
            await db.commit()
        except Exception:
            pass  # Non-critical

    return {"track_date": str(track_date), "updated": updated_count, "errors": errors}

@router.post("/api/v1/admin/refresh-views")
async def refresh_views(
    db: AsyncSession = Depends(get_db),
    api_key_id: int = Depends(verify_api_key)
):
    """Manually trigger materialized view refresh."""
    await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY signal_pnl_summary"))
    await db.commit()
    return {"status": "refreshed"}
