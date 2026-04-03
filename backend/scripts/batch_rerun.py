#!/usr/bin/env python3
"""
Batch re-run: chạy lại tất cả ngày tín hiệu bằng phương pháp 3-day mean-reversion mới.
Fetch dữ liệu Fireant 1 lần → replay cho từng ngày → POST lên PROD.
"""

import asyncio
import httpx
import statistics
import math
import os
import sys
import io
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

# ─── CONFIG ──────────────────────────────────────────────────────────────────
HOLD_DAYS = 3

_DEFAULT_FIREANT = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IkdYdExONzViZlZQakdvNERWdjV4"
    "QkRITHpnSSIsImtpZCI6IkdYdExONzViZlZQakdvNERWdjV4QkRITHpnSSJ9.eyJpc3MiOiJo"
    "dHRwczovL2FjY291bnRzLmZpcmVhbnQudm4iLCJhdWQiOiJodHRwczovL2FjY291bnRzLmZp"
    "cmVhbnQudm4vcmVzb3VyY2VzIiwiZXhwIjoxODg5NjIyNTMwLCJuYmYiOjE1ODk2MjI1MzAs"
    "ImNsaWVudF9pZCI6ImZpcmVhbnQudHJhZGVzdGF0aW9uIiwic2NvcGUiOlsiYWNhZGVteS1y"
    "ZWFkIiwiYWNhZGVteS13cml0ZSIsImFjY291bnRzLXJlYWQiLCJhY2NvdW50cy13cml0ZSIs"
    "ImJsb2ctcmVhZCIsImNvbXBhbmllcy1yZWFkIiwiZmluYW5jZS1yZWFkIiwiaW5kaXZpZHVh"
    "bHMtcmVhZCIsImludmVzdG9wZWRpYS1yZWFkIiwib3JkZXJzLXJlYWQiLCJvcmRlcnMtd3Jp"
    "dGUiLCJwb3N0cy1yZWFkIiwicG9zdHMtd3JpdGUiLCJzZWFyY2giLCJzeW1ib2xzLXJlYWQi"
    "LCJ1c2VyLWRhdGEtcmVhZCIsInVzZXItZGF0YS13cml0ZSIsInVzZXJzLXJlYWQiXSwianRp"
    "IjoiMjYxYTZhYWQ2MTQ5Njk1ZmJiYzcwODM5MjM0Njc1NWQifQ.dA5-HVzWv-BRfEiAd24u"
    "NBiBxASO-PAyWeWESovZm_hj4aXMAZA1-bWNZeXt88dqogo18AwpDQ-h6gefLPdZSFrG5umC1"
    "dVWaeYvUnGm62g4XS29fj6p01dhKNNqrsu5KrhnhdnKYVv9VdmbmqDfWR8wDgglk5cJFqalzq"
    "6dJWJInFQEPmUs9BW_Zs8tQDn-i5r4tYq2U8vCdqptXoM7YgPllXaPVDeccC9QNu2Xlp9WUvo"
    "ROzoQXg25lFub1IYkTrM66gJ6t9fJRZToewCt495WNEOQFa_rwLCZ1QwzvL0iYkONHS_jZ0BO"
    "hBCdW9dWSawD6iF1SIQaFROvMDH1rg"
)
FIREANT_TOKEN = os.environ.get("FIREANT_TOKEN", _DEFAULT_FIREANT).strip() or _DEFAULT_FIREANT
WEBSITE_URL = (os.environ.get("WEBSITE_URL") or "https://vnindex-signal-production.up.railway.app").rstrip("/")
API_KEY = os.environ.get("API_KEY") or "sk-vnindex-c87e097efb4dac431dabb8a52e3e5af57e73a74a"

FIREANT_BASE = "https://restv2.fireant.vn"
FA_HEADERS = {"Authorization": f"Bearer {FIREANT_TOKEN}", "Content-Type": "application/json"}

