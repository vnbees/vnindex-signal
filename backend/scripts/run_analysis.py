#!/usr/bin/env python3
"""
Phân tích tín hiệu mua bán TOP 30 cổ phiếu vốn hoá lớn nhất HOSE
Ngày: 2026-03-30 (Thứ Hai)
"""

import asyncio
import httpx
import statistics
import math
import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ─── THÔNG SỐ ────────────────────────────────────────────────────────────────
TODAY = date(2026, 3, 30)   # Thứ Hai
TOP_N = 30
HOLD_DAYS = 20

FIREANT_TOKEN = (
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

WEBSITE_URL = "https://vnindex-signal-production.up.railway.app"
API_KEY = "sk-vnindex-c87e097efb4dac431dabb8a52e3e5af57e73a74a"

FIREANT_BASE = "https://restv2.fireant.vn"
FA_HEADERS = {"Authorization": f"Bearer {FIREANT_TOKEN}", "Content-Type": "application/json"}

CANDIDATES = [
    "VCB","BID","CTG","TCB","MBB","VIC","VHM","VRE","HPG","NVL","MSN","MWG",
    "FPT","VNM","GAS","PLX","POW","VJC","HVN",
    "ACB","STB","VPB","HDB","LPB","SSB","SHB","OCB","TPB","EIB","MSB",
    "SSI","VND","HCM","MBS","VCI","BSI","AGR",
    "REE","PNJ","DGC","DPM","DCM","PHR","VHC","CSV","BSR",
    "SAB","BHN","MCH","QNS","VEA","PAN","BAF","HNG","HAG",
    "BCM","KDH","NLG","DXG","PDR","DIG","CEO","SCR","VPI","KBC","IDC","SZC","SIP",
    "PVS","PVD","PVT","OIL","GEE",
    "GMD","VSC","HAH","DVP","STG","VTO",
    "VGC","LHG","HII",
    "NT2","PGV","HND","EVG",
    "EVF","CTD","GEG",
]

# ─── UTILITIES ────────────────────────────────────────────────────────────────

def wilder_rsi(closes: List[float], period: int = 14) -> float:
    """Wilder RSI - closes[0] là phiên mới nhất."""
    prices = list(reversed(closes))  # oldest first
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
        if b and b != 0:
            return a / b
        return default
    except:
        return default

def parse_date(s: str) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except:
        return None

# ─── BƯỚC 1: TOP N THEO VỐN HOÁ ──────────────────────────────────────────────

async def get_top_stocks(client: httpx.AsyncClient) -> List[Dict]:
    print(f"\n🔍 Bước 1: Lấy top {TOP_N} mã theo vốn hoá...")

    async def fetch_fundamental(sym: str) -> Optional[Dict]:
        try:
            r = await client.get(f"{FIREANT_BASE}/symbols/{sym}/fundamental", headers=FA_HEADERS, timeout=15)
            if r.status_code == 200:
                d = r.json()
                mc = d.get("marketCap", 0)
                if mc and mc > 0:
                    return {"sym": sym, "marketCap": mc, "pe": d.get("pe"), "eps": d.get("eps")}
        except Exception as e:
            pass
        return None

    results = await asyncio.gather(*[fetch_fundamental(s) for s in CANDIDATES])
    valid = [r for r in results if r]
    valid.sort(key=lambda x: x["marketCap"], reverse=True)
    top = valid[:TOP_N]
    syms = [x["sym"] for x in top]
    print(f"✅ Top {TOP_N}: {', '.join(syms)}")
    return top

# ─── BƯỚC 2: THU THẬP DỮ LIỆU ────────────────────────────────────────────────

async def fetch_price_data(client: httpx.AsyncClient, sym: str) -> List[Dict]:
    try:
        r = await client.get(
            f"{FIREANT_BASE}/symbols/{sym}/historical-quotes",
            params={"startDate": "2021-01-01", "endDate": "2030-12-31", "limit": 1000},
            headers=FA_HEADERS, timeout=30
        )
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

async def fetch_financial_data(client: httpx.AsyncClient, sym: str) -> Optional[Dict]:
    try:
        r = await client.get(
            f"{FIREANT_BASE}/symbols/{sym}/financial-reports",
            params={"limit": 20, "type": 1},
            headers=FA_HEADERS, timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "rows" in data:
                return data
    except:
        pass
    return None

async def collect_data(syms: List[str]) -> Tuple[Dict, Dict]:
    print(f"\n📥 Bước 2: Thu thập dữ liệu cho {len(syms)} mã (song song)...")
    price_data: Dict[str, List] = {}
    fin_data: Dict[str, Optional[Dict]] = {}

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)) as client:
        price_results = await asyncio.gather(*[fetch_price_data(client, s) for s in syms])
        fin_results = await asyncio.gather(*[fetch_financial_data(client, s) for s in syms])

    for sym, data in zip(syms, price_results):
        price_data[sym] = data
    for sym, data in zip(syms, fin_results):
        fin_data[sym] = data

    ok_price = sum(1 for v in price_data.values() if v)
    ok_fin = sum(1 for v in fin_data.values() if v)
    print(f"✅ Giá: {ok_price}/{len(syms)} | Tài chính: {ok_fin}/{len(syms)}")

    # Retry missing price data
    missing_price = [s for s in syms if not price_data.get(s)]
    if missing_price:
        print(f"   Retry {len(missing_price)} mã thiếu giá: {', '.join(missing_price)}")
        async with httpx.AsyncClient() as client2:
            retry_results = await asyncio.gather(*[fetch_price_data(client2, s) for s in missing_price])
        for sym, data in zip(missing_price, retry_results):
            if data:
                price_data[sym] = data
        ok_price2 = sum(1 for v in price_data.values() if v)
        print(f"   Sau retry - Giá: {ok_price2}/{len(syms)}")

    return price_data, fin_data

