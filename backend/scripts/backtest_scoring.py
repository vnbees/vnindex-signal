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
    """3-day mean-reversion: financial score not used (always 0)."""
    return 0, {"quarter": None, "lnstYoY": None, "salesYoY": None,
               "marginDelta": None, "earningsAccel": None}


def calc_seasonal_score(d: date) -> Tuple[int, Dict]:
    """Weekday effect from 3-day backtest (80k+ observations)."""
    dow = d.weekday()  # 0=Mon...4=Fri
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
    return score, {"month": d.month, "dayOfWeek": dow + 1, "reason": reason}


def calc_technical_score(sym: str, prices_desc: List[Dict]) -> Tuple[int, Dict]:
    """Mean-reversion strength score - main driver for 3-day strategy.
    prices_desc: newest first (same convention as Fireant API)."""
    detail = {"vsMa20": None, "rsi14": None, "bbPos": None, "ma20": None, "ma60": None,
              "consecutiveDown": 0, "dayReturn": None, "volRatio": None, "matchedStrategies": []}
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

    prev_close = closes[1] if len(closes) > 1 else close
    day_return = (close / prev_close - 1) * 100 if prev_close > 0 else 0

    vols = [p.get("dealVolume") or p.get("totalVolume") or 0 for p in prices_desc[:21]]
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
        for p in prices_desc[:5]
    )

    detail.update({
        "vsMa20": round(vs_ma20, 2),
        "rsi14": rsi14,
        "bbPos": round(bb_pos, 3),
        "ma20": round(ma20),
        "ma60": round(ma60),
        "consecutiveDown": consecutive_down,
        "dayReturn": round(day_return, 2),
        "volRatio": round(vol_ratio, 2),
        "matchedStrategies": [],
    })

    matched = []
    score = 0

    if rsi14 < 40 and vol_ratio > 2:
        score = -2
        matched.append("RSI<40 + Vol>2x (WR=43.7%)")
    elif bb_pos > 0.9:
        score = -1
        matched.append("BB>0.9 near upper (WR=45.3%)")
    elif consecutive_down >= 4 and rsi14 < 35:
        score = 3
        matched.append("4 down + RSI<35 (WR=59.5%)")
    elif consecutive_down >= 3 and rsi14 < 40:
        score = 2
        matched.append("3 down + RSI<40 (WR=56.7%)")
    elif vs_ma20 < -5 and fg_net_5d > 0:
        score = 2
        matched.append("Below MA20 >5% + NN buy (WR=56.4%)")
    elif day_return < -3 and fg_net_5d > 0:
        score = 2
        matched.append("Drop >3% + NN buy (WR=56.0%)")
    elif vs_ma20 < -5:
        score = 1
        matched.append("Below MA20 >5% (WR=55.6%)")
    elif day_return < -5:
        score = 1
        matched.append("Drop >5% (WR=55.1%)")
    elif day_return < -3:
        score = 1
        matched.append("Drop >3% (WR=54.8%)")
    elif rsi14 < 30:
        score = 1
        matched.append("RSI<30 oversold (WR=54.0%)")

    detail["matchedStrategies"] = matched
    return score, detail


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
    if total >= -1:
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