CANDIDATES = [
    "SHB","HPG","VIX","SSI","MBB","HDB","BSR","VPB","POW","EIB",
    "SHS","TCB","ACB","DXG","CII","CTG","STB","VND","HCM","TPB",
    "FPT","MSB","CEO","VCI","VCB","DIG","NVL","PDR","PVS","GEX",
    "BID","PVD","VCG","DPM","VSC","EVF","PVT","MWG","VNM","PLX",
    "VIB","OIL","VRE","TCH","HNG","MSN","VHM","HAG","VIC","SSB",
    "KDH","KBC","DGC","DCM","MBS","OCB","NKG","HHV","IDC","HQC",
    "HSG","GAS","NLG","HDC","DGW","LPB","MSR","SCR","ORS","ABB",
    "HDG","GMD","HAH","BAF","LCG","VPI","BVB","VDS","PNJ","DDV",
    "VAB","HVN","NAB","VJC","NT2","ANV","SAB","VHC","VGI","YEG",
    "VGC","GEG","LDG","PAN","KSB","HBC","BCM","ELC","FTS","SZC",
    "DSC","BVH","CSV","TVN","AGR","REE","VEA","PLC","FCN","CTS",
    "GEE","DRH","PHR","CTD","POM","FRT","NRC","EVG","APG","SIP",
    "C4G","IDI","VGS","SAM","SGB","MCH","SMC","BSI","KLB","PPC",
    "BMI","APS","PVB",
]

RUN_DATES = [
    "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09",
    "2026-01-12", "2026-01-13", "2026-01-14", "2026-01-15",
    "2026-01-16", "2026-01-19", "2026-01-20", "2026-01-21", "2026-01-22", "2026-01-23",
    "2026-01-26", "2026-01-27", "2026-01-28", "2026-01-29", "2026-01-30",
    "2026-02-02", "2026-02-03", "2026-02-04", "2026-02-05", "2026-02-06",
    "2026-02-09", "2026-02-10", "2026-02-11", "2026-02-12", "2026-02-13",
    "2026-02-24", "2026-02-25", "2026-02-26", "2026-02-27",
    "2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06",
    "2026-03-09", "2026-03-10", "2026-03-11", "2026-03-12", "2026-03-13",
    "2026-03-16", "2026-03-17", "2026-03-18", "2026-03-19", "2026-03-20",
    "2026-03-23", "2026-03-24", "2026-03-25", "2026-03-26", "2026-03-27",
    "2026-03-30", "2026-03-31",
    "2026-04-01", "2026-04-02", "2026-04-03",
]

# ─── UTILITIES ───────────────────────────────────────────────────────────────

def wilder_rsi(closes: List[float], period: int = 14) -> float:
    prices = list(reversed(closes))
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def safe_div(a, b, default=0.0):
    try:
        return a / b if b and b != 0 else default
    except Exception:
        return default


# ─── SCORING (same as run_analysis.py) ───────────────────────────────────────

def calc_seasonal_score(target_date: date) -> Tuple[int, Dict]:
    dow = target_date.weekday()
    score = 0
    reason = "neutral"
    if dow == 0:
        score = 1
        reason = "Monday (WR=52.4%, best day)"
    elif dow == 2:
        score = -1
        reason = "Wednesday (WR=44.7%, worst day)"
    else:
        day_names = {1: "Tuesday", 3: "Thursday", 4: "Friday"}
        reason = f"{day_names.get(dow, '')} (neutral)"
    return score, {"month": target_date.month, "dayOfWeek": dow + 1, "reason": reason}


