import asyncio
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import AsyncSessionLocal, get_db
from schemas.automation import DailyAutomationResponse, DailyAutomationTriggerResponse
from services.daily_automation_service import run_daily_balanced_automation

router = APIRouter(tags=["automation"])
_active_daily_run: asyncio.Task | None = None


def _assert_token(x_automation_token: str | None) -> None:
    expected = settings.automation_token
    if not expected:
        raise HTTPException(status_code=503, detail="AUTOMATION_TOKEN is not configured")
    if x_automation_token != expected:
        raise HTTPException(status_code=401, detail="Invalid automation token")


def _assert_force_allowed(force: bool) -> None:
    if force and not settings.automation_allow_force_rerun:
        raise HTTPException(status_code=400, detail="force rerun is disabled")


@router.post(
    "/api/v1/automation/daily-balanced-run",
    response_model=DailyAutomationResponse,
    summary="Chạy pipeline balanced hàng ngày (snapshot-only, không Gemini; không cần GOOGLE_GEMINI_API_KEY).",
)
async def run_daily_automation(
    dry_run: bool = False,
    force: bool = False,
    use_mock_result: bool = Query(
        False,
        deprecated=True,
        description="Deprecated, luôn bỏ qua: job chỉ dùng snapshot đã sync, không còn mock Gemini.",
    ),
    db: AsyncSession = Depends(get_db),
    x_automation_token: str | None = Header(default=None, alias="X-Automation-Token"),
):
    _ = use_mock_result  # noop — giữ query param để client cũ không lỗi
    _assert_token(x_automation_token)
    _assert_force_allowed(force)

    try:
        return await run_daily_balanced_automation(
            db,
            dry_run=dry_run,
            force=force,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _run_daily_automation_in_background(*, dry_run: bool, force: bool) -> None:
    async with AsyncSessionLocal() as db:
        await run_daily_balanced_automation(
            db,
            dry_run=dry_run,
            force=force,
        )


@router.post(
    "/api/v1/automation/daily-balanced-trigger",
    response_model=DailyAutomationTriggerResponse,
    summary="Trigger pipeline balanced hàng ngày nền (snapshot-only, không Gemini).",
)
async def trigger_daily_automation(
    dry_run: bool = False,
    force: bool = False,
    use_mock_result: bool = Query(
        False,
        deprecated=True,
        description="Deprecated, luôn bỏ qua.",
    ),
    x_automation_token: str | None = Header(default=None, alias="X-Automation-Token"),
):
    global _active_daily_run
    _ = use_mock_result
    _assert_token(x_automation_token)
    _assert_force_allowed(force)

    if _active_daily_run and not _active_daily_run.done():
        raise HTTPException(status_code=409, detail="A daily automation run is already in progress")

    run_id = uuid.uuid4().hex
    _active_daily_run = asyncio.create_task(
        _run_daily_automation_in_background(
            dry_run=dry_run,
            force=force,
        ),
        name=f"daily-balanced-trigger-{run_id}",
    )
    return DailyAutomationTriggerResponse(
        ok=True,
        accepted=True,
        run_id=run_id,
        detail="Daily automation accepted and running in background",
        dry_run=dry_run,
        force=force,
        use_mock_result=False,
    )
