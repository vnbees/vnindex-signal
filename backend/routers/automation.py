import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import AsyncSessionLocal, get_db
from schemas.automation import DailyAutomationResponse, DailyAutomationTriggerResponse
from services.daily_automation_service import run_daily_balanced_automation

router = APIRouter(tags=["automation"])
_active_daily_run: asyncio.Task | None = None
logger = logging.getLogger(__name__)


def _log_background_automation_done(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc is not None:
        logger.exception("daily-balanced automation background task failed", exc_info=exc)


def _assert_token(x_automation_token: str | None) -> None:
    expected = settings.automation_token
    if not expected:
        raise HTTPException(status_code=503, detail="AUTOMATION_TOKEN is not configured")
    if x_automation_token != expected:
        raise HTTPException(status_code=401, detail="Invalid automation token")


def _assert_mock_allowed(use_mock_result: bool) -> None:
    if use_mock_result and not settings.automation_allow_mock_result:
        raise HTTPException(status_code=400, detail="use_mock_result is disabled")


def _assert_force_allowed(force: bool) -> None:
    if force and not settings.automation_allow_force_rerun:
        raise HTTPException(status_code=400, detail="force rerun is disabled")


@router.post(
    "/api/v1/automation/daily-balanced-run",
    response_model=DailyAutomationResponse,
    summary="Run daily balanced automation pipeline",
)
async def run_daily_automation(
    dry_run: bool = False,
    force: bool = False,
    use_mock_result: bool = False,
    db: AsyncSession = Depends(get_db),
    x_automation_token: str | None = Header(default=None, alias="X-Automation-Token"),
):
    _assert_token(x_automation_token)
    _assert_mock_allowed(use_mock_result)
    _assert_force_allowed(force)

    prompt_file = Path(__file__).resolve().parents[1] / "prompt-signal-cash-flow.md"

    try:
        return await run_daily_balanced_automation(
            db,
            dry_run=dry_run,
            force=force,
            use_mock_result=use_mock_result,
            prompt_file_path=str(prompt_file) if prompt_file.exists() else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _run_daily_automation_in_background(*, dry_run: bool, force: bool, use_mock_result: bool) -> None:
    prompt_file = Path(__file__).resolve().parents[1] / "prompt-signal-cash-flow.md"
    async with AsyncSessionLocal() as db:
        await run_daily_balanced_automation(
            db,
            dry_run=dry_run,
            force=force,
            use_mock_result=use_mock_result,
            prompt_file_path=str(prompt_file) if prompt_file.exists() else None,
        )


@router.post(
    "/api/v1/automation/daily-balanced-trigger",
    response_model=DailyAutomationTriggerResponse,
    summary="Trigger daily balanced automation in background",
)
async def trigger_daily_automation(
    dry_run: bool = False,
    force: bool = False,
    use_mock_result: bool = False,
    x_automation_token: str | None = Header(default=None, alias="X-Automation-Token"),
):
    global _active_daily_run
    _assert_token(x_automation_token)
    _assert_mock_allowed(use_mock_result)
    _assert_force_allowed(force)

    if _active_daily_run and not _active_daily_run.done():
        raise HTTPException(status_code=409, detail="A daily automation run is already in progress")

    run_id = uuid.uuid4().hex
    task = asyncio.create_task(
        _run_daily_automation_in_background(
            dry_run=dry_run,
            force=force,
            use_mock_result=use_mock_result,
        ),
        name=f"daily-balanced-trigger-{run_id}",
    )
    task.add_done_callback(_log_background_automation_done)
    _active_daily_run = task
    return DailyAutomationTriggerResponse(
        ok=True,
        accepted=True,
        run_id=run_id,
        detail="Daily automation accepted and running in background",
        dry_run=dry_run,
        force=force,
        use_mock_result=use_mock_result,
    )