def calc_technical_score(sym: str, prices: List[Dict]) -> Tuple[int, Dict]:
    detail = {"vsMa20": None, "rsi14": None, "bbPos": None, "ma20": None, "ma60": None,
              "consecutiveDown": 0, "dayReturn": None, "volRatio": None, "matchedStrategies": []}
    if not prices or len(prices) < 20:
        return 0, detail

    closes = [p.get("priceClose") or 0 for p in prices]
    closes = [c for c in closes if c > 0]
    if len(closes) < 20:
        return 0, detail

    close = closes[0]
    ma20 = statistics.mean(closes[:20])
    ma60 = statistics.mean(closes[:60]) if len(closes) >= 60 else statistics.mean(closes)
    std20 = statistics.stdev(closes[:20]) if len(closes[:20]) > 1 else 0

    vs_ma20 = (close / ma20 - 1) * 100 if ma20 > 0 else 0
    bb_upper = ma20 + 2 * std20
    bb_lower = ma20 - 2 * std20
    bb_pos = safe_div(close - bb_lower, bb_upper - bb_lower, 0.5) if bb_upper != bb_lower else 0.5
    rsi14 = wilder_rsi(closes, 14)

    prev_close = closes[1] if len(closes) > 1 else close
    day_return = (close / prev_close - 1) * 100 if prev_close > 0 else 0

    vols = [p.get("dealVolume") or p.get("totalVolume") or 0 for p in prices[:21]]
    vol_now = vols[0] if vols else 0
    vol_ma20 = statistics.mean(vols[:20]) if len(vols) >= 20 else (statistics.mean(vols) if vols else 1)
    vol_ratio = safe_div(vol_now, vol_ma20, 1.0)

    consecutive_down = 0
    for j in range(len(closes) - 1):
        if j + 1 < len(closes) and closes[j] < closes[j + 1]:
            consecutive_down += 1
        else:
            break

    fg_net_5d = sum(
        (p.get("buyForeignQuantity") or 0) - (p.get("sellForeignQuantity") or 0)
        for p in prices[:5]
    )

    detail.update({
        "vsMa20": round(vs_ma20, 2), "rsi14": rsi14, "bbPos": round(bb_pos, 3),
        "ma20": round(ma20), "ma60": round(ma60),
        "consecutiveDown": consecutive_down, "dayReturn": round(day_return, 2),
        "volRatio": round(vol_ratio, 2), "matchedStrategies": [],
    })

    matched = []
    score = 0

    if rsi14 < 40 and vol_ratio > 2:
        score = -2
        matched.append("RSI<40 + Vol>2x (PF=0.77)")
    elif bb_pos > 0.9:
        score = -1
        matched.append("BB>0.9 near upper (PF=1.07)")
    elif consecutive_down >= 4 and rsi14 < 35:
        score = 3
        matched.append("4 down + RSI<35 (PF=1.94, WR=59.5%)")
    elif consecutive_down >= 3 and rsi14 < 40:
        score = 2
        matched.append("3 down + RSI<40 (PF=1.69, WR=56.7%)")
    elif consecutive_down >= 3 and fg_net_5d > 0:
        score = 2
        matched.append("3 down + NN buy (PF=1.63, WR=54.5%)")
    elif vs_ma20 < -5 and fg_net_5d > 0:
        score = 2
        matched.append("Below MA20 >5% + NN buy (PF=1.49, WR=56.4%)")
    elif day_return < -3 and fg_net_5d > 0:
        score = 1
        matched.append("Drop >3% + NN buy (PF=1.41, WR=56.0%)")
    elif rsi14 < 30:
        score = 1
        matched.append("RSI<30 oversold (PF=1.36, WR=54.0%)")
    elif consecutive_down >= 5:
        score = 1
        matched.append("5+ down consecutive (PF=1.25, WR=54.4%)")

    detail["matchedStrategies"] = matched
    return score, detail


def calc_cashflow_score(sym: str, prices: List[Dict]) -> Tuple[int, Dict]:
    detail = {"fgNet5d": None, "propNet5d": None, "fgNet5dZ": 0.0}
    if not prices or len(prices) < 5:
        return 0, detail

    fg_net_5d = sum(
        (p.get("buyForeignQuantity") or 0) - (p.get("sellForeignQuantity") or 0)
        for p in prices[:5]
    )
    prop_net_5d = sum(p.get("propTradingNetValue") or 0 for p in prices[:5])

    if len(prices) >= 60:
        fg_vals = [
            (p.get("buyForeignQuantity") or 0) - (p.get("sellForeignQuantity") or 0)
            for p in prices[:60]
        ]
        fg_mean = statistics.mean(fg_vals)
        fg_std = statistics.stdev(fg_vals) if len(fg_vals) > 1 else 1
        fg_z = (fg_net_5d - fg_mean * 5) / (fg_std * math.sqrt(5)) if fg_std != 0 else 0
    else:
        fg_z = 0.0

    detail.update({"fgNet5d": float(fg_net_5d), "propNet5d": float(prop_net_5d), "fgNet5dZ": round(fg_z, 2)})

    if fg_net_5d > 0 and prop_net_5d > 0:
        return 1, detail
    elif fg_net_5d < 0 and prop_net_5d < 0:
        return -1, detail
    return 0, detail


def get_recommendation(total: int) -> str:
    if total >= 4:
        return "BUY_STRONG"
    elif total >= 2:
        return "BUY"
    elif total >= 0:
        return "HOLD"
    elif total >= -1:
        return "AVOID"
    else:
        return "SELL"


# ─── DATA FETCHING (one-time) ───────────────────────────────────────────────

