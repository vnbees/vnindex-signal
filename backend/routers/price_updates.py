from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from pydantic import BaseModel
from database import get_db
from models.signal import Signal, AnalysisRun, AuditLog
from models.price_tracking import PriceTracking
from models.trading_calendar import TradingCalendar
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
    limit: int = 10000,
    db: AsyncSession = Depends(get_db)
):
    """Return signals that need price tracking data. Bulk-query version (no N+1)."""
    # 1. Fetch all active signals (1 query)
    result = await db.execute(
        select(Signal).where(Signal.status == "active").order_by(Signal.run_date.desc()).limit(limit)
    )
    signals = result.scalars().all()
    if not signals:
        return []

    today = date.today()
    signal_ids = [s.id for s in signals]
    unique_run_dates = list({s.run_date for s in signals})

    # 2. Bulk-fetch T+1/T+3/T+10/T+20 for every unique run_date at once (1 query)
    TARGETS = [1, 3, 10, 20]
    max_target = max(TARGETS)

    # For each unique run_date we need the first max_target trading days after it.
    # Fetch ALL trading days after min(run_dates) up to today in one shot.
    min_run_date = min(unique_run_dates)
    cal_result = await db.execute(
        select(TradingCalendar.trade_date)
        .where(
            TradingCalendar.trade_date > min_run_date,
            TradingCalendar.trade_date <= today,
            TradingCalendar.is_trading == True,
        )
        .order_by(TradingCalendar.trade_date)
    )
    all_trading_days = [row[0] for row in cal_result.fetchall()]

    # Build lookup: run_date → [T+1, T+3, T+10, T+20]
    from bisect import bisect_right
    run_date_to_targets: dict[date, list[date]] = {}
    for rd in unique_run_dates:
        # find index of first trading day > rd
        idx = bisect_right(all_trading_days, rd)
        remaining = all_trading_days[idx:]
        dates_for_rd = []
        for t in TARGETS:
            # t is 1-indexed
            pos = t - 1
            if pos < len(remaining):
                dates_for_rd.append(remaining[pos])
        run_date_to_targets[rd] = dates_for_rd

    # 3. Bulk-fetch all existing price_tracking rows for those signals (1 query)
    pt_result = await db.execute(
        select(PriceTracking.signal_id, PriceTracking.track_date)
        .where(PriceTracking.signal_id.in_(signal_ids))
    )
    existing: dict[int, set[date]] = {}
    for sig_id, td in pt_result.fetchall():
        existing.setdefault(sig_id, set()).add(td)

    # 4. Build pending list (pure Python, no more DB queries)
    pending = []
    for signal in signals:
        track_dates = run_date_to_targets.get(signal.run_date, [])
        already_done = existing.get(signal.id, set())
        needed = [d for d in track_dates if d not in already_done]
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


@router.post("/api/v1/admin/seed-calendar")
async def seed_calendar(
    db: AsyncSession = Depends(get_db),
    api_key_id: int = Depends(verify_api_key)
):
    """Seed trading_calendar with weekday trading days from 2015 to 2027."""
    FIXED_HOLIDAYS = [(1, 1), (4, 30), (5, 1), (9, 2)]
    SPECIFIC_HOLIDAYS = {
        date(2015, 2, 18), date(2015, 2, 19), date(2015, 2, 20), date(2015, 2, 21),
        date(2015, 2, 22), date(2015, 2, 23), date(2015, 4, 2),
        date(2016, 2, 7), date(2016, 2, 8), date(2016, 2, 9), date(2016, 2, 10),
        date(2016, 2, 11), date(2016, 2, 12), date(2016, 4, 16),
        date(2017, 1, 26), date(2017, 1, 27), date(2017, 1, 28), date(2017, 1, 29),
        date(2017, 1, 30), date(2017, 1, 31), date(2017, 4, 6),
        date(2018, 2, 14), date(2018, 2, 15), date(2018, 2, 16), date(2018, 2, 17),
        date(2018, 2, 18), date(2018, 2, 19), date(2018, 4, 25),
        date(2019, 2, 4), date(2019, 2, 5), date(2019, 2, 6), date(2019, 2, 7),
        date(2019, 2, 8), date(2019, 2, 9), date(2019, 4, 14),
        date(2020, 1, 23), date(2020, 1, 24), date(2020, 1, 25), date(2020, 1, 26),
        date(2020, 1, 27), date(2020, 1, 28), date(2020, 4, 2),
        date(2021, 2, 10), date(2021, 2, 11), date(2021, 2, 12), date(2021, 2, 13),
        date(2021, 2, 14), date(2021, 2, 15), date(2021, 4, 21),
        date(2022, 1, 29), date(2022, 1, 30), date(2022, 1, 31), date(2022, 2, 1),
        date(2022, 2, 2), date(2022, 2, 3), date(2022, 4, 10),
        date(2023, 1, 20), date(2023, 1, 21), date(2023, 1, 22), date(2023, 1, 23),
        date(2023, 1, 24), date(2023, 1, 25), date(2023, 4, 29),
        date(2024, 2, 8), date(2024, 2, 9), date(2024, 2, 10), date(2024, 2, 11),
        date(2024, 2, 12), date(2024, 2, 13), date(2024, 4, 18),
        date(2025, 1, 27), date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
        date(2025, 1, 31), date(2025, 2, 3), date(2025, 4, 7),
        date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18), date(2026, 2, 19),
        date(2026, 2, 20), date(2026, 2, 23), date(2026, 4, 16),
        date(2027, 2, 5), date(2027, 2, 6), date(2027, 2, 7), date(2027, 2, 8),
        date(2027, 2, 9), date(2027, 2, 10), date(2027, 4, 6),
    }

    start = date(2015, 1, 1)
    end = date(2027, 12, 31)
    rows = []
    current = start
    while current <= end:
        is_weekend = current.weekday() >= 5
        is_fixed = (current.month, current.day) in FIXED_HOLIDAYS
        is_specific = current in SPECIFIC_HOLIDAYS
        is_trading = not (is_weekend or is_fixed or is_specific)
        rows.append({"trade_date": current, "is_trading": is_trading, "note": None})
        current += timedelta(days=1)

    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        stmt = pg_insert(TradingCalendar).values(batch).on_conflict_do_update(
            index_elements=["trade_date"],
            set_={"is_trading": pg_insert(TradingCalendar).excluded.is_trading}
        )
        await db.execute(stmt)
    await db.commit()

    trading_count = sum(1 for r in rows if r["is_trading"])
    return {"seeded": len(rows), "trading_days": trading_count}
