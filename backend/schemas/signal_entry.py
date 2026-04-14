from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalize_symbol_optional(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.upper()
    if len(s) > 16:
        raise ValueError("symbol must be at most 16 characters")
    return s


class SignalEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Optional[str] = None
    reference_date: Optional[date] = None
    title: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    data_extracted: bool = False

    @field_validator("symbol")
    @classmethod
    def symbol_norm(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_symbol_optional(v)

    @model_validator(mode="after")
    def require_symbol_or_notes(self):
        has_sym = self.symbol is not None
        has_notes = self.notes is not None and str(self.notes).strip() != ""
        if not has_sym and not has_notes:
            raise ValueError("Cần ít nhất mã CK hoặc nội dung ghi chú.")
        return self

    @field_validator("title", "notes", mode="before")
    @classmethod
    def strip_optional_str(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return v.strip() or None
        return v


class SignalEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Optional[str] = None
    reference_date: Optional[date] = None
    title: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    data_extracted: Optional[bool] = None
    deleted_at: Optional[datetime] = None

    @field_validator("symbol")
    @classmethod
    def symbol_norm(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_symbol_optional(v)

    @field_validator("title", "notes", mode="before")
    @classmethod
    def strip_optional_str(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return v.strip() or None
        return v


class SignalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: Optional[str] = None
    reference_date: Optional[date] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    data_extracted: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SignalEntryListResponse(BaseModel):
    items: list[SignalEntryOut]
    total: int
    limit: int
    offset: int


class BuySignalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: Optional[int] = None
    symbol: str = Field(..., min_length=1, max_length=16)
    recommendation: Optional[str] = None
    sector: Optional[str] = None
    price: Optional[float] = None
    current_price: Optional[float] = None
    pnl_3d_pct: Optional[float] = None
    pnl_5d_pct: Optional[float] = None
    pnl_10d_pct: Optional[float] = None
    price_as_of: Optional[date] = None
    pnl_basis_trade_dates: Optional[dict[str, Optional[date]]] = None

    @field_validator("symbol")
    @classmethod
    def symbol_required_upper(cls, v: str) -> str:
        s = _normalize_symbol_optional(v)
        if s is None:
            raise ValueError("symbol is required")
        return s

    @field_validator("recommendation", "sector", mode="before")
    @classmethod
    def strip_optional_fields(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return v.strip() or None
        return v


class SignalEntryIngestAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=200)
    reference_date: date
    raw_text: str = Field(..., min_length=1)
    buy_signals: list[BuySignalIn] = Field(..., min_length=1)

    @field_validator("title", "raw_text", mode="before")
    @classmethod
    def strip_text_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("raw_text")
    @classmethod
    def ensure_raw_text_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_text must not be empty")
        return v


class SignalEntryIngestAgentResponse(BaseModel):
    ok: bool = True
    id: int
    reference_date: date
    created_at: datetime
    buy_signal_count: int


class NewfeedItem(BaseModel):
    id: int
    reference_date: Optional[date] = None
    created_at: datetime
    title: Optional[str] = None
    raw_text: str
    raw_text_preview: str
    buy_signals: list[BuySignalIn]


class NewfeedListResponse(BaseModel):
    items: list[NewfeedItem]
    total: int
    limit: int
    offset: int
