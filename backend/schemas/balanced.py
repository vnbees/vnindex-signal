from typing import Any

from pydantic import BaseModel, Field


class BalancedSyncResponse(BaseModel):
    synced_at: str
    as_of_date: str | None = None
    symbols_total: int
    symbols_ok: int
    errors_count: int
    errors: list[dict[str, str]] = Field(default_factory=list)
    snapshot_top9_count: int = 0
    screened_top3_symbols: list[str] = Field(default_factory=list)


class BalancedSnapshotResponse(BaseModel):
    """Payload đọc từ DB — cấu trúc theo balanced_sync_service."""

    found: bool
    payload: dict[str, Any] | None = None
