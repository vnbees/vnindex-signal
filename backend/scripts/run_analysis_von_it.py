#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Danh mục vốn ít: vốn hoá cao + thanh khoản + giá ≤ max_price (mặc định 30k/cp).
Scoring dùng backtest_scoring (cùng rule với run_backtest). POST portfolio_kind=low_cap.

Không sửa run_analysis.py. Cần FIREANT_TOKEN (env), WEBSITE_URL + API_KEY (env hoặc mặc định như run_analysis).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import httpx

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

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
from run_backtest import trailing_avg_volume

HOLD_DAYS_DEFAULT = 20


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)


async def fetch_fundamental_mc(
    client: httpx.AsyncClient, headers: dict, sym: str
) -> Optional[Dict]:
    try:
        r = await client.get(
            f"{ra.FIREANT_BASE}/symbols/{sym}/fundamental",
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            d = r.json()
            mc = d.get("marketCap", 0)
            if mc and mc > 0:
                return {"sym": sym, "marketCap": float(mc)}
    except Exception:
        pass
    return None


async def universe_by_market_cap(
    min_mc_bil: float, headers: dict
) -> Tuple[List[str], Dict[str, float]]:
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    ) as client:
        results = await asyncio.gather(
            *[fetch_fundamental_mc(client, headers, s) for s in ra.CANDIDATES]
        )
    min_vnd = float(min_mc_bil) * 1e9
    valid = [r for r in results if r and r["marketCap"] >= min_vnd]
    valid.sort(key=lambda x: x["marketCap"], reverse=True)
    syms = [x["sym"] for x in valid]
    mc_map = {x["sym"]: x["marketCap"] for x in valid}
    return syms, mc_map


def filter_liquidity_price(
    price_data: Dict[str, List],
    syms: List[str],
    as_of: date,
    max_price: float,
    min_avg_volume: float,
    liquidity_window: int,
) -> List[str]:
    out: List[str] = []
    for sym in syms:
        qdesc = price_data.get(sym) or []
        qasc = sorted(qdesc, key=lambda r: (r.get("date") or "")[:10])
        bar = bar_on_date(qasc, as_of)
        if not bar:
            continue
        pc = bar.get("priceClose") or 0
        if pc <= 0 or float(pc) > float(max_price):
            continue
        pdesc = prices_as_of(qasc, as_of)
        if len(pdesc) < 60:
            continue
        avg_vol = trailing_avg_volume(qasc, as_of, liquidity_window)
        if avg_vol is None or avg_vol < float(min_avg_volume):
            continue
        out.append(sym)
    return out


