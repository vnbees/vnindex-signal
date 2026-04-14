import json
from datetime import date, datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.signal_entry import SignalEntry
from services.fireant_quote_service import (
    fetch_historical_quotes,
    get_fireant_token,
    get_latest_close,
    get_trade_dates_with_close,
    upsert_quotes,
)
from schemas.signal_entry import (
    BuySignalIn,
    NewfeedItem,
    NewfeedListResponse,
    SignalEntryCreate,
    SignalEntryIngestAgentRequest,
    SignalEntryIngestAgentResponse,
    SignalEntryListResponse,
    SignalEntryOut,
    SignalEntryUpdate,
)

router = APIRouter(tags=["signal-entries"])


def _truncate_preview(text: str, max_chars: int = 280) -> str:
    plain = text.strip()
    if len(plain) <= max_chars:
        return plain
    return f"{plain[:max_chars].rstrip()}..."


def _parse_buy_signals(payload: object) -> list[BuySignalIn]:
    if not isinstance(payload, dict):
        return []
    raw_signals = payload.get("buy_signals")
    if not isinstance(raw_signals, list):
        return []
    parsed: list[BuySignalIn] = []
    for item in raw_signals:
        if not isinstance(item, dict):
            continue
        try:
            parsed.append(BuySignalIn.model_validate(item))
        except Exception:
            continue
    return parsed


def _validate_newfeeds_pagination(limit: int, offset: int) -> None:
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")


