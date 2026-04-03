#!/usr/bin/env python3
"""
Phân tích chiến lược mua cổ phiếu hôm nay - lãi sau 3 ngày giao dịch
Lấy dữ liệu 100 cổ phiếu vốn hóa lớn nhất từ Fireant API
Backtest trên 2 năm dữ liệu (2024-2026)
"""

import asyncio
import httpx
import statistics
import math
import json
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# ─── CONFIG ──────────────────────────────────────────────────────────────────
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

HOLD_DAYS = 3

# ─── UTILITIES ───────────────────────────────────────────────────────────────

def wilder_rsi(closes: List[float], period: int = 14) -> float:
    prices = list(reversed(closes))
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
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
    except:
        return default

# ─── STEP 1: FETCH FUNDAMENTAL & SELECT TOP 100 ─────────────────────────────

async def fetch_top100_by_market_cap(client: httpx.AsyncClient) -> List[Dict]:
    print(f"\n{'='*80}")
    print(f"BUOC 1: Lay von hoa {len(CANDIDATES)} ma -> chon Top 100")
    print(f"{'='*80}")

    async def fetch_fundamental(sym: str) -> Optional[Dict]:
        try:
            r = await client.get(
                f"{FIREANT_BASE}/symbols/{sym}/fundamental",
                headers=FA_HEADERS, timeout=15
            )
            if r.status_code == 200:
                d = r.json()
                return {"sym": sym, "marketCap": d.get("marketCap") or 0}
        except:
            pass
        return {"sym": sym, "marketCap": 0}

    results = await asyncio.gather(*[fetch_fundamental(s) for s in CANDIDATES])
    valid = [r for r in results if r and r["marketCap"] > 0]
    valid.sort(key=lambda x: x["marketCap"], reverse=True)

    top100 = valid[:100]
    print(f"  Co {len(valid)} ma co von hoa > 0, chon top {len(top100)}")
    if top100:
        print(f"  Top 5: {', '.join(s['sym'] for s in top100[:5])}")
        print(f"  Bottom 5: {', '.join(s['sym'] for s in top100[-5:])}")
        mc1 = top100[0]['marketCap']/1e12
        mc2 = top100[-1]['marketCap']/1e9
        print(f"  Von hoa lon nhat: {top100[0]['sym']} = {mc1:.1f} nghin ty")
        print(f"  Von hoa nho nhat (top100): {top100[-1]['sym']} = {mc2:.0f} ty")
    return top100

# ─── STEP 2: FETCH HISTORICAL PRICES ────────────────────────────────────────

async def fetch_price_data(client: httpx.AsyncClient, sym: str) -> List[Dict]:
    try:
        r = await client.get(
            f"{FIREANT_BASE}/symbols/{sym}/historical-quotes",
            params={"startDate": "2023-01-01", "endDate": "2030-12-31", "limit": 2000},
            headers=FA_HEADERS, timeout=30
        )
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

async def fetch_all_prices(syms: List[str]) -> Dict[str, List]:
    print(f"\n{'='*80}")
    print(f"BUOC 2: Tai du lieu gia lich su cho {len(syms)} ma")
    print(f"{'='*80}")

    price_data = {}
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    ) as client:
        results = await asyncio.gather(*[fetch_price_data(client, s) for s in syms])
    for sym, data in zip(syms, results):
        price_data[sym] = data

    ok = sum(1 for v in price_data.values() if len(v) > 60)
    total_bars = sum(len(v) for v in price_data.values())
    print(f"  OK (>60 phien): {ok}/{len(syms)} ma")
    print(f"  Tong so phien: {total_bars:,}")
    return price_data

# ─── STEP 3: COMPUTE INDICATORS FOR EACH BAR ────────────────────────────────