async def post_low_cap_signals(
    as_of: date,
    signals: List[Dict],
    top_n: int,
    hold_days: int,
    website_url: str,
    api_key: str,
) -> bool:
    print(f"\n📤 POST {len(signals)} signals (low_cap) lên {website_url}...")
    payload = {
        "run_date": as_of.isoformat(),
        "top_n": top_n,
        "hold_days": hold_days,
        "portfolio_kind": "low_cap",
        "signals": signals,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{website_url}/api/v1/signals", json=payload, headers=headers)
        if r.status_code in (200, 201):
            print(f"✅ POST signals OK ({r.status_code})")
            r2 = await client.post(
                f"{website_url}/api/v1/admin/refresh-views", json={}, headers=headers
            )
            if r2.status_code == 200:
                print("✅ Refresh views OK")
            else:
                print(f"⚠️  Refresh views: {r2.status_code} — {r2.text[:200]}")
            return True
        print(f"❌ POST FAILED: {r.status_code} {r.text[:500]}")
        return False


def _parse_item_run_date(item: dict) -> Optional[date]:
    rd = item.get("run_date")
    if rd is None:
        return None
    if isinstance(rd, date):
        return rd
    if isinstance(rd, str):
        try:
            return date.fromisoformat(rd[:10])
        except ValueError:
            return None
    return None


async def update_price_tracking_for_date(
    price_data: Dict[str, List],
    as_of: date,
    website_url: str,
    api_key: str,
    run_dates_filter: Optional[Set[date]] = None,
) -> None:
    """run_dates_filter: nếu có, chỉ xử lý pending có run_date thuộc tập này (vd. 10 ngày giao dịch đầu năm)."""
    print("\n💹 Update price tracking (pending)...")
    if run_dates_filter is not None:
        print(f"   Lọc run_date: {len(run_dates_filter)} ngày tín hiệu")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # Large batches (nhiều symbol × nhiều ngày) có thể vượt 60s trên PROD
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
        r = await client.get(
            f"{website_url}/api/v1/price-updates/pending?limit=10000", headers=headers
        )
        if r.status_code != 200:
            print(f"⚠️  pending: {r.status_code}")
            return
        pending = r.json()
        if not pending:
            print("✅ Không có price tracking cần update")
            return
        raw_n = len(pending)
        if run_dates_filter is not None:
            pending = [
                p
                for p in pending
                if (rd := _parse_item_run_date(p)) is not None and rd in run_dates_filter
            ]
            print(f"   {raw_n} pending → {len(pending)} sau lọc run_date")
        else:
            print(f"   {len(pending)} pending")

        if not pending:
            print("✅ Không có price tracking cần update (sau lọc)")
            return

        missing = {item.get("symbol") for item in pending if item.get("symbol")}
        missing = {s for s in missing if s and s not in price_data}
        if missing:
            print(f"   Fetch thêm: {', '.join(sorted(missing))}")
            results = await asyncio.gather(*[ra.fetch_price_data(client, s) for s in missing])
            for sym, data in zip(missing, results):
                if data:
                    price_data[sym] = data

        price_lookup: Dict[str, Dict[str, Dict]] = {}
        for sym, records in price_data.items():
            price_lookup[sym] = {}
            for rec in records:
                d = (rec.get("date") or "")[:10]
                if d:
                    price_lookup[sym][d] = {
                        "price_open": rec.get("priceOpen") or 0,
                        "price_close": rec.get("priceClose") or 0,
                    }

        by_date: Dict[str, List[Dict]] = {}
        for item in pending:
            sym = item.get("symbol")
            for td in item.get("track_dates_needed") or []:
                td_str = td[:10]
                if td_str > as_of.isoformat():
                    continue
                by_date.setdefault(td_str, []).append(
                    {"signal_id": item.get("signal_id"), "symbol": sym}
                )

        sorted_dates = sorted(by_date.keys())
        total_updated = 0
        for i, track_date in enumerate(sorted_dates):
            is_last = i == len(sorted_dates) - 1
            items = by_date[track_date]
            prices = []
            for it in items:
                sym = it["symbol"]
                rec = price_lookup.get(sym, {}).get(track_date)
                if rec and rec["price_close"] > 0:
                    prices.append(
                        {
                            "symbol": sym,
                            "price_open": rec["price_open"],
                            "price_close": rec["price_close"],
                        }
                    )
            if not prices:
                continue
            body = {"track_date": track_date, "prices": prices, "skip_refresh": not is_last}
            r2 = await client.post(
                f"{website_url}/api/v1/price-updates", json=body, headers=headers
            )
            if r2.status_code in (200, 201):
                total_updated += len(prices)
            else:
                print(f"   ⚠️  {track_date}: {r2.status_code}")

        print(f"✅ Đã update price tracking: {total_updated} records / {len(sorted_dates)} ngày")


async def async_main() -> None:
    p = argparse.ArgumentParser(description="Phân tích danh mục vốn ít → POST low_cap.")
    p.add_argument("--date", type=_parse_iso_date, default=None, help="Ngày tín hiệu (ISO), mặc định hôm nay")
    p.add_argument("--hold-days", type=int, default=HOLD_DAYS_DEFAULT)
    p.add_argument("--min-market-cap-bil", type=float, default=8000.0)
    p.add_argument("--min-avg-volume", type=float, default=300_000.0)
    p.add_argument("--liquidity-window", type=int, default=60)
    p.add_argument("--max-price", type=float, default=30.0, help="Giá đóng tối đa (nghìn VND)")
    p.add_argument(
        "--website-url",
        default=os.environ.get("WEBSITE_URL", "https://vnindex-signal-production.up.railway.app"),
    )
    p.add_argument(
        "--api-key",
        default=os.environ.get(
            "API_KEY", "sk-vnindex-c87e097efb4dac431dabb8a52e3e5af57e73a74a"
        ),
    )
    args = p.parse_args()

    token = os.environ.get("FIREANT_TOKEN", "").strip()
    if not token:
        print("Thiếu FIREANT_TOKEN trong môi trường.", file=sys.stderr)
        sys.exit(1)

    as_of = args.date or date.today()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    ra.FA_HEADERS["Authorization"] = f"Bearer {token}"

    print("=" * 72)
    print(f"Danh mục vốn ít (low_cap) | ngày {as_of.isoformat()}")
    print(
        f"MC ≥ {args.min_market_cap_bil} tỷ | avgVolume ≥ {args.min_avg_volume:,.0f} / {args.liquidity_window} phiên | giá ≤ {args.max_price}k"
    )
    print("=" * 72)

    syms_mc, mc_map = await universe_by_market_cap(args.min_market_cap_bil, headers)
    if not syms_mc:
        print("Không có mã nào đạt ngưỡng vốn hoá.", file=sys.stderr)
        sys.exit(1)
    print(f"Sau lọc vốn hoá: {len(syms_mc)} mã")

    price_data, fin_data = await ra.collect_data(syms_mc)

    syms = filter_liquidity_price(
        price_data,
        syms_mc,
        as_of,
        args.max_price,
        args.min_avg_volume,
        args.liquidity_window,
    )
    if not syms:
        print("Không có mã nào đạt thanh khoản + giá.", file=sys.stderr)
        sys.exit(1)
    print(f"Sau lọc thanh khoản + giá: {len(syms)} mã")

    score_ss, detail_ss = calc_seasonal_score(as_of)
    signals_out: List[Dict] = []

    for sym in syms:
        qdesc = price_data.get(sym) or []
        qasc = sorted(qdesc, key=lambda r: (r.get("date") or "")[:10])
        pdesc = prices_as_of(qasc, as_of)
        fin = fin_data.get(sym)
        score_tc, detail_tc = calc_financial_score(sym, fin, as_of)
        score_kt, detail_kt = calc_technical_score(sym, pdesc)
        score_dt, detail_dt = calc_cashflow_score(sym, pdesc)
        total = score_tc + score_ss + score_kt + score_dt
        rec = get_recommendation(total)
        bar = bar_on_date(qasc, as_of)
        price_close = (bar.get("priceClose") or 0) if bar else 0
        avg_vol = trailing_avg_volume(qasc, as_of, args.liquidity_window)
        mc_bil = mc_map.get(sym, 0) / 1e9
        detail_kt = dict(detail_kt) if detail_kt else {}
        if avg_vol is not None:
            detail_kt["avg_volume_liq"] = round(avg_vol, 2)

        signals_out.append(
            {
                "symbol": sym,
                "score_financial": score_tc,
                "score_seasonal": score_ss,
                "score_technical": score_kt,
                "score_cashflow": score_dt,
                "score_total": total,
                "recommendation": rec,
                "price_close_signal_date": float(price_close),
                "market_cap_bil": round(mc_bil, 2),
                "detail_financial": detail_tc,
                "detail_technical": detail_kt,
                "detail_cashflow": detail_dt,
                "detail_seasonal": detail_ss,
            }
        )

    signals_out.sort(key=lambda x: x["score_total"], reverse=True)
    n = len(signals_out)
    print(f"\n✅ Đã tính {n} tín hiệu (sort theo tổng điểm)")

    await post_low_cap_signals(
        as_of,
        signals_out,
        top_n=n,
        hold_days=args.hold_days,
        website_url=args.website_url.rstrip("/"),
        api_key=args.api_key,
    )
    await update_price_tracking_for_date(
        price_data, as_of, args.website_url.rstrip("/"), args.api_key
    )
    print("\n✅ Hoàn tất danh mục vốn ít.")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
