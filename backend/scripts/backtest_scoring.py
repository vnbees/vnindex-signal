# -*- coding: utf-8 -*-
"""
Scoring logic copied from backend/scripts/run_analysis.py for walk-forward backtest only.
Do not import from run_analysis (globals TODAY). Parameterized: as_of date + OHLCV rows newest-first.

Source snapshot: vnindex-signal run_analysis.py — keep in sync manually if production rules change.
"""

from __future__ import annotations

import math
import statistics
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

PUBLISH_LAG_DAYS = 45
SALES_KEYS = ["Sales", "NetRevenue"]
PROFIT_KEYS = ["NetProfit", "NetProfit_PCSH"]


def wilder_rsi(closes: List[float], period: int = 14) -> float:
    """Wilder RSI — closes[0] is newest session."""
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
        if b and b != 0:
            return a / b
        return default
    except Exception:
        return default


def get_quarter_end(q: int, year: int) -> date:
    ends = {1: date(year, 3, 31), 2: date(year, 6, 30), 3: date(year, 9, 30), 4: date(year, 12, 31)}
    return ends[q]


def get_available_quarters(as_of: date) -> List[Tuple[int, int]]:
    """(quarter, year) that have passed publish lag relative to as_of; newest first."""
    quarters: List[Tuple[int, int]] = []
    for y in range(as_of.year, as_of.year - 25, -1):
        for q in range(4, 0, -1):
            qend = get_quarter_end(q, y)
            avail = qend + timedelta(days=PUBLISH_LAG_DAYS)
            if avail <= as_of:
                quarters.append((q, y))
    return quarters


def parse_financial_rows(report) -> Dict:
    if not report or not isinstance(report, dict):
        return {}

    columns = report.get("columns") or []
    rows = report.get("rows") or []

    quarter_cols: List[Tuple[int, int, int]] = []
    for i, col in enumerate(columns):
        if i < 2:
            continue
        try:
            q_part, y_part = col.split("/")
            q = int(q_part[1:])
            year = int(y_part)
            quarter_cols.append((q, year, i))
        except Exception:
            pass

    by_quarter: Dict[Tuple[int, int], Dict] = {}
    for q, year, col_idx in quarter_cols:
        metrics: Dict[str, float] = {}
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
            except Exception:
                pass
    return None


def calc_financial_score(sym: str, fin_data, as_of: date) -> Tuple[int, Dict]:
    detail = {
        "quarter": None,
        "lnstYoY": None,
        "salesYoY": None,
        "marginDelta": None,
        "earningsAccel": None,
    }

    if not fin_data:
        return 0, detail

    by_q = parse_financial_rows(fin_data)
    available = get_available_quarters(as_of)

    if not available:
        return 0, detail

    latest_q, latest_y = None, None
    for q, y in available:
        if (q, y) in by_q:
            latest_q, latest_y = q, y
            break

    if not latest_q:
        return 0, detail

    prev_y = latest_y - 1
    if latest_q == 1:
        prev_q_q, prev_q_y = 4, latest_y - 1
    else:
        prev_q_q, prev_q_y = latest_q - 1, latest_y

    curr = by_q.get((latest_q, latest_y), {})
    same_prev = by_q.get((latest_q, prev_y), {})
    prev_q = by_q.get((prev_q_q, prev_q_y), {})

    def get_sales(m):
        return extract_fin_metric(m, SALES_KEYS)

    def get_profit(m):
        return extract_fin_metric(m, PROFIT_KEYS)

    sales_now = get_sales(curr)
    sales_prev = get_sales(same_prev)
    profit_now = get_profit(curr)
    profit_prev = get_profit(same_prev)

    detail["quarter"] = f"Q{latest_q}/{latest_y}"

    if profit_now is None or profit_prev is None or profit_prev == 0:
        return 0, detail

    lnst_yoy = (profit_now / abs(profit_prev) - 1) * 100 if profit_prev != 0 else 0
    detail["lnstYoY"] = round(lnst_yoy, 2)

    if sales_now and sales_prev and sales_prev != 0:
        sales_yoy = (sales_now / abs(sales_prev) - 1) * 100
        detail["salesYoY"] = round(sales_yoy, 2)
    else:
        sales_yoy = None

    margin_now = safe_div(profit_now, sales_now) * 100 if sales_now else None
    margin_prev_val = safe_div(profit_prev, sales_prev) * 100 if sales_prev else None
    if margin_now is not None and margin_prev_val is not None:
        margin_delta = margin_now - margin_prev_val
        detail["marginDelta"] = round(margin_delta, 2)
    else:
        margin_delta = None

    profit_pq = get_profit(prev_q)
    profit_pq_yoy_base = get_profit(by_q.get((prev_q_q, prev_q_y - 1), {}))
    earnings_accel = None
    if profit_pq is not None and profit_pq_yoy_base is not None and profit_pq_yoy_base != 0:
        lnst_yoy_prev_q = (profit_pq / abs(profit_pq_yoy_base) - 1) * 100
        earnings_accel = lnst_yoy - lnst_yoy_prev_q
        detail["earningsAccel"] = round(earnings_accel, 2)

    score = 0
    if earnings_accel is not None and earnings_accel > 10:
        score = 2
    elif lnst_yoy < 0 and margin_delta is not None and margin_delta < -2:
        score = -2
    elif lnst_yoy < 0 and margin_delta is not None and margin_delta > 0:
        score = 2
    elif 0 <= lnst_yoy <= 10 and margin_delta is not None and margin_delta > 0:
        score = 1
    elif lnst_yoy < 0:
        score = 1
    elif 10 < lnst_yoy <= 20:
        score = 0
    elif lnst_yoy > 30 and sales_yoy is not None and sales_yoy > 15:
        score = -1

    return score, detail


