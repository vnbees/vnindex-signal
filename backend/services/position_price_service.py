"""Cập nhật giá và PnL cho stock_positions (tái sử dụng logic newsfeed)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from models.stock_position import StockPosition
from services.fireant_quote_service import (
    fetch_historical_quotes,
    get_fireant_token,
    get_latest_close,
    get_trade_dates_with_close,
    upsert_quotes,
)


def _pct(entry: float, target: float) -> float | None:
    if entry == 0:
        return None
    return ((target - entry) / entry) * 100.0


def _apply_horizon_pnl(
    *,
    entry: float,
    series: list[tuple[date, float]],
) -> tuple[float | None, float | None, float | None]:
    pnl_3d: float | None = None
    pnl_5d: float | None = None
    pnl_10d: float | None = None
    for trading_days, slot in ((3, "3"), (5, "5"), (10, "10")):
        if len(series) > trading_days:
            _, px = series[trading_days]
            val = _pct(entry, px)
            if slot == "3":
                pnl_3d = val
            elif slot == "5":
                pnl_5d = val
            else:
                pnl_10d = val
    return pnl_3d, pnl_5d, pnl_10d


async def _ensure_quotes_cached(
    db: AsyncSession,
    positions: list[StockPosition],
    *,
    token: str,
) -> None:
    symbols: set[str] = set()
    min_signal_date: date | None = None
    for pos in positions:
        symbols.add(pos.symbol)
        if min_signal_date is None or pos.signal_date < min_signal_date:
            min_signal_date = pos.signal_date
    if not symbols:
        return
    fetch_from = min_signal_date or date.today()
    fetch_to = date.today()
    for symbol in sorted(symbols):
        try:
            bars = await fetch_historical_quotes(symbol, fetch_from, fetch_to, token)
            if bars:
                await upsert_quotes(db, symbol, bars)
        except (httpx.HTTPError, Exception):
            continue


async def refresh_positions_prices(
    db: AsyncSession,
    positions: list[StockPosition],
) -> int:
    """Fetch/cache quotes and update price + PnL fields. Returns count of rows changed."""
    if not positions:
        return 0

    token = get_fireant_token()
    if token:
        await _ensure_quotes_cached(db, positions, token=token)

    latest_cache: dict[str, tuple[date, float] | None] = {}
    series_cache: dict[tuple[str, date], list[tuple[date, float]]] = {}
    changed = 0

    for pos in positions:
        symbol = pos.symbol
        buy = float(pos.buy_price)

        if symbol not in latest_cache:
            latest = await get_latest_close(db, symbol)
            latest_cache[symbol] = (
                (latest[0], float(latest[1])) if latest is not None else None
            )
        latest_val = latest_cache[symbol]
        if latest_val is not None:
            pos.current_price = Decimal(str(latest_val[1]))
            pos.price_as_of = latest_val[0]

        if pos.sell_price is None and pos.current_price is not None:
            pnl_val = _pct(buy, float(pos.current_price))
            pos.unrealized_pnl_pct = Decimal(str(pnl_val)) if pnl_val is not None else None
        elif pos.sell_price is None:
            pos.unrealized_pnl_pct = None

        cache_key = (symbol, pos.signal_date)
        if cache_key not in series_cache:
            series = await get_trade_dates_with_close(db, symbol, pos.signal_date)
            series_cache[cache_key] = [(d, float(p)) for d, p in series]
        series = series_cache[cache_key]
        p3, p5, p10 = _apply_horizon_pnl(entry=buy, series=series)
        pos.pnl_3d_pct = Decimal(str(p3)) if p3 is not None else None
        pos.pnl_5d_pct = Decimal(str(p5)) if p5 is not None else None
        pos.pnl_10d_pct = Decimal(str(p10)) if p10 is not None else None
        changed += 1

    if changed:
        await db.commit()
    return changed
