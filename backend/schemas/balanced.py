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


class BalancedSectorFlow5DPoint(BaseModel):
    date: str
    positive_money_flow_vnd: float | None = None
    positive_money_flow_pct_vs_5d_avg: float | None = None


class BalancedSectorFlow5DRow(BaseModel):
    sector: str
    sector_group: str | None = None
    icb_code: str | None = None
    points: list[BalancedSectorFlow5DPoint] = Field(default_factory=list)


class BalancedSectorFlow5DResponse(BaseModel):
    found: bool
    as_of_date: str | None = None
    sessions: list[str] = Field(default_factory=list)
    sectors: list[BalancedSectorFlow5DRow] = Field(default_factory=list)
