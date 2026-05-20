from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.stock_position import StockPosition
from schemas.stock_position import (
    StockPositionCreate,
    StockPositionListResponse,
    StockPositionOut,
    StockPositionRefreshResponse,
    StockPositionSell,
)
from services.position_price_service import refresh_positions_prices

router = APIRouter(tags=["stock-positions"])


def _position_status(row: StockPosition) -> str:
    return "closed" if row.sell_price is not None else "open"


def _to_out(row: StockPosition) -> StockPositionOut:
    return StockPositionOut(
        id=row.id,
        symbol=row.symbol,
        signal_date=row.signal_date,
        valuation_price=float(row.valuation_price) if row.valuation_price is not None else None,
        buy_price=float(row.buy_price),
        sell_price=float(row.sell_price) if row.sell_price is not None else None,
        sell_date=row.sell_date,
        current_price=float(row.current_price) if row.current_price is not None else None,
        price_as_of=row.price_as_of,
        unrealized_pnl_pct=float(row.unrealized_pnl_pct) if row.unrealized_pnl_pct is not None else None,
        realized_pnl_pct=float(row.realized_pnl_pct) if row.realized_pnl_pct is not None else None,
        pnl_3d_pct=float(row.pnl_3d_pct) if row.pnl_3d_pct is not None else None,
        pnl_5d_pct=float(row.pnl_5d_pct) if row.pnl_5d_pct is not None else None,
        pnl_10d_pct=float(row.pnl_10d_pct) if row.pnl_10d_pct is not None else None,
        status=_position_status(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _load_positions(
    db: AsyncSession,
    *,
    status: str = "all",
) -> list[StockPosition]:
    q = select(StockPosition).order_by(
        StockPosition.sell_price.is_(None).desc(),
        StockPosition.signal_date.desc(),
        StockPosition.created_at.desc(),
    )
    if status == "open":
        q = q.where(StockPosition.sell_price.is_(None))
    elif status == "closed":
        q = q.where(StockPosition.sell_price.is_not(None))
    return (await db.execute(q)).scalars().all()


@router.get("/api/v1/stock-positions", response_model=StockPositionListResponse)
async def list_stock_positions(
    status: str = "all",
    db: AsyncSession = Depends(get_db),
):
    if status not in ("all", "open", "closed"):
        raise HTTPException(status_code=400, detail="status must be all, open, or closed")
    rows = await _load_positions(db, status=status)
    items = [_to_out(r) for r in rows]
    return StockPositionListResponse(items=items, total=len(items))


@router.post("/api/v1/stock-positions", response_model=StockPositionOut, status_code=201)
async def create_stock_position(
    body: StockPositionCreate,
    db: AsyncSession = Depends(get_db),
):
    row = StockPosition(
        symbol=body.symbol,
        signal_date=body.signal_date,
        valuation_price=Decimal(str(body.valuation_price)) if body.valuation_price is not None else None,
        buy_price=Decimal(str(body.buy_price)),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await refresh_positions_prices(db, [row])
    await db.refresh(row)
    return _to_out(row)


@router.patch("/api/v1/stock-positions/{position_id}/sell", response_model=StockPositionOut)
async def sell_stock_position(
    position_id: int,
    body: StockPositionSell,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(StockPosition).where(StockPosition.id == position_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="position not found")
    if row.sell_price is not None:
        raise HTTPException(status_code=400, detail="position already sold")
    if body.sell_date < row.signal_date:
        raise HTTPException(status_code=400, detail="sell_date must be >= signal_date")

    buy = float(row.buy_price)
    sell = body.sell_price
    row.sell_price = Decimal(str(sell))
    row.sell_date = body.sell_date
    row.realized_pnl_pct = Decimal(str(((sell - buy) / buy) * 100))
    row.unrealized_pnl_pct = None
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return _to_out(row)


@router.delete("/api/v1/stock-positions/{position_id}", status_code=204)
async def delete_stock_position(
    position_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(StockPosition).where(StockPosition.id == position_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="position not found")
    await db.delete(row)
    await db.commit()


@router.get("/api/v1/stock-positions/refresh-prices", response_model=StockPositionRefreshResponse)
async def refresh_stock_positions_prices(
    db: AsyncSession = Depends(get_db),
):
    rows = await _load_positions(db, status="all")
    updated = await refresh_positions_prices(db, rows)
    for row in rows:
        await db.refresh(row)
    items = [_to_out(r) for r in rows]
    return StockPositionRefreshResponse(updated=updated, items=items, total=len(items))
