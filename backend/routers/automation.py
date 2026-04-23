from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from schemas.automation import DailyAutomationResponse
from services.daily_automation_service import run_daily_balanced_automation

router = APIRouter(tags=["automation"])


@router.post(
    "/api/v1/automation/daily-balanced-run",
    response_model=DailyAutomationResponse,
    summary="Run daily balanced automation pipeline",
)
async def run_daily_automation(
    dry_run: bool = False,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    x_automation_token: str | None = Header(default=None, alias="X-Automation-Token"),
):
    expected = settings.automation_token
    if not expected:
        raise HTTPException(status_code=503, detail="AUTOMATION_TOKEN is not configured")
    if x_automation_token != expected:
        raise HTTPException(status_code=401, detail="Invalid automation token")

    prompt_file = Path(__file__).resolve().parents[1] / "prompt-signal-cash-flow.md"

    try:
        return await run_daily_balanced_automation(
            db,
            dry_run=dry_run,
            force=force,
            prompt_file_path=str(prompt_file) if prompt_file.exists() else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