async def _query_newfeed_rows(
    db: AsyncSession,
    limit: int,
    offset: int,
) -> tuple[list[SignalEntry], int]:
    cond = (
        SignalEntry.deleted_at.is_(None),
        SignalEntry.data_extracted.is_(True),
    )
    count_q = select(func.count()).select_from(SignalEntry).where(*cond)
    total = (await db.execute(count_q)).scalar_one()
    q = (
        select(SignalEntry)
        .where(*cond)
        .order_by(SignalEntry.reference_date.desc().nullslast(), SignalEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(q)).scalars().all()
    return rows, total


def _to_newfeed_item(row: SignalEntry) -> NewfeedItem:
    return NewfeedItem(
        id=row.id,
        reference_date=row.reference_date,
        created_at=row.created_at,
        title=row.title,
        raw_text=row.notes or "",
        raw_text_preview=_truncate_preview(row.notes or ""),
        buy_signals=_parse_buy_signals(row.payload),
    )


@router.get(
    "/api/v1/admin/signal-entries",
    response_model=SignalEntryListResponse,
)
async def list_signal_entries(
    limit: int = 50,
    offset: int = 0,
    symbol: str | None = None,
    data_extracted: bool | None = None,
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    base = select(SignalEntry)
    count_base = select(func.count()).select_from(SignalEntry)

    if not include_deleted:
        cond = SignalEntry.deleted_at.is_(None)
        base = base.where(cond)
        count_base = count_base.where(cond)

    if symbol and symbol.strip():
        sym = symbol.strip().upper()
        base = base.where(SignalEntry.symbol == sym)
        count_base = count_base.where(SignalEntry.symbol == sym)

    if data_extracted is not None:
        base = base.where(SignalEntry.data_extracted == data_extracted)
        count_base = count_base.where(SignalEntry.data_extracted == data_extracted)

    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    result = await db.execute(
        base.order_by(SignalEntry.created_at.desc()).limit(limit).offset(offset)
    )
    rows = result.scalars().all()
    return SignalEntryListResponse(
        items=[SignalEntryOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/api/v1/admin/signal-entries/{entry_id}",
    response_model=SignalEntryOut,
)
async def get_signal_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SignalEntry).where(SignalEntry.id == entry_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="signal entry not found")
    return SignalEntryOut.model_validate(row)


@router.post(
    "/api/v1/admin/signal-entries",
    response_model=SignalEntryOut,
    status_code=201,
)
async def create_signal_entry(
    body: SignalEntryCreate,
    db: AsyncSession = Depends(get_db),
):
    row = SignalEntry(
        symbol=body.symbol,
        reference_date=body.reference_date,
        title=body.title,
        notes=body.notes,
        payload=body.payload,
        data_extracted=body.data_extracted,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SignalEntryOut.model_validate(row)


@router.post(
    "/api/v1/admin/signal-entries/ingest-agent",
    response_model=SignalEntryIngestAgentResponse,
    status_code=201,
)
async def ingest_signal_entry_from_agent(
    body: SignalEntryIngestAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    parsed_at = datetime.now(timezone.utc).isoformat()
    buy_signals = [item.model_dump(mode="json") for item in body.buy_signals]
    row = SignalEntry(
        symbol=None,
        reference_date=body.reference_date,
        title=body.title,
        notes=body.raw_text,
        payload={
            "source": "cursor-agent",
            "buy_signals": buy_signals,
            "meta": {"title": body.title, "parsed_at": parsed_at},
        },
        data_extracted=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return SignalEntryIngestAgentResponse(
        id=row.id,
        reference_date=row.reference_date,
        created_at=row.created_at,
        buy_signal_count=len(body.buy_signals),
    )


@router.get(
    "/api/v1/newfeeds",
    response_model=NewfeedListResponse,
)
async def list_newfeeds(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    _validate_newfeeds_pagination(limit, offset)
    rows, total = await _query_newfeed_rows(db, limit, offset)
    items = [_to_newfeed_item(row) for row in rows]
    return NewfeedListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/api/v1/newfeeds/refresh-prices",
    response_model=NewfeedListResponse,
)
async def refresh_newfeeds_prices(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    _validate_newfeeds_pagination(limit, offset)
    rows, total = await _query_newfeed_rows(db, limit, offset)
    if not rows:
        return NewfeedListResponse(items=[], total=total, limit=limit, offset=offset)

    symbols: set[str] = set()
    min_reference_date: date | None = None
    for row in rows:
        if row.reference_date and (min_reference_date is None or row.reference_date < min_reference_date):
            min_reference_date = row.reference_date
        for sig in _parse_buy_signals(row.payload):
            symbols.add(sig.symbol)

    if symbols:
        token = get_fireant_token()
        if not token:
            raise HTTPException(
                status_code=500,
                detail="Missing FIREANT_TOKEN for quote refresh",
            )
        fetch_from = min_reference_date or date.today()
        fetch_to = date.today()
        for symbol in sorted(symbols):
            try:
                bars = await fetch_historical_quotes(symbol, fetch_from, fetch_to, token)
                if bars:
                    await upsert_quotes(db, symbol, bars)
            except httpx.HTTPError:
                # Keep endpoint responsive even when a symbol fails to fetch.
                continue

    changed = False
    latest_cache: dict[str, tuple[date, float] | None] = {}
    series_cache: dict[tuple[str, date], list[tuple[date, float]]] = {}

    for row in rows:
        if not isinstance(row.payload, dict):
            continue
        raw_signals = row.payload.get("buy_signals")
        if not isinstance(raw_signals, list):
            continue
        original_json = json.dumps(raw_signals, ensure_ascii=False, sort_keys=True)
        updated_signals: list[dict] = []
        for raw in raw_signals:
            if not isinstance(raw, dict):
                updated_signals.append(raw)
                continue
            signal = dict(raw)
            symbol = str(signal.get("symbol") or "").strip().upper()
            entry_price = signal.get("price")
            if not symbol:
                updated_signals.append(signal)
                continue

            if symbol not in latest_cache:
                latest = await get_latest_close(db, symbol)
                latest_cache[symbol] = (
                    (latest[0], float(latest[1])) if latest is not None else None
                )
            latest_val = latest_cache[symbol]
            if latest_val is not None:
                signal["current_price"] = latest_val[1]
                signal["price_as_of"] = latest_val[0].isoformat()

            ref_date = row.reference_date
            if ref_date is None:
                signal["pnl_3d_pct"] = None
                signal["pnl_5d_pct"] = None
                signal["pnl_10d_pct"] = None
                signal["pnl_basis_trade_dates"] = {"d3": None, "d5": None, "d10": None}
                updated_signals.append(signal)
                continue

            cache_key = (symbol, ref_date)
            if cache_key not in series_cache:
                series = await get_trade_dates_with_close(db, symbol, ref_date)
                series_cache[cache_key] = [(d, float(p)) for d, p in series]
            series = series_cache[cache_key]
            basis_dates: dict[str, str | None] = {"d3": None, "d5": None, "d10": None}

            if entry_price is None:
                signal["pnl_3d_pct"] = None
                signal["pnl_5d_pct"] = None
                signal["pnl_10d_pct"] = None
                signal["pnl_basis_trade_dates"] = basis_dates
                updated_signals.append(signal)
                continue

            try:
                entry = float(entry_price)
                if entry == 0:
                    raise ValueError("entry price cannot be zero")
            except Exception:
                signal["pnl_3d_pct"] = None
                signal["pnl_5d_pct"] = None
                signal["pnl_10d_pct"] = None
                signal["pnl_basis_trade_dates"] = basis_dates
                updated_signals.append(signal)
                continue

            for trading_days, field in (
                (3, "pnl_3d_pct"),
                (5, "pnl_5d_pct"),
                (10, "pnl_10d_pct"),
            ):
                if len(series) > trading_days:
                    d, px = series[trading_days]
                    pnl = ((px - entry) / entry) * 100
                    signal[field] = pnl
                    basis_dates[f"d{trading_days}"] = d.isoformat()
                else:
                    signal[field] = None

            signal["pnl_basis_trade_dates"] = basis_dates
            updated_signals.append(signal)

        if json.dumps(updated_signals, ensure_ascii=False, sort_keys=True) != original_json:
            new_payload = dict(row.payload)
            new_payload["buy_signals"] = updated_signals
            row.payload = new_payload
            row.updated_at = datetime.now(timezone.utc)
            changed = True

    if changed:
        await db.commit()

    items = [_to_newfeed_item(row) for row in rows]
    return NewfeedListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch(
    "/api/v1/admin/signal-entries/{entry_id}",
    response_model=SignalEntryOut,
)
async def patch_signal_entry(
    entry_id: int,
    body: SignalEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SignalEntry).where(SignalEntry.id == entry_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="signal entry not found")

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return SignalEntryOut.model_validate(row)


@router.delete("/api/v1/admin/signal-entries/{entry_id}", response_model=SignalEntryOut)
async def soft_delete_signal_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SignalEntry).where(SignalEntry.id == entry_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="signal entry not found")
    row.deleted_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return SignalEntryOut.model_validate(row)