def calc_seasonal_score(d: date) -> Tuple[int, Dict]:
    m = d.month
    dow = d.weekday() + 1

    score = 0
    reason = "neutral"

    if m == 11 and dow == 4:
        score = 2
        reason = "tháng 11 + thứ 5 (P=60.4%)"
    elif m == 11:
        score = 1
        reason = "tháng 11 (P=52.8%)"
    elif m == 2:
        score = 1
        reason = "tháng 2 (P=51.4%)"
    elif dow == 4:
        score = 1
        reason = "thứ 5 (P=51.0%)"
    elif m == 10:
        score = -2
        reason = "tháng 10 (P=42.2%, TRÁNH)"
    elif dow == 2:
        score = -1
        reason = "thứ 3 (P=44.8%, TRÁNH)"
    else:
        reason = f"tháng {m}, thứ {dow} (neutral)"

    return score, {"month": m, "dayOfWeek": dow, "reason": reason}


def calc_technical_score(sym: str, prices_desc: List[Dict]) -> Tuple[int, Dict]:
    """prices_desc: newest first (same convention as Fireant API)."""
    detail = {"vsMa20": None, "rsi14": None, "bbPos": None, "ma20": None, "ma60": None}
    if not prices_desc or len(prices_desc) < 20:
        return 0, detail

    closes = [p.get("priceClose") or 0 for p in prices_desc]
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

    prop_vals = [p.get("propTradingNetValue") or 0 for p in prices_desc[:60]]
    prop_med = statistics.median(prop_vals) if prop_vals else 0
    prop_latest = prices_desc[0].get("propTradingNetValue") or 0

    detail.update(
        {
            "vsMa20": round(vs_ma20, 2),
            "rsi14": rsi14,
            "bbPos": round(bb_pos, 3),
            "ma20": round(ma20),
            "ma60": round(ma60),
        }
    )

    in_zone = -3 <= vs_ma20 <= 1
    if in_zone and prop_latest > prop_med:
        return 1, detail
    if vs_ma20 > 3:
        return -1, detail
    return 0, detail


def calc_cashflow_score(sym: str, prices_desc: List[Dict]) -> Tuple[int, Dict]:
    detail = {"fgNet5d": None, "propNet5d": None, "fgNet5dZ": 0.0}
    if not prices_desc or len(prices_desc) < 5:
        return 0, detail

    fg_net_5d = sum(
        (p.get("buyForeignQuantity") or 0) - (p.get("sellForeignQuantity") or 0) for p in prices_desc[:5]
    )
    prop_net_5d = sum(p.get("propTradingNetValue") or 0 for p in prices_desc[:5])

    if len(prices_desc) >= 60:
        fg_vals = [
            (p.get("buyForeignQuantity") or 0) - (p.get("sellForeignQuantity") or 0)
            for p in prices_desc[:60]
        ]
        fg_mean = statistics.mean(fg_vals)
        fg_std = statistics.stdev(fg_vals) if len(fg_vals) > 1 else 1
        fg_z = (fg_net_5d - fg_mean * 5) / (fg_std * math.sqrt(5)) if fg_std != 0 else 0
    else:
        fg_z = 0.0

    detail.update({"fgNet5d": float(fg_net_5d), "propNet5d": float(prop_net_5d), "fgNet5dZ": round(fg_z, 2)})

    if fg_net_5d > 0 and prop_net_5d > 0:
        return 1, detail
    if fg_net_5d < 0 and prop_net_5d < 0:
        return -1, detail
    return 0, detail


def get_recommendation(total: int) -> str:
    if total >= 4:
        return "BUY_STRONG"
    if total >= 2:
        return "BUY"
    if total >= 0:
        return "HOLD"
    if total >= -2:
        return "AVOID"
    return "SELL"


def prices_as_of(quotes_asc: List[Dict], as_of: date) -> List[Dict]:
    """Filter to date <= as_of, return newest-first for scoring."""
    out: List[Dict] = []
    for rec in quotes_asc:
        ds = (rec.get("date") or "")[:10]
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if d <= as_of:
            out.append(rec)
    out.sort(key=lambda r: (r.get("date") or "")[:10], reverse=True)
    return out


def bar_on_date(quotes_asc: List[Dict], d: date) -> Optional[Dict]:
    key = d.isoformat()
    for rec in quotes_asc:
        if (rec.get("date") or "")[:10] == key:
            return rec
    return None


def forward_pnl_at_horizons(
    quotes_asc: List[Dict], signal_date: date
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Match production: open = first session strictly after signal_date (T+1 open).
    PnL at T+k uses close on the k-th trading day after signal_date (same indexing as calendar_service targets).
    Returns (open_t1, pnl_d3, pnl_d10, pnl_d20).
    """
    future: List[Dict] = []
    for rec in quotes_asc:
        ds = (rec.get("date") or "")[:10]
        try:
            rd = date.fromisoformat(ds)
        except ValueError:
            continue
        if rd > signal_date:
            future.append(rec)

    if not future:
        return None, None, None, None

    open_t1 = future[0].get("priceOpen")
    if open_t1 is None or open_t1 == 0:
        open_t1 = future[0].get("priceClose")
    if not open_t1 or open_t1 == 0:
        return None, None, None, None

    def pnl_for_k(k: int) -> Optional[float]:
        j = k - 1
        if j >= len(future):
            return None
        pc = future[j].get("priceClose")
        if pc is None or pc == 0:
            return None
        return (float(pc) / float(open_t1) - 1.0) * 100.0

    p3 = pnl_for_k(3)
    p10 = pnl_for_k(10)
    p20 = pnl_for_k(20)
    return float(open_t1), p3, p10, p20
