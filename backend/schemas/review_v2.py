from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewV2BuySignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    symbol: str
    sector: str | None = None
    recommendation: str = "THEO DÕI MUA"
    price: float | None = None
    why_selected: list[str] = Field(default_factory=list)
    sector_flow_pct: float | None = None


class ReviewV2CandidatesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    reference_date: date
    as_of_date: date
    title: str
    source: str = "api.fireant.vn"
    screened_count: int
    display_count: int
    buy_signals: list[ReviewV2BuySignal]
    cached: bool = False
    computed_at: datetime


class ReviewV2PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbols: list[str] = Field(..., min_length=1)


class ReviewV2PublishResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    entry_id: int
    reference_date: date
    published_symbols: list[str]
    buy_signal_count: int