def compute_indicators(prices: List[Dict]) -> List[Dict]:
    """
    prices: Fireant desc order (newest first).
    Returns list of enriched bars sorted oldest->newest for backtest iteration.
    """
    if len(prices) < 62:
        return []

    enriched = []
    for i in range(len(prices)):
        p = prices[i]
        close = p.get("priceClose") or 0
        open_ = p.get("priceOpen") or 0
        high = p.get("priceHigh") or 0
        low = p.get("priceLow") or 0
        vol = p.get("dealVolume") or 0
        if close <= 0:
            continue

        closes_from_here = [pp.get("priceClose") or 0 for pp in prices[i:i+62]]
        closes_from_here = [c for c in closes_from_here if c > 0]
        if len(closes_from_here) < 21:
            continue

        ma5 = statistics.mean(closes_from_here[:5]) if len(closes_from_here) >= 5 else close
        ma10 = statistics.mean(closes_from_here[:10]) if len(closes_from_here) >= 10 else close
        ma20 = statistics.mean(closes_from_here[:20]) if len(closes_from_here) >= 20 else close
        ma60 = statistics.mean(closes_from_here[:60]) if len(closes_from_here) >= 60 else ma20

        std20 = statistics.stdev(closes_from_here[:20]) if len(closes_from_here) >= 20 else 0
        bb_upper = ma20 + 2 * std20
        bb_lower = ma20 - 2 * std20
        bb_pos = safe_div(close - bb_lower, bb_upper - bb_lower, 0.5)

        rsi14 = wilder_rsi(closes_from_here, 14) if len(closes_from_here) >= 16 else 50

        vols_from_here = [pp.get("dealVolume") or 0 for pp in prices[i:i+22]]
        vol_ma20 = statistics.mean(vols_from_here[:20]) if len(vols_from_here) >= 20 else vol
        vol_ratio = safe_div(vol, vol_ma20, 1.0)

        fg_buy = p.get("buyForeignQuantity") or 0
        fg_sell = p.get("sellForeignQuantity") or 0
        fg_net = fg_buy - fg_sell
        prop_net = p.get("propTradingNetValue") or 0

        fg_net_5d = sum(
            (pp.get("buyForeignQuantity") or 0) - (pp.get("sellForeignQuantity") or 0)
            for pp in prices[i:i+5]
        )
        prop_net_5d = sum(pp.get("propTradingNetValue") or 0 for pp in prices[i:i+5])

        prev_close = closes_from_here[1] if len(closes_from_here) > 1 else close
        day_return = (close / prev_close - 1) * 100 if prev_close > 0 else 0

        consecutive_down = 0
        for j in range(1, min(len(closes_from_here), 10)):
            if j + 1 < len(closes_from_here) and closes_from_here[j] < closes_from_here[j+1]:
                consecutive_down += 1
            else:
                break

        consecutive_up = 0
        for j in range(1, min(len(closes_from_here), 10)):
            if j + 1 < len(closes_from_here) and closes_from_here[j] > closes_from_here[j+1]:
                consecutive_up += 1
            else:
                break

        vs_ma20 = (close / ma20 - 1) * 100 if ma20 > 0 else 0
        vs_ma60 = (close / ma60 - 1) * 100 if ma60 > 0 else 0

        bar_date = (p.get("date") or "")[:10]

        enriched.append({
            "date": bar_date,
            "close": close,
            "open": open_,
            "high": high,
            "low": low,
            "vol": vol,
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "ma60": ma60,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_pos": bb_pos,
            "rsi14": rsi14,
            "vol_ratio": vol_ratio,
            "vol_ma20": vol_ma20,
            "vs_ma20": vs_ma20,
            "vs_ma60": vs_ma60,
            "fg_net": fg_net,
            "fg_net_5d": fg_net_5d,
            "prop_net": prop_net,
            "prop_net_5d": prop_net_5d,
            "day_return": day_return,
            "consecutive_down": consecutive_down,
            "consecutive_up": consecutive_up,
            "std20": std20,
        })

    enriched.reverse()
    return enriched

# ─── STEP 4: DEFINE STRATEGIES ───────────────────────────────────────────────