async def fetch_price_data(client: httpx.AsyncClient, sym: str) -> List[Dict]:
    try:
        r = await client.get(
            f"{FIREANT_BASE}/symbols/{sym}/historical-quotes",
            params={"startDate": "2021-01-01", "endDate": "2030-12-31", "limit": 1000},
            headers=FA_HEADERS, timeout=30,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


async def fetch_fundamental(client: httpx.AsyncClient, sym: str) -> Optional[Dict]:
    try:
        r = await client.get(f"{FIREANT_BASE}/symbols/{sym}/fundamental", headers=FA_HEADERS, timeout=15)
        if r.status_code == 200:
            d = r.json()
            return {"sym": sym, "marketCap": d.get("marketCap") or 0}
    except Exception:
        pass
    return {"sym": sym, "marketCap": 0}


async def fetch_all_data() -> Tuple[Dict[str, List[Dict]], Dict[str, float]]:
    """Fetch price + market cap for all candidates once."""
    print(f"  Fetching data for {len(CANDIDATES)} symbols...")
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)) as client:
        price_results = await asyncio.gather(*[fetch_price_data(client, s) for s in CANDIDATES])
        mc_results = await asyncio.gather(*[fetch_fundamental(client, s) for s in CANDIDATES])

    price_data = {}
    for sym, data in zip(CANDIDATES, price_results):
        price_data[sym] = data

    mc_map = {}
    for r in mc_results:
        if r:
            mc_map[r["sym"]] = r["marketCap"]

    ok_price = sum(1 for v in price_data.values() if v)
    print(f"  Price: {ok_price}/{len(CANDIDATES)} | MarketCap: {len(mc_map)}/{len(CANDIDATES)}")

    missing_price = [s for s in CANDIDATES if not price_data.get(s)]
    if missing_price:
        print(f"  Retrying {len(missing_price)} missing: {', '.join(missing_price[:10])}...")
        async with httpx.AsyncClient() as client2:
            retry = await asyncio.gather(*[fetch_price_data(client2, s) for s in missing_price])
        for sym, data in zip(missing_price, retry):
            if data:
                price_data[sym] = data
        ok2 = sum(1 for v in price_data.values() if v)
        print(f"  After retry: {ok2}/{len(CANDIDATES)}")

    return price_data, mc_map


def slice_prices_as_of(all_prices: List[Dict], target_date: date) -> List[Dict]:
    """Return price data slice where prices[0] is the target_date (or closest before)."""
    target_str = target_date.isoformat()
    for i, p in enumerate(all_prices):
        d = (p.get("date") or "")[:10]
        if d <= target_str:
            return all_prices[i:]
    return []


# ─── ANALYZE ONE DATE ────────────────────────────────────────────────────────

def analyze_date(target_date: date, price_data: Dict[str, List[Dict]], mc_map: Dict[str, float]) -> List[Dict]:
    score_ss, detail_ss = calc_seasonal_score(target_date)
    signals = []

    for sym in CANDIDATES:
        all_prices = price_data.get(sym, [])
        prices = slice_prices_as_of(all_prices, target_date)

        score_kt, detail_kt = calc_technical_score(sym, prices)
        score_dt, detail_dt = calc_cashflow_score(sym, prices)
        score_tc = 0

        total = score_tc + score_ss + score_kt + score_dt
        rec = get_recommendation(total)
        price_close = (prices[0].get("priceClose") or 0) if prices else 0
        mc_bil = mc_map.get(sym, 0) / 1e9

        signals.append({
            "symbol": sym,
            "score_financial": score_tc,
            "score_seasonal": score_ss,
            "score_technical": score_kt,
            "score_cashflow": score_dt,
            "score_total": total,
            "recommendation": rec,
            "price_close_signal_date": float(price_close),
            "market_cap_bil": round(mc_bil, 2),
            "detail_financial": {"quarter": None, "lnstYoY": None, "salesYoY": None,
                                 "marginDelta": None, "earningsAccel": None},
            "detail_technical": detail_kt,
            "detail_cashflow": detail_dt,
            "detail_seasonal": detail_ss,
        })

    signals.sort(key=lambda x: x["score_total"], reverse=True)
    return signals


# ─── POST SIGNALS ────────────────────────────────────────────────────────────