# ─── BƯỚC 3A: TÍN HIỆU TÀI CHÍNH ────────────────────────────────────────────

PUBLISH_LAG_DAYS = 45

def get_quarter_end(q: int, year: int) -> date:
    ends = {1: date(year, 3, 31), 2: date(year, 6, 30), 3: date(year, 9, 30), 4: date(year, 12, 31)}
    return ends[q]

def get_available_quarters(today: date) -> List[Tuple[int, int]]:
    """Trả về list (quarter, year) đã qua publish lag, mới nhất trước."""
    quarters = []
    for y in range(today.year, today.year - 3, -1):
        for q in range(4, 0, -1):
            qend = get_quarter_end(q, y)
            avail = qend + timedelta(days=PUBLISH_LAG_DAYS)
            if avail <= today:
                quarters.append((q, y))
    return quarters

def parse_financial_rows(report) -> Dict:
    """
    Fireant financial-reports type=1 trả về dict:
      {"symbol": "VCB", "columns": ["Name","Symbol","Q1/2021",...], "rows": [...]}
    Mỗi row là: [name_str, code_str, val_Q1, val_Q2, ...]
    Returns {(q, year): {"Sales": val, "NetProfit": val, ...}}
    """
    if not report or not isinstance(report, dict):
        return {}

    columns = report.get("columns") or []
    rows = report.get("rows") or []

    # Parse quarter columns starting at index 2
    quarter_cols = []  # [(q, year, col_idx)]
    for i, col in enumerate(columns):
        if i < 2:
            continue
        try:
            # Format: "Q1/2025"
            q_part, y_part = col.split("/")
            q = int(q_part[1:])
            year = int(y_part)
            quarter_cols.append((q, year, i))
        except:
            pass

    by_quarter = {}
    for q, year, col_idx in quarter_cols:
        metrics = {}
        for row in rows:
            if isinstance(row, list) and len(row) > col_idx:
                code = row[1] if len(row) > 1 else ""
                val = row[col_idx]
                if val is not None:
                    metrics[code] = val
        by_quarter[(q, year)] = metrics
    return by_quarter

def extract_fin_metric(metrics: Dict, keys: List[str]) -> Optional[float]:
    for k in keys:
        v = metrics.get(k)
        if v is not None:
            try:
                return float(v)
            except:
                pass
    return None

SALES_KEYS = ["Sales", "NetRevenue"]
PROFIT_KEYS = ["NetProfit", "NetProfit_PCSH"]

