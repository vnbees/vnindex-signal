#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Đồng bộ tín hiệu top_cap (CANDIDATES) theo từng ngày giao dịch trong khoảng [start, end] lên PROD.

- Scoring theo as_of: dùng backtest_scoring + prices_as_of (không dùng run_analysis.calc_* với TODAY cố định).
- Bước 6A: POST /api/v1/signals cho từng run_date; refresh-views mặc định một lần cuối.
- Bước 6B: update_price_tracking (giống run_analysis_von_it) sau khi xong các ngày.

Preflight (PROD):
  - Đặt FIREANT_TOKEN, API_KEY; WEBSITE_URL trỏ PROD.
  - Calendar: POST /api/v1/admin/seed-calendar nếu PROD chưa seed (khớp logic seed_trading_calendar).
  - GET /price-updates/pending chỉ xét tối đa 10000 signal active; nếu vượt ngưỡng, một phần pending có thể không hiện.

Không sửa main-prompt.txt.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

import httpx

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from seed_trading_calendar import SPECIFIC_HOLIDAYS, is_fixed_holiday

from backtest_scoring import (
    bar_on_date,
    calc_cashflow_score,
    calc_financial_score,
    calc_seasonal_score,
    calc_technical_score,
    get_recommendation,
    prices_as_of,
)
import run_analysis as ra
from run_analysis_von_it import update_price_tracking_for_date


