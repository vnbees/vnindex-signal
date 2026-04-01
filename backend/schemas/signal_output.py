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
    portfolio_kind: str = "top_cap"
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


class SymbolStatSummary(BaseModel):
    symbol: str
    total_signals: int
    buy_strong_count: int
    buy_count: int
    hold_count: int
    avg_pnl_d3: Optional[Decimal] = None
    avg_pnl_d10: Optional[Decimal] = None
    avg_pnl_d20: Optional[Decimal] = None
    avg_latest_pnl: Optional[Decimal] = None
    winrate_d3: Optional[Decimal] = None
    winrate_d10: Optional[Decimal] = None
    winrate_d20: Optional[Decimal] = None


class AllocationSuggestionItem(BaseModel):
    symbol: str
    recommendation: str
    reference_price: Decimal
    final_score: Decimal
    allocated_amount: Decimal
    quantity: int
    amount_to_buy: Decimal
    reasons: list[str]


class AllocationSuggestionResponse(BaseModel):
    run_date: date
    portfolio_kind: str
    capital: Decimal
    total_planned: Decimal
    cash_left: Decimal
    lot_size: int
    min_required_capital: Optional[Decimal] = None
    min_required_symbol: Optional[str] = None
    min_required_reference_price: Optional[Decimal] = None
    no_result_message: Optional[str] = None
    suggestions: list[AllocationSuggestionItem]
