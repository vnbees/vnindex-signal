#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug bước 6B: đo thời gian từng bước, chỉ chạy 1 run_date đầu tiên.
Chạy: python scripts/debug_price_tracking.py --run-date 2026-01-05
"""
import asyncio
import os
import sys
import time
from datetime import date
from pathlib import Path

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

import run_analysis as ra

WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://vnindex-signal-production.up.railway.app").rstrip("/")
API_KEY = os.environ.get("API_KEY", ra.API_KEY)


def ts():
    return time.strftime("%H:%M:%S")


async def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--run-date", type=lambda s: date.fromisoformat(s), default=None,
                   help="run_date để lọc pending (vd. 2026-01-05). Bỏ qua = lấy tất cả để đếm")
    p.add_argument("--post", action="store_true", help="Thật sự POST price-updates (mặc định dry-run)")
    args = p.parse_args()

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    # --- Step 1: GET pending ---
    print(f"[{ts()}] GET /price-updates/pending?limit=10000 ...")
    t0 = time.time()
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(f"{WEBSITE_URL}/api/v1/price-updates/pending?limit=10000", headers=headers)
    print(f"[{ts()}] → status={r.status_code}, elapsed={time.time()-t0:.1f}s, bytes={len(r.content)}")

    if r.status_code != 200:
        print(f"FAILED: {r.text[:500]}")
        return

    all_pending = r.json()
    print(f"[{ts()}] Tổng pending: {len(all_pending)} records")

    # Thống kê run_date
    from collections import Counter
    run_date_counts = Counter(
        (item.get("run_date") or "")[:10] for item in all_pending
    )
    print(f"\n--- run_date breakdown (top 15) ---")
    for rd, cnt in sorted(run_date_counts.items())[:15]:
        print(f"  {rd}: {cnt} signals")
    print(f"  ... tổng {len(run_date_counts)} run_dates\n")

    # Lọc theo run_date nếu có
    if args.run_date:
        target = args.run_date.isoformat()
        pending = [p for p in all_pending if (p.get("run_date") or "")[:10] == target]
        print(f"[{ts()}] Sau lọc run_date={target}: {len(pending)} signals")
    else:
        pending = all_pending
        print(f"[{ts()}] Không lọc, dùng tất cả {len(pending)} signals")

    if not pending:
        print("Không có pending để xử lý.")
        return

    # Tổng số track_dates_needed
    total_track_items = sum(len(p.get("track_dates_needed") or []) for p in pending)
    unique_track_dates = sorted(set(
        td[:10]
        for p in pending
        for td in (p.get("track_dates_needed") or [])
    ))
    print(f"[{ts()}] track_dates_needed: {total_track_items} tổng items, {len(unique_track_dates)} ngày duy nhất")
    print(f"   ngày: {unique_track_dates[:10]}{'...' if len(unique_track_dates) > 10 else ''}")

    # --- Step 2: Fetch price data ---
    symbols = list({p.get("symbol") for p in pending if p.get("symbol")})
    print(f"\n[{ts()}] Fetch price_data cho {len(symbols)} symbols (song song)...")
    t1 = time.time()
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    ) as client:
        results = await asyncio.gather(*[ra.fetch_price_data(client, s) for s in symbols])
    price_data = {sym: data for sym, data in zip(symbols, results)}
    ok_count = sum(1 for v in price_data.values() if v)
    print(f"[{ts()}] Fetch xong: {ok_count}/{len(symbols)} symbols có data, elapsed={time.time()-t1:.1f}s")

    # --- Step 3: Build price_lookup ---
    price_lookup = {}
    for sym, records in price_data.items():
        price_lookup[sym] = {}
        for rec in records:
            d = (rec.get("date") or "")[:10]
            if d:
                price_lookup[sym][d] = {
                    "price_open": rec.get("priceOpen") or 0,
                    "price_close": rec.get("priceClose") or 0,
                }

    # --- Step 4: Group by track_date ---
    from collections import defaultdict
    by_date = defaultdict(list)
    today_str = date.today().isoformat()
    for item in pending:
        sym = item.get("symbol")
        for td in item.get("track_dates_needed") or []:
            td_str = td[:10]
            if td_str > today_str:
                continue
            by_date[td_str].append({"signal_id": item.get("signal_id"), "symbol": sym})

    sorted_dates = sorted(by_date.keys())
    print(f"\n[{ts()}] Sẽ POST {len(sorted_dates)} track_dates:")
    for td in sorted_dates:
        items_on_day = by_date[td]
        prices_ok = sum(
            1 for it in items_on_day
            if (price_lookup.get(it["symbol"]) or {}).get(td, {}).get("price_close", 0) > 0
        )
        print(f"  {td}: {len(items_on_day)} signals, {prices_ok} có giá")

    # --- Step 5: POST (dry-run hoặc thật) ---
    if not args.post:
        print(f"\n[{ts()}] DRY-RUN — không POST. Thêm --post để POST thật.")
        return

    print(f"\n[{ts()}] Bắt đầu POST {len(sorted_dates)} track_dates...")
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
        for i, track_date in enumerate(sorted_dates):
            is_last = (i == len(sorted_dates) - 1)
            items = by_date[track_date]
            prices = []
            for it in items:
                sym = it["symbol"]
                rec = (price_lookup.get(sym) or {}).get(track_date)
                if rec and rec["price_close"] > 0:
                    prices.append({
                        "symbol": sym,
                        "price_open": rec["price_open"],
                        "price_close": rec["price_close"],
                    })
            if not prices:
                print(f"  [{i+1}/{len(sorted_dates)}] {track_date}: bỏ qua (không có giá)")
                continue

            t_post = time.time()
            body = {"track_date": track_date, "prices": prices, "skip_refresh": not is_last}
            r2 = await client.post(f"{WEBSITE_URL}/api/v1/price-updates", json=body, headers=headers)
            elapsed = time.time() - t_post
            print(f"  [{i+1}/{len(sorted_dates)}] {track_date}: {len(prices)} prices → {r2.status_code} ({elapsed:.1f}s)")
            if r2.status_code not in (200, 201):
                print(f"    BODY: {r2.text[:300]}")

    print(f"\n[{ts()}] Done.")


if __name__ == "__main__":
    asyncio.run(main())