def calc_financial_score(sym: str, fin_data) -> Tuple[int, Dict]:
    """Tính điểm tài chính và detail. fin_data là dict từ Fireant financial-reports."""
    detail = {"quarter": None, "lnstYoY": None, "salesYoY": None,
              "marginDelta": None, "earningsAccel": None}

    if not fin_data:
        return 0, detail

    # Parse theo quý
    by_q = parse_financial_rows(fin_data)
    available = get_available_quarters(TODAY)

    if not available:
        return 0, detail

    # Lấy quý gần nhất có data
    latest_q, latest_y = None, None
    for q, y in available:
        if (q, y) in by_q:
            latest_q, latest_y = q, y
            break

    if not latest_q:
        return 0, detail

    # Quý cùng kỳ năm trước
    prev_y = latest_y - 1
    # Quý liền trước (để tính earningsAccel)
    if latest_q == 1:
        prev_q_q, prev_q_y = 4, latest_y - 1
    else:
        prev_q_q, prev_q_y = latest_q - 1, latest_y

    curr = by_q.get((latest_q, latest_y), {})
    same_prev = by_q.get((latest_q, prev_y), {})
    prev_q = by_q.get((prev_q_q, prev_q_y), {})

    # Extract metrics
    def get_sales(m):
        return extract_fin_metric(m, SALES_KEYS)
    def get_profit(m):
        return extract_fin_metric(m, PROFIT_KEYS)

    sales_now = get_sales(curr)
    sales_prev = get_sales(same_prev)
    profit_now = get_profit(curr)
    profit_prev = get_profit(same_prev)

    detail["quarter"] = f"Q{latest_q}/{latest_y}"

    # Cần có đủ data để tính
    if profit_now is None or profit_prev is None or profit_prev == 0:
        return 0, detail

    lnst_yoy = (profit_now / abs(profit_prev) - 1) * 100 if profit_prev != 0 else 0
    detail["lnstYoY"] = round(lnst_yoy, 2)

    if sales_now and sales_prev and sales_prev != 0:
        sales_yoy = (sales_now / abs(sales_prev) - 1) * 100
        detail["salesYoY"] = round(sales_yoy, 2)
    else:
        sales_yoy = None

    # Margin
    margin_now = safe_div(profit_now, sales_now) * 100 if sales_now else None
    margin_prev_val = safe_div(profit_prev, sales_prev) * 100 if sales_prev else None
    if margin_now is not None and margin_prev_val is not None:
        margin_delta = margin_now - margin_prev_val
        detail["marginDelta"] = round(margin_delta, 2)
    else:
        margin_delta = None

    # EarningsAccel
    profit_pq = get_profit(prev_q)
    profit_pq_yoy_base = get_profit(by_q.get((prev_q_q, prev_q_y - 1), {}))
    earnings_accel = None
    if (profit_pq is not None and profit_pq_yoy_base is not None
            and profit_pq_yoy_base != 0):
        lnst_yoy_prev_q = (profit_pq / abs(profit_pq_yoy_base) - 1) * 100
        earnings_accel = lnst_yoy - lnst_yoy_prev_q
        detail["earningsAccel"] = round(earnings_accel, 2)

    # Scoring — kiểm tra specific trước, general sau
    score = 0
    if earnings_accel is not None and earnings_accel > 10:
        score = 2
    elif lnst_yoy < 0 and margin_delta is not None and margin_delta < -2:
        score = -2  # lỗ kép: earnings xấu + margin xấu
    elif lnst_yoy < 0 and margin_delta is not None and margin_delta > 0:
        score = 2   # bad news priced in + improving margin
    elif 0 <= lnst_yoy <= 10 and margin_delta is not None and margin_delta > 0:
        score = 1
    elif lnst_yoy < 0:
        score = 1   # bad news priced in (alone)
    elif 10 < lnst_yoy <= 20:
        score = 0
    elif lnst_yoy > 30 and sales_yoy is not None and sales_yoy > 15:
        score = -1  # sell the news risk

    return score, detail

# ─── BƯỚC 3B: SEASONALITY ────────────────────────────────────────────────────

def calc_seasonal_score(today: date) -> Tuple[int, Dict]:
    m = today.month
    dow = today.weekday() + 1  # 1=Mon...5=Fri

    score = 0
    reason = "neutral"

    if m == 11 and dow == 4:  # thứ 5
        score = 2
        reason = "tháng 11 + thứ 5 (P=60.4%)"
    elif m == 11:
        score = 1
        reason = "tháng 11 (P=52.8%)"
    elif m == 2:
        score = 1
        reason = "tháng 2 (P=51.4%)"
    elif dow == 4:  # thứ 5
        score = 1
        reason = "thứ 5 (P=51.0%)"
    elif m == 10:
        score = -2
        reason = "tháng 10 (P=42.2%, TRÁNH)"
    elif dow == 2:  # thứ 3
        score = -1
        reason = "thứ 3 (P=44.8%, TRÁNH)"
    else:
        reason = f"tháng {m}, thứ {dow} (neutral)"

    return score, {"month": m, "dayOfWeek": dow, "reason": reason}

