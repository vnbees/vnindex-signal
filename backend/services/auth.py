import bcrypt
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.signal import ApiKey
from config import settings

async def verify_api_key(
    authorization: str = Header(..., description="Bearer {API_KEY}"),
    db: AsyncSession = Depends(get_db)
) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    raw_key = authorization[7:]

    # Check all active keys
    result = await db.execute(
        select(ApiKey).where(ApiKey.is_active == True)
    )
    api_keys = result.scalars().all()

    for api_key in api_keys:
        if bcrypt.checkpw(raw_key.encode(), api_key.key_hash.encode()):
            # Update last_used (non-blocking, best effort)
            api_key.last_used = datetime.now(timezone.utc)
            try:
                await db.flush()
            except Exception:
                pass
            # Audit
            from models.signal import AuditLog
            db.add(AuditLog(action="key.auth", api_key_id=api_key.id))
            try:
                await db.commit()
            except Exception:
                await db.rollback()
            return api_key.id

    raise HTTPException(status_code=401, detail="Invalid API key")
