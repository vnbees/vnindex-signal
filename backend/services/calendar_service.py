from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.trading_calendar import TradingCalendar

async def is_trading_day(db: AsyncSession, d: date) -> bool:
    result = await db.execute(
        select(TradingCalendar).where(
            TradingCalendar.trade_date == d,
            TradingCalendar.is_trading == True
        )
    )
    if result.scalar_one_or_none() is not None:
        return True

    # Fallback: check if calendar table has any data for this year
    # If calendar is not seeded yet, allow weekdays (Mon-Fri) through
    count_result = await db.execute(
        select(func.count()).where(
            TradingCalendar.trade_date >= date(d.year, 1, 1),
            TradingCalendar.trade_date <= date(d.year, 12, 31),
        )
    )
    count = count_result.scalar_one() or 0
    if count == 0:
        # Calendar not seeded for this year - fallback to weekday check
        return d.weekday() < 5  # Mon=0..Fri=4
    return False

async def trading_days_between(db: AsyncSession, start: date, end: date) -> int:
    """Count trading days from start (exclusive) to end (inclusive)."""
    result = await db.execute(
        select(func.count()).where(
            TradingCalendar.trade_date > start,
            TradingCalendar.trade_date <= end,
            TradingCalendar.is_trading == True
        )
    )
    return result.scalar_one() or 0

async def get_trading_days_needed(db: AsyncSession, run_date: date, hold_days: int) -> list[date]:
    """Return list of trading dates T+1, T+5, T+10, T+20 from run_date."""
    targets = [1, 3, 10, 20]
    result = await db.execute(
        select(TradingCalendar.trade_date).where(
            TradingCalendar.trade_date > run_date,
            TradingCalendar.is_trading == True
        ).order_by(TradingCalendar.trade_date)
    )
    trading_days = [row[0] for row in result.fetchall()]

    dates_needed = []
    for target in targets:
        if target <= len(trading_days):
            dates_needed.append(trading_days[target - 1])
    return dates_needed