# ─── BƯỚC 3C: KỸ THUẬT ───────────────────────────────────────────────────────

def calc_technical_score(sym: str, prices: List[Dict]) -> Tuple[int, Dict]:
    detail = {"vsMa20": None, "rsi14": None, "bbPos": None, "ma20": None, "ma60": None}
    if not prices or len(prices) < 20:
        return 0, detail

    # prices[0] = phiên mới nhất (Fireant trả về desc)
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

    prop_vals = [p.get("propTradingNetValue") or 0 for p in prices[:60]]
    prop_med = statistics.median(prop_vals) if prop_vals else 0
    prop_latest = prices[0].get("propTradingNetValue") or 0

    detail.update({
        "vsMa20": round(vs_ma20, 2),
        "rsi14": rsi14,
        "bbPos": round(bb_pos, 3),
        "ma20": round(ma20),
        "ma60": round(ma60)
    })

    # Scoring
    in_zone = -3 <= vs_ma20 <= 1
    if in_zone and prop_latest > prop_med:
        return 1, detail
    elif vs_ma20 > 3:
        return -1, detail
    return 0, detail

# ─── BƯỚC 3D: DÒNG TIỀN ──────────────────────────────────────────────────────

def calc_cashflow_score(sym: str, prices: List[Dict]) -> Tuple[int, Dict]:
    detail = {"fgNet5d": None, "propNet5d": None, "fgNet5dZ": 0.0}
    if not prices or len(prices) < 5:
        return 0, detail

    fg_net_5d = sum(
        (p.get("buyForeignQuantity") or 0) - (p.get("sellForeignQuantity") or 0)
        for p in prices[:5]
    )
    prop_net_5d = sum(p.get("propTradingNetValue") or 0 for p in prices[:5])

    # z-score of fgNet5d
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

    detail.update({
        "fgNet5d": float(fg_net_5d),
        "propNet5d": float(prop_net_5d),
        "fgNet5dZ": round(fg_z, 2)
    })

    if fg_net_5d > 0 and prop_net_5d > 0:
        return 1, detail
    elif fg_net_5d < 0 and prop_net_5d < 0:
        return -1, detail
    return 0, detail

# ─── BƯỚC 4: TỔNG ĐIỂM & KHUYẾN NGHỊ ────────────────────────────────────────

def get_recommendation(total: int) -> str:
    if total >= 4:
        return "BUY_STRONG"
    elif total >= 2:
        return "BUY"
    elif total >= 0:
        return "HOLD"
    elif total >= -2:
        return "AVOID"
    else:
        return "SELL"

def rec_icon(r: str) -> str:
    return {"BUY_STRONG": "🟢🟢", "BUY": "🟢", "HOLD": "🟡", "AVOID": "🔴", "SELL": "🔴🔴"}.get(r, "⚪")

# ─── BƯỚC 5: OUTPUT ──────────────────────────────────────────────────────────

