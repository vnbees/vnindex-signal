"""API GET đồng bộ Fireant→DB và đọc snapshot Balanced (theo plan)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.balanced import (
    BalancedSectorFlow5DResponse,
    BalancedSnapshotResponse,
    BalancedSyncResponse,
)
from services.balanced_sync_service import (
    load_sector_flow_5d_payload,
    load_snapshot_payload,
    run_balanced_sync,
)
from services.fireant_quote_service import require_fireant_token

router = APIRouter(tags=["balanced"])


@router.get(
    "/api/v1/balanced/sync",
    response_model=BalancedSyncResponse,
    summary="Đồng bộ Fireant → Postgres + snapshot JSON (226 mã), không cần API key",
)
async def balanced_sync_fireant(
    db: AsyncSession = Depends(get_db),
):
    try:
        token = require_fireant_token()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        summary = await run_balanced_sync(db, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return BalancedSyncResponse(**summary)


@router.get(
    "/api/v1/balanced/snapshot",
    response_model=BalancedSnapshotResponse,
    summary="Đọc snapshot mới nhất hoặc theo ngày (chỉ DB, không gọi Fireant)",
)
async def balanced_read_snapshot(
    as_of_date: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    as_of: date | None = None
    if as_of_date:
        try:
            as_of = date.fromisoformat(as_of_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="as_of_date must be YYYY-MM-DD") from None
    payload = await load_snapshot_payload(db, as_of)
    if not payload:
        return BalancedSnapshotResponse(found=False, payload=None)
    return BalancedSnapshotResponse(found=True, payload=payload)


@router.get(
    "/api/v1/balanced/sector-flow-5d",
    response_model=BalancedSectorFlow5DResponse,
    summary="Dòng tiền ngành 5 phiên gần nhất (đọc từ snapshot DB)",
)
async def balanced_sector_flow_5d(
    as_of_date: str | None = None,
    sessions: int = 5,
    db: AsyncSession = Depends(get_db),
):
    as_of: date | None = None
    if as_of_date:
        try:
            as_of = date.fromisoformat(as_of_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="as_of_date must be YYYY-MM-DD") from None

    payload = await load_sector_flow_5d_payload(db, as_of=as_of, sessions=sessions)
    if not payload:
        return BalancedSectorFlow5DResponse(found=False, as_of_date=None, sessions=[], sectors=[])
    return BalancedSectorFlow5DResponse(**payload)
