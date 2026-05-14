"""
Soft-delete mọi signal_entries theo reference_date (mặc định: ngày hôm nay theo Asia/Ho_Chi_Minh),
rồi gọi POST /api/v1/automation/daily-balanced-trigger để chạy lại pipeline (nền).

Chạy trên Railway (backend):
  railway run --service backend python scripts/reset_newsfeed_day.py

Local (cần .env có DATABASE_URL, AUTOMATION_BASE_URL, AUTOMATION_TOKEN):
  cd backend && python scripts/reset_newsfeed_day.py

Tuỳ chọn:
  python scripts/reset_newsfeed_day.py --date 2026-05-10
  python scripts/reset_newsfeed_day.py --skip-automation   # chỉ xóa
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import update

from database import AsyncSessionLocal
from models.signal_entry import SignalEntry


def _vn_today() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


async def soft_delete_entries_for_date(d: date) -> int:
    async with AsyncSessionLocal() as session:
        stmt = (
            update(SignalEntry)
            .where(
                SignalEntry.reference_date == d,
                SignalEntry.deleted_at.is_(None),
            )
            .values(
                deleted_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return int(result.rowcount or 0)


async def trigger_daily_balanced_run() -> tuple[int, str]:
    base = (os.environ.get("AUTOMATION_BASE_URL") or "http://localhost:8000").rstrip("/")
    token = (os.environ.get("AUTOMATION_TOKEN") or "").strip()
    if not token:
        return 0, "AUTOMATION_TOKEN trống — bỏ qua bước chạy lại automation."

    # Chạy nền — tránh timeout khi pipeline Gemini/Fireant dài.
    url = f"{base}/api/v1/automation/daily-balanced-trigger"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers={"X-Automation-Token": token})
        body = (r.text or "")[:2000]
        return r.status_code, body


async def main() -> None:
    p = argparse.ArgumentParser(description="Xóa newsfeed theo ngày + chạy lại automation")
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="reference_date YYYY-MM-DD (mặc định: hôm nay theo giờ VN)",
    )
    p.add_argument("--skip-automation", action="store_true", help="Chỉ soft-delete, không gọi API automation")
    args = p.parse_args()

    if args.date:
        d = date.fromisoformat(args.date)
    else:
        d = _vn_today()

    print(f"reference_date = {d.isoformat()}")
    n = await soft_delete_entries_for_date(d)
    print(f"Đã soft-delete {n} bản ghi signal_entries (reference_date={d}).")

    if args.skip_automation:
        print("Đã --skip-automation, kết thúc.")
        return

    status, detail = await trigger_daily_balanced_run()
    print(f"automation HTTP {status}")
    print(detail)


if __name__ == "__main__":
    asyncio.run(main())