async def post_signals(target_date: date, signals: List[Dict], is_last: bool) -> bool:
    payload = {
        "run_date": target_date.isoformat(),
        "top_n": len(signals),
        "hold_days": HOLD_DAYS,
        "signals": signals,
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{WEBSITE_URL}/api/v1/signals", json=payload, headers=headers)
        if r.status_code in (200, 201):
            resp = r.json()
            ins = resp.get("inserted", 0)
            upd = resp.get("updated", 0)
            print(f"    POST OK: inserted={ins} updated={upd}")
            if is_last:
                r2 = await client.post(f"{WEBSITE_URL}/api/v1/admin/refresh-views", json={}, headers=headers)
                print(f"    Refresh views: {r2.status_code}")
            return True
        else:
            print(f"    POST FAILED: {r.status_code} - {r.text[:200]}")
            return False


# ─── UPDATE PRICE TRACKING ──────────────────────────────────────────────────

async def update_price_tracking(price_data: Dict[str, List[Dict]]) -> None:
    print(f"\n{'='*60}")
    print(f"PHASE 3: Update price tracking (PnL)...")
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{WEBSITE_URL}/api/v1/price-updates/pending?limit=50000", headers=headers)
        if r.status_code != 200:
            print(f"  Cannot get pending: {r.status_code}")
            return

        pending = r.json()
        if not pending:
            print("  No pending records")
            return

        print(f"  Found {len(pending)} pending records")

        missing = set()
        for item in pending:
            sym = item.get("symbol")
            if sym and sym not in price_data:
                missing.add(sym)
        if missing:
            print(f"  Fetching {len(missing)} extra symbols...")
            async with httpx.AsyncClient() as client2:
                results = await asyncio.gather(*[fetch_price_data(client2, s) for s in missing])
            for sym, data in zip(missing, results):
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

        today_str = date.today().isoformat()
        by_date: Dict[str, List[Dict]] = {}
        for item in pending:
            sym = item.get("symbol")
            for td in item.get("track_dates_needed") or []:
                td_str = td[:10]
                if td_str > today_str:
                    continue
                if td_str not in by_date:
                    by_date[td_str] = []
                by_date[td_str].append({"signal_id": item.get("signal_id"), "symbol": sym})

        sorted_dates = sorted(by_date.keys())
        total_updated = 0
        for i, track_date in enumerate(sorted_dates):
            is_last = (i == len(sorted_dates) - 1)
            items = by_date[track_date]
            prices_list = []
            for it in items:
                sym = it["symbol"]
                rec = price_lookup.get(sym, {}).get(track_date)
                if rec and rec["price_close"] > 0:
                    prices_list.append({"symbol": sym, "price_open": rec["price_open"],
                                        "price_close": rec["price_close"]})
            if not prices_list:
                continue
            body = {"track_date": track_date, "prices": prices_list, "skip_refresh": not is_last}
            r2 = await client.post(f"{WEBSITE_URL}/api/v1/price-updates", json=body, headers=headers)
            if r2.status_code in (200, 201):
                total_updated += len(prices_list)
            else:
                print(f"    {track_date}: {r2.status_code} - {r2.text[:100]}")

        print(f"  Updated {total_updated} price records across {len(sorted_dates)} trading days")


# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 60)
    print(f"BATCH RE-RUN: {len(RUN_DATES)} dates x {len(CANDIDATES)} symbols")
    print(f"Method: 3-day mean-reversion | Hold: {HOLD_DAYS} days")
    print(f"Target: {WEBSITE_URL}")
    print("=" * 60)

    # Phase 1: Fetch all data once
    print(f"\nPHASE 1: Fetching Fireant data (one-time)...")
    price_data, mc_map = await fetch_all_data()

    # Phase 2: Analyze & POST for each date
    print(f"\n{'='*60}")
    print(f"PHASE 2: Analyze & POST {len(RUN_DATES)} dates...")
    success = 0
    fail = 0

    for i, date_str in enumerate(RUN_DATES):
        target = date.fromisoformat(date_str)
        is_last = (i == len(RUN_DATES) - 1)
        day_names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}
        dow = day_names.get(target.weekday(), "?")

        print(f"\n  [{i+1}/{len(RUN_DATES)}] {date_str} ({dow})")
        signals = analyze_date(target, price_data, mc_map)

        buy_count = sum(1 for s in signals if s["recommendation"] in ("BUY", "BUY_STRONG"))
        sell_count = sum(1 for s in signals if s["recommendation"] in ("AVOID", "SELL"))
        print(f"    {len(signals)} signals: {buy_count} BUY+ / {sell_count} AVOID/SELL")

        ok = await post_signals(target, signals, is_last)
        if ok:
            success += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    print(f"PHASE 2 DONE: {success} OK / {fail} FAILED")

    # Phase 3: Update price tracking
    await update_price_tracking(price_data)

    print(f"\n{'='*60}")
    print(f"ALL DONE! {success}/{len(RUN_DATES)} dates re-run successfully.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