def define_strategies():
    """
    Each strategy is a (name, filter_fn) tuple.
    filter_fn(bar) -> bool: whether to BUY at close of this bar.
    """
    strategies = []

    # === RSI-based ===
    strategies.append(("RSI < 30", lambda b: b["rsi14"] < 30))
    strategies.append(("RSI < 35", lambda b: b["rsi14"] < 35))
    strategies.append(("RSI < 40", lambda b: b["rsi14"] < 40))
    strategies.append(("RSI 30-40", lambda b: 30 <= b["rsi14"] < 40))
    strategies.append(("RSI > 70 (overbought)", lambda b: b["rsi14"] > 70))

    # === Bollinger Band ===
    strategies.append(("BB pos < 0.1 (near lower)", lambda b: b["bb_pos"] < 0.1))
    strategies.append(("BB pos < 0.2", lambda b: b["bb_pos"] < 0.2))
    strategies.append(("BB pos > 0.9 (near upper)", lambda b: b["bb_pos"] > 0.9))

    # === Price vs MA ===
    strategies.append(("Gia duoi MA20 1-3%", lambda b: -3 <= b["vs_ma20"] <= -1))
    strategies.append(("Gia duoi MA20 3-5%", lambda b: -5 <= b["vs_ma20"] < -3))
    strategies.append(("Gia duoi MA20 >5%", lambda b: b["vs_ma20"] < -5))
    strategies.append(("Gia tren MA20 0-2%", lambda b: 0 <= b["vs_ma20"] <= 2))
    strategies.append(("Gia tren MA20 2-5%", lambda b: 2 < b["vs_ma20"] <= 5))
    strategies.append(("MA5 > MA20 (uptrend)", lambda b: b["ma5"] > b["ma20"]))
    strategies.append(("MA5 < MA20 (downtrend)", lambda b: b["ma5"] < b["ma20"]))
    strategies.append(("Gia > MA60 (long-term up)", lambda b: b["close"] > b["ma60"]))
    strategies.append(("Gia < MA60 (long-term down)", lambda b: b["close"] < b["ma60"]))

    # === Volume ===
    strategies.append(("Vol tang dot bien >2x", lambda b: b["vol_ratio"] > 2.0))
    strategies.append(("Vol tang >1.5x", lambda b: b["vol_ratio"] > 1.5))
    strategies.append(("Vol thap <0.5x", lambda b: b["vol_ratio"] < 0.5))

    # === Consecutive days ===
    strategies.append(("3 phien giam lien tiep", lambda b: b["consecutive_down"] >= 3))
    strategies.append(("4 phien giam lien tiep", lambda b: b["consecutive_down"] >= 4))
    strategies.append(("5 phien giam lien tiep", lambda b: b["consecutive_down"] >= 5))
    strategies.append(("3 phien tang lien tiep", lambda b: b["consecutive_up"] >= 3))

    # === Day return ===
    strategies.append(("Giam >3% trong phien", lambda b: b["day_return"] < -3))
    strategies.append(("Giam >5% trong phien", lambda b: b["day_return"] < -5))
    strategies.append(("Tang >3% trong phien", lambda b: b["day_return"] > 3))

    # === Foreign + Proprietary ===
    strategies.append(("Nuoc ngoai mua rong 5d", lambda b: b["fg_net_5d"] > 0))
    strategies.append(("Nuoc ngoai ban rong 5d", lambda b: b["fg_net_5d"] < 0))
    strategies.append(("Tu doanh mua rong 5d", lambda b: b["prop_net_5d"] > 0))
    strategies.append(("Tu doanh ban rong 5d", lambda b: b["prop_net_5d"] < 0))
    strategies.append(("NN+TD cung mua rong 5d", lambda b: b["fg_net_5d"] > 0 and b["prop_net_5d"] > 0))
    strategies.append(("NN+TD cung ban rong 5d", lambda b: b["fg_net_5d"] < 0 and b["prop_net_5d"] < 0))

    # === COMBO strategies (the interesting ones) ===

    # RSI oversold + volume surge
    strategies.append(("RSI<35 + Vol>1.5x", lambda b: b["rsi14"] < 35 and b["vol_ratio"] > 1.5))
    strategies.append(("RSI<40 + Vol>2x", lambda b: b["rsi14"] < 40 and b["vol_ratio"] > 2.0))

    # RSI oversold + foreign buying
    strategies.append(("RSI<40 + NN mua rong", lambda b: b["rsi14"] < 40 and b["fg_net_5d"] > 0))

    # BB lower + volume
    strategies.append(("BB<0.2 + Vol>1.5x", lambda b: b["bb_pos"] < 0.2 and b["vol_ratio"] > 1.5))

    # Drop then foreign buy
    strategies.append(("3 giam + NN mua rong", lambda b: b["consecutive_down"] >= 3 and b["fg_net_5d"] > 0))
    strategies.append(("Giam>3% + NN mua rong", lambda b: b["day_return"] < -3 and b["fg_net_5d"] > 0))

    # Near MA20 support + good flow
    strategies.append((
        "Gan MA20 + NN+TD mua",
        lambda b: -3 <= b["vs_ma20"] <= 1 and b["fg_net_5d"] > 0 and b["prop_net_5d"] > 0
    ))

    # Strong reversal: big drop + volume spike + oversold
    strategies.append((
        "RSI<35 + Giam>3% + Vol>1.5x",
        lambda b: b["rsi14"] < 35 and b["day_return"] < -3 and b["vol_ratio"] > 1.5
    ))

    # Consecutive drop + oversold
    strategies.append(("3 giam + RSI<40", lambda b: b["consecutive_down"] >= 3 and b["rsi14"] < 40))
    strategies.append(("4 giam + RSI<35", lambda b: b["consecutive_down"] >= 4 and b["rsi14"] < 35))

    # Volume dry-up then surge (accumulation breakout)
    strategies.append((
        "Gia>MA20 + Vol>2x + RSI 40-60",
        lambda b: b["close"] > b["ma20"] and b["vol_ratio"] > 2.0 and 40 <= b["rsi14"] <= 60
    ))

    # Gap down recovery signal
    strategies.append((
        "BB<0.15 + TD mua + RSI<40",
        lambda b: b["bb_pos"] < 0.15 and b["prop_net_5d"] > 0 and b["rsi14"] < 40
    ))

    # Mean reversion: far below MA then foreign accumulate
    strategies.append((
        "Duoi MA20 >5% + NN mua",
        lambda b: b["vs_ma20"] < -5 and b["fg_net_5d"] > 0
    ))

    # Uptrend pullback
    strategies.append((
        "Uptrend (>MA60) + RSI<40",
        lambda b: b["close"] > b["ma60"] and b["rsi14"] < 40
    ))

    strategies.append((
        "Uptrend + Pullback MA20 + Vol>1.5x",
        lambda b: b["close"] > b["ma60"] and -3 <= b["vs_ma20"] <= 0 and b["vol_ratio"] > 1.5
    ))

    # Day of week
    strategies.append(("Mua thu 2 (Monday)", lambda b: _day_of_week(b["date"]) == 0))
    strategies.append(("Mua thu 3 (Tuesday)", lambda b: _day_of_week(b["date"]) == 1))
    strategies.append(("Mua thu 4 (Wednesday)", lambda b: _day_of_week(b["date"]) == 2))
    strategies.append(("Mua thu 5 (Thursday)", lambda b: _day_of_week(b["date"]) == 3))
    strategies.append(("Mua thu 6 (Friday)", lambda b: _day_of_week(b["date"]) == 4))

    return strategies


