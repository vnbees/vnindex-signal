from datetime import date
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel

class SignalListItem(BaseModel):
    id: int
    run_date: date
    symbol: str
    status: str
    score_financial: int
    score_seasonal: int
    score_technical: int
    score_cashflow: int
    score_total: int
    recommendation: str
    signal_type: str
    price_close_signal_date: Decimal
    price_open_t1: Optional[Decimal]
    market_cap_bil: Optional[Decimal]
    has_corporate_action: bool
    pnl_d3: Optional[Decimal] = None
    pnl_d10: Optional[Decimal] = None
    pnl_d20: Optional[Decimal] = None
    latest_pnl_pct: Optional[Decimal] = None

    class Config:
        from_attributes = True

class SignalDetail(SignalListItem):
    detail_financial: Optional[dict[str, Any]] = None
    detail_technical: Optional[dict[str, Any]] = None
    detail_cashflow: Optional[dict[str, Any]] = None
    detail_seasonal: Optional[dict[str, Any]] = None

class RunListItem(BaseModel):
    id: int
    run_date: date
    top_n: int
    hold_days: int
    signal_count: int = 0

    class Config:
        from_attributes = True

class PendingPriceUpdate(BaseModel):
    signal_id: int
    symbol: str
    run_date: date
    track_dates_needed: list[date]
    needs_price_open_t1: bool
