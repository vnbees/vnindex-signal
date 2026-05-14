"""
Soft-delete signal_entries rồi gọi POST /api/v1/automation/daily-balanced-trigger (chạy nền).

Hai chế độ xóa:
  - Mặc định (legacy): mọi bản ghi chưa xóa theo reference_date (= hôm nay VN hoặc --date).
  - --pending-only: chỉ bản chờ review (data_extracted=false); an toàn, không đụng bản đã publish lên newsfeed.
    + Có --date: chỉ pending của ngày đó.
    + Không --date: xóa toàn bộ pending trên mọi ngày (dọn sạch trang /review-signal-entries).

Chạy trên Railway (backend):
  railway run --service backend python scripts/reset_newsfeed_day.py --pending-only --date 2026-05-14

Local (cần .env: DATABASE_URL, AUTOMATION_BASE_URL, AUTOMATION_TOKEN):
  cd backend && python scripts/reset_newsfeed_day.py --pending-only --date 2026-05-14

Tuỳ chọn:
  python scripts/reset_newsfeed_day.py --date 2026-05-10
  python scripts/reset_newsfeed_day.py --pending-only --date 2026-05-14
  python scripts/reset_newsfeed_day.py --skip-automation   # chỉ xóa

Nếu sau khi xóa vẫn bị skip vì còn bản đã publish cùng ngày: bật AUTOMATION_ALLOW_FORCE_RERUN trên server
và gọi trigger với force (đặt env AUTOMATION_FORCE_RERUN=1 khi chạy script — script sẽ gửi ?force=true).
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


async def soft_delete_pending_review(*, ref_date: date | None) -> int:
    """Chỉ các entry chờ publish (data_extracted=false). ref_date=None → mọi ngày."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        cond = [SignalEntry.deleted_at.is_(None), SignalEntry.data_extracted.is_(False)]
        if ref_date is not None:
            cond.append(SignalEntry.reference_date == ref_date)
        stmt = update(SignalEntry).where(*cond).values(deleted_at=now, updated_at=now)
        result = await session.execute(stmt)
        await session.commit()
        return int(result.rowcount or 0)


async def trigger_daily_balanced_run() -> tuple[int, str]:
    base = (os.environ.get("AUTOMATION_BASE_URL") or "http://localhost:8000").rstrip("/")
    token = (os.environ.get("AUTOMATION_TOKEN") or "").strip()
    if not token:
        return 0, "AUTOMATION_TOKEN trống — bỏ qua bước chạy lại automation."

    force = os.environ.get("AUTOMATION_FORCE_RERUN", "").strip().lower() in ("1", "true", "yes")
    params: dict[str, str] = {}
    if force:
        params["force"] = "true"

    # Chạy nền — tránh timeout khi pipeline Gemini/Fireant dài.
    url = f"{base}/api/v1/automation/daily-balanced-trigger"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers={"X-Automation-Token": token}, params=params)
        body = (r.text or "")[:2000]
        return r.status_code, body


async def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    p = argparse.ArgumentParser(description="Xóa signal_entries + chạy lại automation (tuỳ chọn)")
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="reference_date YYYY-MM-DD (với chế độ legacy: mặc định hôm nay VN; với --pending-only: lọc pending theo ngày, bỏ trống = mọi ngày)",
    )
    p.add_argument(
        "--pending-only",
        action="store_true",
        help="Chỉ xóa entry chờ review (không xóa bản đã publish); khuyến nghị cho trang /review-signal-entries",
    )
    p.add_argument("--skip-automation", action="store_true", help="Chỉ soft-delete, không gọi API automation")
    args = p.parse_args()

    if args.pending_only:
        ref: date | None = date.fromisoformat(args.date) if args.date else None
        scope = ref.isoformat() if ref else "mọi ngày (toàn bộ pending)"
        print(f"Chế độ: pending-only | phạm vi reference_date = {scope}")
        n = await soft_delete_pending_review(ref_date=ref)
        print(f"Đã soft-delete {n} bản ghi chờ review (data_extracted=false).")
    else:
        d = date.fromisoformat(args.date) if args.date else _vn_today()
        print(f"Chế độ: theo ngày (mọi trạng thái) | reference_date = {d.isoformat()}")
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