def _day_of_week(date_str: str) -> int:
    try:
        return date.fromisoformat(date_str).weekday()
    except:
        return -1

# ─── STEP 5: BACKTEST ENGINE ────────────────────────────────────────────────

def backtest_strategies(
    all_bars: Dict[str, List[Dict]],
    strategies: List[Tuple],
    hold_days: int = 3
) -> List[Dict]:
    """
    For each strategy, scan all bars for all symbols.
    When signal fires at bar[i], check return = close[i+hold_days] / close[i] - 1.
    """
    print(f"\n{'='*80}")
    print(f"BUOC 4: Backtest {len(strategies)} chien luoc | hold = {hold_days} ngay")
    print(f"{'='*80}")

    results = []

    for strat_name, strat_fn in strategies:
        wins = 0
        losses = 0
        total_return = 0.0
        returns_list = []
        trades = []

        for sym, bars in all_bars.items():
            for i in range(len(bars) - hold_days):
                bar = bars[i]
                try:
                    if not strat_fn(bar):
                        continue
                except:
                    continue

                buy_price = bar["close"]
                sell_price = bars[i + hold_days]["close"]
                ret = (sell_price / buy_price - 1) * 100

                returns_list.append(ret)
                total_return += ret
                if ret > 0:
                    wins += 1
                else:
                    losses += 1
                trades.append({
                    "sym": sym, "date": bar["date"],
                    "buy": buy_price, "sell": sell_price, "ret": ret
                })

        n = wins + losses
        if n < 30:
            results.append({
                "name": strat_name, "n": n, "wins": wins,
                "win_rate": 0, "avg_ret": 0, "med_ret": 0,
                "avg_win": 0, "avg_loss": 0, "profit_factor": 0,
                "note": f"Qua it mau ({n})"
            })
            continue

        win_rate = wins / n * 100
        avg_ret = total_return / n
        med_ret = statistics.median(returns_list) if returns_list else 0

        win_returns = [r for r in returns_list if r > 0]
        loss_returns = [r for r in returns_list if r <= 0]
        avg_win = statistics.mean(win_returns) if win_returns else 0
        avg_loss = statistics.mean(loss_returns) if loss_returns else 0
        total_win = sum(win_returns)
        total_loss = abs(sum(loss_returns))
        profit_factor = safe_div(total_win, total_loss, 0)

        results.append({
            "name": strat_name,
            "n": n,
            "wins": wins,
            "win_rate": round(win_rate, 2),
            "avg_ret": round(avg_ret, 3),
            "med_ret": round(med_ret, 3),
            "avg_win": round(avg_win, 3),
            "avg_loss": round(avg_loss, 3),
            "profit_factor": round(profit_factor, 3),
            "note": ""
        })

    return results

