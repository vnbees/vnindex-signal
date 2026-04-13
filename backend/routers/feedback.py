import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.feedback import Feedback
from schemas.feedback import FeedbackCreate, FeedbackOut

router = APIRouter(tags=["feedback"])

# Allow http(s) URLs and relative paths for same-origin
_PAGE_URL_RE = re.compile(r"^(https?://[^\s]+|/[^\s]*)$", re.IGNORECASE)


@router.post("/api/v1/feedback", response_model=FeedbackOut)
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    if not _PAGE_URL_RE.match(payload.page_url):
        raise HTTPException(
            status_code=400,
            detail="page_url must be a valid http(s) URL or path starting with /",
        )
    if not payload.message:
        raise HTTPException(status_code=400, detail="message is required")

    row = Feedback(
        message=payload.message,
        name=payload.name or None,
        contact=payload.contact or None,
        page_url=payload.page_url,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return FeedbackOut.model_validate(row)


@router.get("/api/v1/admin/feedback", response_model=list[FeedbackOut])
async def list_feedback(
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    result = await db.execute(
        select(Feedback)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()
    return [FeedbackOut.model_validate(r) for r in rows]


# Mount cùng cụm admin — tránh bản deploy cũ chỉ include feedback mà thiếu router riêng signal_entries.
from routers.signal_entries import router as signal_entries_admin_router

router.include_router(signal_entries_admin_router)