def display_results(signals: List[Dict]):
    print(f"\n{'='*105}")
    print(f"📊 Phân tích TOP {TOP_N} mã theo vốn hoá lớn nhất HOSE | {TODAY.strftime('%Y-%m-%d')}")
    print(f"TC=Tài chính | SS=Seasonality | KT=Kỹ thuật | DT=Dòng tiền")
    print(f"{'='*105}")
    header = f"{'Vốn hoá(tỷ)':>14} | {'Mã':^5} | {'TC':^4} | {'SS':^4} | {'KT':^4} | {'DT':^4} | {'TỔNG':^5} | Khuyến nghị"
    print(header)
    print(f"{'-'*105}")

    for s in signals:
        mc_bil = s["market_cap_bil"]
        sym = s["symbol"]
        tc = s["score_financial"]
        ss = s["score_seasonal"]
        kt = s["score_technical"]
        dt = s["score_cashflow"]
        tot = s["score_total"]
        rec = s["recommendation"]
        icon = rec_icon(rec)
        print(f"{mc_bil:>14,.0f} | {sym:^5} | {tc:^4} | {ss:^4} | {kt:^4} | {dt:^4} | {tot:^5} | {icon} {rec}")

    print(f"{'='*105}")

    # Chi tiết các mã điểm cao/thấp
    notable = [s for s in signals if s["score_total"] >= 2 or s["score_total"] <= -2]
    if notable:
        print(f"\n📋 Chi tiết các mã nổi bật:")
        for s in notable:
            icon = rec_icon(s["recommendation"])
            print(f"\n  {icon} {s['symbol']} (Tổng: {s['score_total']:+d})")
            df = s.get("detail_financial", {})
            if df.get("quarter"):
                print(f"    📊 Tài chính [{df['quarter']}]:")
                print(f"       LNST YoY: {df.get('lnstYoY','N/A')}%  | Doanh thu YoY: {df.get('salesYoY','N/A')}%")
                print(f"       Margin Δ: {df.get('marginDelta','N/A')}pp | Earnings Accel: {df.get('earningsAccel','N/A')}pp")
            dt_d = s.get("detail_technical", {})
            if dt_d.get("ma20"):
                print(f"    📈 Kỹ thuật: Giá {s['price_close_signal_date']:,.0f} | vs MA20 {dt_d.get('vsMa20',0):+.1f}% | RSI14 {dt_d.get('rsi14',0):.1f} | BB {dt_d.get('bbPos',0):.2f}")
            dc = s.get("detail_cashflow", {})
            if dc.get("fgNet5d") is not None:
                fg = dc["fgNet5d"]
                prop = dc["propNet5d"]
                print(f"    💰 Dòng tiền: Ngoại 5d {fg:+,.0f} CP | Tự doanh 5d {prop:+,.0f}")
            ds = s.get("detail_seasonal", {})
            print(f"    📅 Seasonality (điểm SS={s['score_seasonal']:+d}): {ds.get('reason','')}")

    print(f"\n{'─'*80}")
    print(f"📊 Phân tích {TOP_N} mã theo vốn hoá lớn nhất HOSE | {TODAY.strftime('%Y-%m-%d')}")
    print(f"Backtest: 989 obs tài chính (2015-2025) + 18,563 obs kỹ thuật/seasonality (2022-2026)")
    print(f"⚠️  Không phải khuyến nghị đầu tư. Kết hợp với phân tích riêng và quản lý rủi ro.")

# ─── BƯỚC 6A: POST SIGNALS ───────────────────────────────────────────────────