# ─── STEP 6: DISPLAY RESULTS ────────────────────────────────────────────────

def display_results(results: List[Dict]):
    print(f"\n{'='*120}")
    print(f"KET QUA BACKTEST - Chien luoc mua hom nay, ban sau {HOLD_DAYS} ngay giao dich")
    print(f"Top 100 co phieu von hoa lon nhat HOSE | Du lieu 2023-2026")
    print(f"{'='*120}")

    valid = [r for r in results if r["n"] >= 30]
    valid.sort(key=lambda x: x["win_rate"], reverse=True)

    print(f"\n{'Strategy':<45} {'Trades':>8} {'Wins':>7} {'Win%':>7} {'AvgRet%':>8} {'Med%':>7} {'AvgWin%':>8} {'AvgLoss%':>9} {'PF':>6}")
    print(f"{'-'*120}")

    for r in valid:
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 100 else ">100"
        marker = ""
        if r["win_rate"] >= 55 and r["avg_ret"] > 0 and r["n"] >= 100:
            marker = " ***"
        elif r["win_rate"] >= 52 and r["avg_ret"] > 0:
            marker = " *"

        print(
            f"{r['name']:<45} {r['n']:>8,} {r['wins']:>7,} {r['win_rate']:>6.1f}% "
            f"{r['avg_ret']:>+7.3f} {r['med_ret']:>+6.3f} {r['avg_win']:>+7.3f} "
            f"{r['avg_loss']:>+8.3f} {pf_str:>6}{marker}"
        )

    # Top 10 best strategies
    best = [r for r in valid if r["n"] >= 50 and r["avg_ret"] > 0]
    best.sort(key=lambda x: (x["win_rate"], x["avg_ret"]), reverse=True)

    print(f"\n{'='*120}")
    print(f"TOP 10 CHIEN LUOC TOT NHAT (>= 50 lenh, avg return > 0)")
    print(f"{'='*120}")

    for i, r in enumerate(best[:10], 1):
        print(f"\n  #{i}: {r['name']}")
        print(f"      Win rate: {r['win_rate']:.1f}% | Trades: {r['n']:,}")
        print(f"      Avg return: {r['avg_ret']:+.3f}% | Median: {r['med_ret']:+.3f}%")
        print(f"      Avg win: {r['avg_win']:+.3f}% | Avg loss: {r['avg_loss']:+.3f}% | PF: {r['profit_factor']:.2f}")

    # Worst strategies (to avoid)
    worst = [r for r in valid if r["n"] >= 50]
    worst.sort(key=lambda x: x["win_rate"])
    print(f"\n{'='*120}")
    print(f"TOP 5 CHIEN LUOC TE NHAT (NEN TRANH)")
    print(f"{'='*120}")
    for i, r in enumerate(worst[:5], 1):
        print(f"  #{i}: {r['name']} | Win: {r['win_rate']:.1f}% | N={r['n']:,} | Avg: {r['avg_ret']:+.3f}%")

    return best[:10] if best else []

# ─── STEP 7: TODAY'S SIGNALS ─────────────────────────────────────────────────

