from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.signal_entry import SignalEntry
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
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

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
    items = [
        NewfeedItem(
            id=row.id,
            reference_date=row.reference_date,
            created_at=row.created_at,
            title=row.title,
            raw_text=row.notes or "",
            raw_text_preview=_truncate_preview(row.notes or ""),
            buy_signals=_parse_buy_signals(row.payload),
        )
        for row in rows
    ]
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