async def post_signals(signals: List[Dict]) -> bool:
    print(f"\n📤 Bước 6A: POST {len(signals)} signals lên {WEBSITE_URL}...")
    payload = {
        "run_date": TODAY.isoformat(),
        "top_n": TOP_N,
        "hold_days": HOLD_DAYS,
        "signals": signals
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{WEBSITE_URL}/api/v1/signals", json=payload, headers=headers)
        if r.status_code in (200, 201):
            print(f"✅ POST signals OK ({r.status_code})")
            # Refresh views
            r2 = await client.post(f"{WEBSITE_URL}/api/v1/admin/refresh-views", json={}, headers=headers)
            if r2.status_code == 200:
                print(f"✅ Refresh views OK")
            else:
                print(f"⚠️  Refresh views: {r2.status_code} - {r2.text[:200]}")
            return True
        else:
            print(f"❌ POST signals FAILED: {r.status_code}")
            print(f"   {r.text[:500]}")
            return False

# ─── BƯỚC 6B: PRICE TRACKING ─────────────────────────────────────────────────

async def update_price_tracking(price_data: Dict[str, List]) -> None:
    print(f"\n💹 Bước 6B: Update price tracking...")
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{WEBSITE_URL}/api/v1/price-updates/pending?limit=10000", headers=headers)
        if r.status_code != 200:
            print(f"⚠️  Không lấy được pending: {r.status_code}")
            return

        pending = r.json()
        if not pending:
            print("✅ Không có price tracking cần update")
            return

        print(f"   Tìm thấy {len(pending)} pending records")

        # Fetch thêm symbols chưa có
        missing = set()
        for item in pending:
            sym = item.get("symbol")
            if sym and sym not in price_data:
                missing.add(sym)

        if missing:
            print(f"   Fetch bổ sung {len(missing)} symbols: {', '.join(missing)}")
            async with httpx.AsyncClient() as client2:
                results = await asyncio.gather(*[fetch_price_data(client2, s) for s in missing])
            for sym, data in zip(missing, results):
                price_data[sym] = data

        # Build price lookup: {sym: {date_str: {open, close}}}
        price_lookup: Dict[str, Dict[str, Dict]] = {}
        for sym, records in price_data.items():
            price_lookup[sym] = {}
            for rec in records:
                d = (rec.get("date") or "")[:10]
                if d:
                    price_lookup[sym][d] = {
                        "price_open": rec.get("priceOpen") or 0,
                        "price_close": rec.get("priceClose") or 0
                    }

        # Group by track_date
        by_date: Dict[str, List[Dict]] = {}
        for item in pending:
            sym = item.get("symbol")
            for td in item.get("track_dates_needed") or []:
                td_str = td[:10]
                # Skip if today (phiên chưa chốt) — but allow if it's in price_lookup
                if td_str > TODAY.isoformat():
                    continue
                if td_str not in by_date:
                    by_date[td_str] = []
                by_date[td_str].append({"signal_id": item.get("signal_id"), "symbol": sym})

        sorted_dates = sorted(by_date.keys())
        total_updated = 0
        for i, track_date in enumerate(sorted_dates):
            is_last = (i == len(sorted_dates) - 1)
            items = by_date[track_date]
            prices = []
            for it in items:
                sym = it["symbol"]
                rec = price_lookup.get(sym, {}).get(track_date)
                if rec and rec["price_close"] > 0:
                    prices.append({"symbol": sym, "price_open": rec["price_open"],
                                   "price_close": rec["price_close"]})

            if not prices:
                continue

            body = {"track_date": track_date, "prices": prices,
                    "skip_refresh": not is_last}
            r2 = await client.post(f"{WEBSITE_URL}/api/v1/price-updates", json=body, headers=headers)
            if r2.status_code in (200, 201):
                total_updated += len(prices)
            else:
                print(f"   ⚠️  {track_date}: {r2.status_code} - {r2.text[:100]}")

        print(f"✅ Đã update price tracking: {total_updated} records cho {len(sorted_dates)} ngày giao dịch")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 80)
    print(f"🚀 PHÂN TÍCH TÍN HIỆU CỔ PHIẾU TỰ ĐỘNG — TOP {TOP_N} VỐN HOÁ HOSE")
    print(f"   Ngày: {TODAY.strftime('%Y-%m-%d')} (Thứ Hai)")
    print("=" * 80)

    # Bước 1: Top N stocks
    async with httpx.AsyncClient() as client:
        top_stocks = await get_top_stocks(client)

    syms = [x["sym"] for x in top_stocks]
    mc_map = {x["sym"]: x["marketCap"] for x in top_stocks}

    # Bước 2: Collect data
    price_data, fin_data = await collect_data(syms)

    # Seasonality (cùng cho tất cả)
    score_ss, detail_ss = calc_seasonal_score(TODAY)
    print(f"\n📅 Seasonality: {detail_ss['reason']} → điểm {score_ss:+d}")

    # Bước 3-4: Tính signals
    print(f"\n🧮 Bước 3-4: Tính toán tín hiệu...")
    signals = []
    for stock in top_stocks:
        sym = stock["sym"]
        prices = price_data.get(sym, [])
        fins = fin_data.get(sym, [])

        score_tc, detail_tc_fin = calc_financial_score(sym, fins)
        score_kt, detail_kt = calc_technical_score(sym, prices)
        score_dt, detail_dt = calc_cashflow_score(sym, prices)

        total = score_tc + score_ss + score_kt + score_dt
        rec = get_recommendation(total)
        price_close = (prices[0].get("priceClose") or 0) if prices else 0
        mc_bil = mc_map[sym] / 1e9

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
            "detail_financial": detail_tc_fin,
            "detail_technical": detail_kt,
            "detail_cashflow": detail_dt,
            "detail_seasonal": detail_ss,
        })

    # Sort by total score
    signals.sort(key=lambda x: x["score_total"], reverse=True)
    print(f"✅ Tính xong {len(signals)} signals")

    # Bước 5: Display
    display_results(signals)

    # Bước 6A: POST
    await post_signals(signals)

    # Bước 6B: Price tracking
    await update_price_tracking(price_data)

    print("\n✅ HOÀN TẤT!")

if __name__ == "__main__":
    asyncio.run(main())