def find_today_signals(
    all_bars: Dict[str, List[Dict]],
    top_strategies: List[Dict]
) -> List[Dict]:
    """Find stocks that match top strategies today (latest bar)."""
    print(f"\n{'='*120}")
    print(f"AP DUNG TOP CHIEN LUOC CHO NGAY HOM NAY")
    print(f"{'='*120}")

    strategies = define_strategies()
    strat_dict = {name: fn for name, fn in strategies}

    today_picks = []

    for strat_result in top_strategies:
        strat_name = strat_result["name"]
        strat_fn = strat_dict.get(strat_name)
        if not strat_fn:
            continue

        matching_syms = []
        for sym, bars in all_bars.items():
            if not bars:
                continue
            latest = bars[-1]
            try:
                if strat_fn(latest):
                    matching_syms.append((sym, latest))
            except:
                continue

        if matching_syms:
            print(f"\n  {strat_name} (Win: {strat_result['win_rate']:.1f}%, N={strat_result['n']}):")
            for sym, bar in matching_syms:
                print(f"    -> {sym}: Close={bar['close']:,.0f} | RSI={bar['rsi14']:.1f} | vs MA20={bar['vs_ma20']:+.1f}% | Vol ratio={bar['vol_ratio']:.2f}")
                today_picks.append({
                    "sym": sym,
                    "strategy": strat_name,
                    "win_rate": strat_result["win_rate"],
                    "avg_ret": strat_result["avg_ret"],
                    "close": bar["close"],
                    "rsi14": bar["rsi14"],
                    "vs_ma20": bar["vs_ma20"],
                })

    # Aggregate: stocks matching multiple top strategies
    sym_counts = defaultdict(list)
    for pick in today_picks:
        sym_counts[pick["sym"]].append(pick)

    multi_match = {s: picks for s, picks in sym_counts.items() if len(picks) >= 2}
    if multi_match:
        print(f"\n{'='*80}")
        print(f"CO PHIEU KHOP NHIEU CHIEN LUOC (uu tien cao):")
        print(f"{'='*80}")
        for sym, picks in sorted(multi_match.items(), key=lambda x: len(x[1]), reverse=True):
            strats_str = ", ".join(p["strategy"] for p in picks)
            avg_wr = statistics.mean([p["win_rate"] for p in picks])
            print(f"  {sym}: {len(picks)} chiến lược | TB win rate: {avg_wr:.1f}%")
            print(f"    Strategies: {strats_str}")

    return today_picks

# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main():
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 120)
    print("PHAN TICH CHIEN LUOC MUA-LAI SAU 3 NGAY | TOP 100 CO PHIEU VON HOA LON NHAT")
    print(f"Ngay phan tich: {date.today().isoformat()}")
    print("=" * 120)

    # Step 1: Get top 100
    async with httpx.AsyncClient() as client:
        top100 = await fetch_top100_by_market_cap(client)

    syms = [s["sym"] for s in top100]
    mc_map = {s["sym"]: s["marketCap"] for s in top100}

    # Step 2: Fetch prices
    price_data = await fetch_all_prices(syms)

    # Step 3: Compute indicators
    print(f"\n{'='*80}")
    print(f"BUOC 3: Tinh chi bao ky thuat cho {len(syms)} ma")
    print(f"{'='*80}")

    all_bars = {}
    for sym in syms:
        bars = compute_indicators(price_data.get(sym, []))
        if bars:
            all_bars[sym] = bars
    print(f"  OK: {len(all_bars)} ma co du du lieu backtest")
    if all_bars:
        sample_sym = list(all_bars.keys())[0]
        print(f"  Mau: {sample_sym} co {len(all_bars[sample_sym])} phien")
        if all_bars[sample_sym]:
            print(f"  Tu {all_bars[sample_sym][0]['date']} den {all_bars[sample_sym][-1]['date']}")

    # Step 4: Backtest
    strategies = define_strategies()
    results = backtest_strategies(all_bars, strategies, HOLD_DAYS)

    # Step 5: Display
    top_strats = display_results(results)

    # Step 6: Today's signals
    if top_strats:
        find_today_signals(all_bars, top_strats)

    # Save results to JSON
    output = {
        "analysis_date": date.today().isoformat(),
        "hold_days": HOLD_DAYS,
        "num_stocks": len(all_bars),
        "strategies": results,
        "top_strategies": top_strats,
    }
    output_path = os.path.join(os.path.dirname(__file__), "3day_analysis_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_path}")

    print("\n" + "=" * 120)
    print("HOAN TAT PHAN TICH!")
    print("=" * 120)
    return output


if __name__ == "__main__":
    asyncio.run(main())
