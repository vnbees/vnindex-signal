import asyncio
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

from database import AsyncSessionLocal
from models.signal_entry import SignalEntry
from services.daily_automation_service import run_daily_balanced_automation

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_SCHEDULER_POLL_SECONDS = 45
_RETRY_COOLDOWN_SECONDS = 300


class DailyRunnerScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._last_attempt_at: datetime | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop(), name="daily-balanced-scheduler")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _already_ingested(self, ref_date: date) -> bool:
        async with AsyncSessionLocal() as db:
            q = select(SignalEntry.id).where(
                SignalEntry.reference_date == ref_date,
                SignalEntry.deleted_at.is_(None),
                SignalEntry.data_extracted.is_(True),
            )
            return (await db.execute(q)).first() is not None

    async def _run_once(self) -> None:
        now = datetime.now(_VN_TZ)
        if now.weekday() >= 5:
            return
        if (now.hour, now.minute) < (16, 30):
            return
        if self._last_attempt_at:
            elapsed = (datetime.now(_VN_TZ) - self._last_attempt_at).total_seconds()
            if elapsed < _RETRY_COOLDOWN_SECONDS:
                return

        ref_date = now.date()
        if await self._already_ingested(ref_date):
            return

        self._last_attempt_at = datetime.now(_VN_TZ)
        prompt_file = Path(__file__).resolve().parents[1] / "prompt-signal-cash-flow.md"
        async with AsyncSessionLocal() as db:
            await run_daily_balanced_automation(
                db,
                dry_run=False,
                force=False,
                use_mock_result=False,
                prompt_file_path=str(prompt_file) if prompt_file.exists() else None,
            )

    async def _run_loop(self) -> None:
        while True:
            try:
                await self._run_once()
            except Exception:
                # Keep scheduler alive; it will retry on next poll.
                pass
            await asyncio.sleep(_SCHEDULER_POLL_SECONDS)

