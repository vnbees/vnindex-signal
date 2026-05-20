from datetime import date, datetime
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _today_vn() -> date:
    return datetime.now(_VN_TZ).date()


def _normalize_symbol(v: str) -> str:
    s = str(v).strip().upper()
    if not s:
        raise ValueError("symbol is required")
    if len(s) > 16:
        raise ValueError("symbol must be at most 16 characters")
    return s


class StockPositionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    signal_date: date = Field(default_factory=_today_vn)
    valuation_price: Optional[float] = None
    buy_price: float

    @field_validator("symbol")
    @classmethod
    def symbol_norm(cls, v: str) -> str:
        return _normalize_symbol(v)

    @field_validator("buy_price", "valuation_price")
    @classmethod
    def positive_price(cls, v: Optional[float], info) -> Optional[float]:
        if v is None:
            return None
        if v <= 0:
            raise ValueError(f"{info.field_name} must be > 0")
        return v


class StockPositionSell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sell_price: float
    sell_date: date = Field(default_factory=_today_vn)

    @field_validator("sell_price")
    @classmethod
    def positive_sell(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("sell_price must be > 0")
        return v


class StockPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    signal_date: date
    valuation_price: Optional[float] = None
    buy_price: float
    sell_price: Optional[float] = None
    sell_date: Optional[date] = None
    current_price: Optional[float] = None
    price_as_of: Optional[date] = None
    unrealized_pnl_pct: Optional[float] = None
    realized_pnl_pct: Optional[float] = None
    pnl_3d_pct: Optional[float] = None
    pnl_5d_pct: Optional[float] = None
    pnl_10d_pct: Optional[float] = None
    status: Literal["open", "closed"]
    created_at: datetime
    updated_at: datetime


class StockPositionListResponse(BaseModel):
    items: list[StockPositionOut]
    total: int


class StockPositionRefreshResponse(BaseModel):
    updated: int
    items: list[StockPositionOut]
    total: int