def is_trading_day_local(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    if is_fixed_holiday(d) or d in SPECIFIC_HOLIDAYS:
        return False
    return True


def iter_trading_days(start: date, end: date) -> List[date]:
    out: List[date] = []
    cur = start
    while cur <= end:
        if is_trading_day_local(cur):
            out.append(cur)
        cur += timedelta(days=1)
    return out


async def post_signals_batch(
    run_date: date,
    signals: List[Dict],
    top_n: int,
    hold_days: int,
    website_url: str,
    api_key: str,
    do_refresh: bool,
) -> bool:
    payload = {
        "run_date": run_date.isoformat(),
        "top_n": top_n,
        "hold_days": hold_days,
        "portfolio_kind": "top_cap",
        "signals": signals,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{website_url}/api/v1/signals", json=payload, headers=headers)
        if r.status_code not in (200, 201):
            print(f"❌ POST signals {run_date}: {r.status_code} {r.text[:500]}")
            return False
        body = r.json() if r.content else {}
        errs = body.get("errors") or []
        if errs:
            print(f"⚠️  {run_date}: API errors: {errs[:3]}{'...' if len(errs) > 3 else ''}")
        if do_refresh:
            r2 = await client.post(f"{website_url}/api/v1/admin/refresh-views", json={}, headers=headers)
            if r2.status_code != 200:
                print(f"⚠️  refresh-views: {r2.status_code} — {r2.text[:200]}")
        return True


def build_signals_for_day(
    as_of: date,
    top_stocks: List[Dict],
    mc_map: Dict[str, float],
    price_data: Dict[str, List],
    fin_data: Dict,
) -> List[Dict]:
    score_ss, detail_ss = calc_seasonal_score(as_of)
    signals: List[Dict] = []

    for stock in top_stocks:
        sym = stock["sym"]
        qdesc = price_data.get(sym) or []
        qasc = sorted(qdesc, key=lambda r: (r.get("date") or "")[:10])
        bar = bar_on_date(qasc, as_of)
        if not bar or (bar.get("priceClose") or 0) <= 0:
            continue
        pdesc = prices_as_of(qasc, as_of)
        if len(pdesc) < 5:
            continue

        fin = fin_data.get(sym)
        score_tc, detail_tc = calc_financial_score(sym, fin, as_of)
        score_kt, detail_kt = calc_technical_score(sym, pdesc)
        score_dt, detail_dt = calc_cashflow_score(sym, pdesc)
        total = score_tc + score_ss + score_kt + score_dt
        rec = get_recommendation(total)
        price_close = float(bar.get("priceClose") or 0)
        mc_bil = mc_map.get(sym, 0) / 1e9

        signals.append(
            {
                "symbol": sym,
                "score_financial": score_tc,
                "score_seasonal": score_ss,
                "score_technical": score_kt,
                "score_cashflow": score_dt,
                "score_total": total,
                "recommendation": rec,
                "price_close_signal_date": price_close,
                "market_cap_bil": round(mc_bil, 2),
                "detail_financial": detail_tc,
                "detail_technical": detail_kt,
                "detail_cashflow": detail_dt,
                "detail_seasonal": detail_ss,
            }
        )

    signals.sort(key=lambda x: x["score_total"], reverse=True)
    return signals


async def run_preflight(website_url: str, api_key: str) -> bool:
    """Kiểm tra health, API key, và nhắc về giới hạn pending."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    ok = True
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{website_url}/api/v1/health")
        print(f"GET /api/v1/health → {r.status_code}")
        if r.status_code != 200:
            print(f"   {r.text[:300]}")
            ok = False
        else:
            print(f"   {r.json()}")

        r2 = await client.get(f"{website_url}/api/v1/runs?limit=1", headers=headers)
        print(f"GET /api/v1/runs?limit=1 → {r.status_code}")
        if r2.status_code != 200:
            print(f"   (Bearer) — kiểm tra API_KEY: {r2.text[:200]}")
            ok = False

        r3 = await client.get(f"{website_url}/api/v1/price-updates/pending?limit=5", headers=headers)
        print(f"GET /api/v1/price-updates/pending?limit=5 → {r3.status_code}")
        if r3.status_code != 200:
            ok = False

    print(
        "\nℹ️  Pending chỉ quét tối đa 10000 signal active (mặc định backend). "
        "Nếu tổng signal active > 10000, backfill giá có thể thiếu phần cũ."
    )
    print("ℹ️  Đảm bảo PROD đã seed trading_calendar (POST /api/v1/admin/seed-calendar) nếu POST signals báo không phải ngày giao dịch.\n")
    return ok


async def async_main() -> None:
    p = argparse.ArgumentParser(description="Đồng bộ top_cap YTD lên PROD (theo main-prompt).")
    p.add_argument("--start", type=lambda s: date.fromisoformat(s), default=date(2026, 1, 1))
    p.add_argument("--end", type=lambda s: date.fromisoformat(s), default=None, help="Mặc định: hôm nay (local)")
    p.add_argument("--hold-days", type=int, default=20)
    p.add_argument("--dry-run", action="store_true", help="Tính signals, không POST")
    p.add_argument(
        "--refresh-each-day",
        action="store_true",
        help="Gọi refresh-views sau mỗi ngày (mặc định: chỉ refresh sau batch POST cuối)",
    )
    p.add_argument("--skip-price-tracking", action="store_true", help="Bỏ bước 6B sau khi POST xong")
    p.add_argument(
        "--price-tracking-only",
        action="store_true",
        help="Chỉ chạy bước 6B (Fireant + POST price-updates), không POST signals",
    )
    p.add_argument(
        "--website-url",
        default=os.environ.get("WEBSITE_URL", "https://vnindex-signal-production.up.railway.app"),
    )
    p.add_argument(
        "--api-key",
        default=os.environ.get("API_KEY", ""),
    )
    p.add_argument("--preflight", action="store_true", help="Chỉ chạy kiểm tra health/API rồi thoát")
    p.add_argument(
        "--max-trading-days",
        type=int,
        default=None,
        metavar="N",
        help="Chỉ xử lý N ngày giao dịch đầu tiên trong [start, end] (vd. 10 để thử nhỏ)",
    )
    args = p.parse_args()

    website_url = args.website_url.rstrip("/")
    end = args.end or date.today()
    if args.start > end:
        print("Lỗi: --start > --end", file=sys.stderr)
        sys.exit(1)

    if args.preflight:
        if not args.api_key.strip():
            print("Thiếu --api-key hoặc API_KEY trong môi trường.", file=sys.stderr)
            sys.exit(1)
        ok = await run_preflight(website_url, args.api_key.strip())
        sys.exit(0 if ok else 1)

    token = os.environ.get("FIREANT_TOKEN", "").strip() or ra.FIREANT_TOKEN
    if not token:
        print("Thiếu FIREANT_TOKEN.", file=sys.stderr)
        sys.exit(1)

    api_key = args.api_key.strip() or os.environ.get("API_KEY", ra.API_KEY)
    if not api_key:
        print("Thiếu API_KEY (env hoặc --api-key).", file=sys.stderr)
        sys.exit(1)

    ra.FA_HEADERS["Authorization"] = f"Bearer {token}"

    if args.price_tracking_only:
        print("=" * 72)
        print(f"Chỉ bước 6B (price tracking) | as_of end = {end}")
        if args.max_trading_days is not None and args.max_trading_days > 0:
            wd = iter_trading_days(args.start, end)[: args.max_trading_days]
            run_dates_filter = set(wd)
            print(
                f"   Lọc: {len(wd)} ngày giao dịch đầu ({wd[0]} … {wd[-1]})"
                if wd
                else "   Lọc: (không có ngày trong khoảng)"
            )
        else:
            run_dates_filter = None
        print(f"Backend: {website_url}")
        print("=" * 72)
        async with httpx.AsyncClient() as client:
            top_stocks = await ra.get_all_stocks(client)
        syms = [x["sym"] for x in top_stocks]
        price_data, _ = await ra.collect_data(syms)
        await update_price_tracking_for_date(
            price_data, end, website_url, api_key, run_dates_filter=run_dates_filter
        )
        print("\n✅ Hoàn tất price tracking.")
        return

    days = iter_trading_days(args.start, end)
    if args.max_trading_days is not None and args.max_trading_days > 0:
        days = days[: args.max_trading_days]
    print("=" * 72)
    print(
        f"YTD top_cap | {args.start} → {end} | {len(days)} ngày giao dịch (local calendar)"
        + (f" [max {args.max_trading_days}]" if args.max_trading_days else "")
    )
    print(f"Backend: {website_url}")
    print("=" * 72)

    async with httpx.AsyncClient() as client:
        top_stocks = await ra.get_all_stocks(client)
    syms = [x["sym"] for x in top_stocks]
    mc_map = {x["sym"]: x["marketCap"] for x in top_stocks}

    price_data, fin_data = await ra.collect_data(syms)

    posted = 0
    for i, as_of in enumerate(days):
        sigs = build_signals_for_day(as_of, top_stocks, mc_map, price_data, fin_data)
        n = len(sigs)
        if n == 0:
            print(f"⚠️  {as_of}: không có signal (bỏ qua)")
            continue
        print(f"[{i + 1}/{len(days)}] {as_of}: {n} signals")

        if args.dry_run:
            continue

        do_refresh = bool(args.refresh_each_day)
        ok = await post_signals_batch(
            as_of,
            sigs,
            top_n=n,
            hold_days=args.hold_days,
            website_url=website_url,
            api_key=api_key,
            do_refresh=do_refresh,
        )
        if ok:
            posted += 1

    if not args.dry_run and posted > 0 and not args.refresh_each_day:
        print("\n📤 refresh-views (một lần)...")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{website_url}/api/v1/admin/refresh-views", json={}, headers=headers)
            if r.status_code == 200:
                print("✅ refresh-views OK")
            else:
                print(f"⚠️  refresh-views: {r.status_code} {r.text[:200]}")

    if not args.dry_run and not args.skip_price_tracking and posted > 0:
        rd_filter = set(days) if args.max_trading_days else None
        await update_price_tracking_for_date(
            price_data, end, website_url, api_key, run_dates_filter=rd_filter
        )

    print("\n✅ Hoàn tất YTD.")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
