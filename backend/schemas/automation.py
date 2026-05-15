from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from schemas.signal_entry import BuySignalIn


class AutomationStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ok: bool
    detail: str | None = None
    payload: dict[str, Any] | None = None


class DailyAutomationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    run_id: str
    skipped: bool = False
    reason: str | None = None
    reference_date: date | None = None
    title: str | None = None
    buy_signals: list[BuySignalIn] = []
    raw_text_preview: str | None = None
    steps: list[AutomationStepResult]


class DailyAutomationTriggerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    accepted: bool
    run_id: str
    detail: str
    dry_run: bool = False
    force: bool = False
    use_mock_result: bool = Field(
        default=False,
        deprecated=True,
        description="Deprecated; luôn false — automation balanced không còn mock Gemini.",
    )
