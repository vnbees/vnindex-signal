from datetime import date
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, field_validator

class SignalInput(BaseModel):
    symbol: str
    score_financial: int
    score_seasonal: int
    score_technical: int
    score_cashflow: int
    score_total: int
    recommendation: str
    price_close_signal_date: Decimal
    market_cap_bil: Optional[Decimal] = None
    detail_financial: Optional[dict[str, Any]] = None
    detail_technical: Optional[dict[str, Any]] = None
    detail_cashflow: Optional[dict[str, Any]] = None
    detail_seasonal: Optional[dict[str, Any]] = None

    @field_validator('recommendation')
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        allowed = {"BUY_STRONG", "BUY", "HOLD", "AVOID", "SELL"}
        if v not in allowed:
            raise ValueError(f"recommendation must be one of {allowed}")
        return v

class SignalBatchInput(BaseModel):
    run_date: date
    top_n: int = 30
    hold_days: int = 20
    signals: list[SignalInput]
