"""
Chỉ báo kỹ thuật cho Balanced — tham số chuẩn phổ biến:
- RSI(14) Wilder (giống backend/scripts/run_analysis.py)
- MACD(12,26,9) histogram (EMA)
- SMA 5 / 20
- ADX(14) Wilder
- Volume ratio: volume phiên mới nhất / SMA(volume, 20) phiên trước
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class BarCloseVol:
    close: float  # ascending date order: oldest → newest
    high: float
    low: float
    volume: float


def wilder_rsi(closes_desc: Sequence[float], period: int = 14) -> float:
    """closes_desc[0] = phiên mới nhất (giố run_analysis)."""
    prices = list(reversed(closes_desc))
    if len(prices) < period + 1:
        return 50.0
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 2)


def _ema_series(values: Sequence[float], span: int) -> list[float]:
    """values oldest first; return EMA same length."""
    if not values:
        return []
    k = 2.0 / (span + 1)
    out: list[float] = []
    ema = values[0]
    for v in values:
        ema = v * k + ema * (1 - k)
        out.append(ema)
    return out


def macd_histogram(closes_desc: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    closes_asc = list(reversed(closes_desc))
    if len(closes_asc) < slow + signal + 2:
        return 0.0
    ema_f = _ema_series(closes_asc, fast)
    ema_s = _ema_series(closes_asc, slow)
    macd_line = [f - s for f, s in zip(ema_f, ema_s)]
    sig = _ema_series(macd_line, signal)
    hist = macd_line[-1] - sig[-1]
    return round(hist, 6)


def sma(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def sma_on_desc(closes_desc: Sequence[float], window: int) -> float | None:
    asc = list(reversed(closes_desc))
    return sma(asc, window)


def volume_ratio(vol_desc: Sequence[float], window: int = 20) -> float | None:
    """vol_desc[0] = mới nhất; so với SMA(window) của các phiên cũ hơn."""
    if len(vol_desc) < window + 1:
        return None
    tail = list(reversed(vol_desc))  # oldest first
    base = tail[-(window + 1) : -1]
    if not base:
        return None
    avg = sum(base) / len(base)
    if avg <= 0:
        return None
    return round(float(vol_desc[0]) / avg, 4)


def adx14(high_desc: Sequence[float], low_desc: Sequence[float], close_desc: Sequence[float]) -> float:
    """ADX(14) Wilder — high/low/close cùng thứ tự desc (mới nhất trước)."""
    high = list(reversed(high_desc))
    low = list(reversed(low_desc))
    close = list(reversed(close_desc))
    period = 14
    if len(close) < period * 2 + 2:
        return 0.0
    trs: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for i in range(1, len(close)):
        h, l, c_prev = high[i], low[i], close[i - 1]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        p_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        m_dm = down_move if down_move > up_move and down_move > 0 else 0.0
        trs.append(tr)
        plus_dm.append(p_dm)
        minus_dm.append(m_dm)

    def wilder_smooth(seq: list[float]) -> list[float]:
        out = [sum(seq[:period]) / period]
        for i in range(period, len(seq)):
            out.append((out[-1] * (period - 1) + seq[i]) / period)
        return out

    atr = wilder_smooth(trs)
    p_di_s = wilder_smooth(plus_dm)
    m_di_s = wilder_smooth(minus_dm)
    dx_list: list[float] = []
    for i in range(len(atr)):
        if atr[i] <= 0:
            continue
        p_di = 100.0 * p_di_s[i] / atr[i]
        m_di = 100.0 * m_di_s[i] / atr[i]
        denom = p_di + m_di
        if denom == 0:
            continue
        dx_list.append(100.0 * abs(p_di - m_di) / denom)
    if len(dx_list) < period:
        return round(dx_list[-1], 2) if dx_list else 0.0
    adx_seq = wilder_smooth(dx_list)
    return round(adx_seq[-1], 2)


def compute_from_bars(bars_desc: list[BarCloseVol]) -> dict[str, float | None]:
    """bars_desc: index 0 = ngày mới nhất."""
    closes = [b.close for b in bars_desc]
    highs = [b.high for b in bars_desc]
    lows = [b.low for b in bars_desc]
    vols = [b.volume for b in bars_desc]
    s5 = sma_on_desc(closes, 5)
    s20 = sma_on_desc(closes, 20)
    ratio = s5 / s20 if s5 and s20 and s20 > 0 else None
    return {
        "rsi14": wilder_rsi(closes, 14),
        "macd_hist": macd_histogram(closes),
        "sma5": round(s5, 6) if s5 is not None else None,
        "sma20": round(s20, 6) if s20 is not None else None,
        "sma5_over_sma20": round(ratio, 6) if ratio is not None else None,
        "adx14": adx14(highs, lows, closes),
        "volume_ratio": volume_ratio(vols, 20),
    }
