"""Review v2 API — on-demand FireAnt candidates and publish."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.signal_entry import SignalEntry
from schemas.review_v2 import (
    ReviewV2CandidatesResponse,
    ReviewV2PublishRequest,
    ReviewV2PublishResponse,
)
from services.fireant_quote_service import require_fireant_token
from services.review_v2_service import compute_review_v2_candidates

router = APIRouter(tags=["review-v2"])


@router.get(
    "/api/v1/review-v2/candidates",
    response_model=ReviewV2CandidatesResponse,
    summary="Tín hiệu review live từ api.fireant.vn (cache TTL)",
)
async def get_review_v2_candidates(
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
):
    try:
        require_fireant_token()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    try:
        return await compute_review_v2_candidates(db, refresh=refresh)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/api/v1/review-v2/publish",
    response_model=ReviewV2PublishResponse,
    summary="Publish mã đã chọn từ review v2 lên newsfeed",
)
async def publish_review_v2(
    body: ReviewV2PublishRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        require_fireant_token()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    requested = sorted({s.strip().upper() for s in body.symbols if s and s.strip()})
    if not requested:
        raise HTTPException(status_code=400, detail="symbols must contain at least one valid symbol")

    try:
        candidates = await compute_review_v2_candidates(db, refresh=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    allowed = {sig.symbol for sig in candidates.buy_signals}
    invalid = sorted([s for s in requested if s not in allowed])
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"symbols not in current review-v2 candidates: {', '.join(invalid)}",
        )

    selected = [sig.model_dump(mode="json") for sig in candidates.buy_signals if sig.symbol in requested]
    if not selected:
        raise HTTPException(status_code=400, detail="no symbols selected for publish")

    raw_lines = [candidates.title, f"Phân tích dựa trên dữ liệu ngày {candidates.reference_date.strftime('%d/%m/%Y')}", ""]
    for sig in candidates.buy_signals:
        if sig.symbol not in requested:
            continue
        raw_lines.append(f"#{sig.rank}. {sig.symbol}" + (f" - {sig.sector}" if sig.sector else ""))
        raw_lines.append("Khuyến nghị: THEO DÕI MUA")
        if sig.price is not None:
            raw_lines.append(f"Giá hiện tại {sig.price} VND")
        for reason in sig.why_selected:
            raw_lines.append(f"- {reason}")
        raw_lines.append("")

    parsed_at = datetime.now(timezone.utc).isoformat()
    row = SignalEntry(
        symbol=None,
        reference_date=candidates.reference_date,
        title=candidates.title,
        notes="\n".join(raw_lines).strip(),
        payload={
            "source": "review-v2-fireant",
            "buy_signals": selected,
            "meta": {
                "title": candidates.title,
                "parsed_at": parsed_at,
                "review_published_at": parsed_at,
                "fireant_api_base": "api.fireant.vn",
            },
        },
        data_extracted=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return ReviewV2PublishResponse(
        entry_id=row.id,
        reference_date=row.reference_date,
        published_symbols=requested,
        buy_signal_count=len(selected),
    )
