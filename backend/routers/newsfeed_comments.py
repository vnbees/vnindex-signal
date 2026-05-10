from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.newsfeed_comment import NewsfeedComment
from models.signal_entry import SignalEntry
from schemas.newsfeed_comment import (
    NewsfeedCommentCreate,
    NewsfeedCommenterIdentityOut,
    NewsfeedCommentListResponse,
    NewsfeedCommentOut,
)
from services.newsfeed_commenter_alias import display_name_for_commenter

router = APIRouter(tags=["newsfeed-comments"])


async def _entry_is_published_newfeed(db: AsyncSession, entry_id: int) -> bool:
    cond = (
        SignalEntry.id == entry_id,
        SignalEntry.deleted_at.is_(None),
        SignalEntry.data_extracted.is_(True),
    )
    q = select(func.count()).select_from(SignalEntry).where(*cond)
    n = (await db.execute(q)).scalar_one()
    return int(n or 0) > 0


async def _resolve_display_name(db: AsyncSession, commenter_id: UUID) -> str:
    q = (
        select(NewsfeedComment.display_name)
        .where(NewsfeedComment.commenter_id == commenter_id)
        .order_by(NewsfeedComment.id.asc())
        .limit(1)
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if row:
        return row
    return display_name_for_commenter(commenter_id)


@router.get(
    "/api/v1/newsfeed/commenter-identity",
    response_model=NewsfeedCommenterIdentityOut,
)
async def get_newsfeed_commenter_identity(
    commenter_id: UUID = Query(..., description="UUID cố định trên trình duyệt (localStorage)"),
    db: AsyncSession = Depends(get_db),
):
    display_name = await _resolve_display_name(db, commenter_id)
    return NewsfeedCommenterIdentityOut(display_name=display_name)


@router.get(
    "/api/v1/newfeeds/{entry_id}/comments",
    response_model=NewsfeedCommentListResponse,
)
async def list_newsfeed_comments(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
):
    if not await _entry_is_published_newfeed(db, entry_id):
        raise HTTPException(status_code=404, detail="newsfeed entry not found")

    q = (
        select(NewsfeedComment)
        .where(
            NewsfeedComment.signal_entry_id == entry_id,
            NewsfeedComment.deleted_at.is_(None),
        )
        .order_by(NewsfeedComment.created_at.asc(), NewsfeedComment.id.asc())
    )
    rows = (await db.execute(q)).scalars().all()
    return NewsfeedCommentListResponse(
        items=[
            NewsfeedCommentOut(
                id=r.id,
                signal_entry_id=r.signal_entry_id,
                display_name=r.display_name,
                body=r.body,
                created_at=r.created_at,
            )
            for r in rows
        ]
    )


@router.post(
    "/api/v1/newfeeds/{entry_id}/comments",
    response_model=NewsfeedCommentOut,
    status_code=201,
)
async def create_newsfeed_comment(
    entry_id: int,
    body: NewsfeedCommentCreate,
    db: AsyncSession = Depends(get_db),
):
    if not await _entry_is_published_newfeed(db, entry_id):
        raise HTTPException(status_code=404, detail="newsfeed entry not found")

    display_name = await _resolve_display_name(db, body.commenter_id)
    row = NewsfeedComment(
        signal_entry_id=entry_id,
        commenter_id=body.commenter_id,
        display_name=display_name,
        body=body.body,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return NewsfeedCommentOut(
        id=row.id,
        signal_entry_id=row.signal_entry_id,
        display_name=row.display_name,
        body=row.body,
        created_at=row.created_at,
    )


@router.delete(
    "/api/v1/newfeeds/comments/{comment_id}",
    status_code=204,
)
async def delete_newsfeed_comment(
    comment_id: int,
    admin: str | None = Query(None, description="Phải là true — cùng ý nghĩa với ?admin=true trên trang newsfeed."),
    db: AsyncSession = Depends(get_db),
):
    if admin != "true":
        raise HTTPException(
            status_code=403,
            detail="Thêm query admin=true khi gọi DELETE (ví dụ ?admin=true).",
        )

    result = await db.execute(select(NewsfeedComment).where(NewsfeedComment.id == comment_id))
    row = result.scalar_one_or_none()
    if not row or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="comment not found")

    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return None
