#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Walk-forward backtest: same TC/SS/KT/DT rules as run_analysis.py (see backtest_scoring.py).

Universe (no top-30 cap rank): from CANDIDATES with snapshot market cap >= --min-market-cap-bil (tỷ VND),
trailing avg totalVolume >= --min-avg-volume over --liquidity-window sessions ending at signal date,
and close <= --max-price (nghìn VND).

Does NOT modify run_analysis.py or production APIs.

Data:
  - Fireant historical-quotes (wide startDate, high limit)
  - Optional CafeF PriceHistory.ashx for older bars (GiaDieuChinh), merged: Fireant wins on same date.

Usage:
  set FIREANT_TOKEN env (same as run_analysis), then:
  python backend/scripts/run_backtest.py --start 2015-01-01 --end 2025-12-31

Defaults: --min-market-cap-bil 8000, --min-avg-volume 300000, --liquidity-window 60, --max-price 30
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _bar_date(rec: Dict) -> Optional[date]:
    ds = (rec.get("date") or "")[:10]
    try:
        return date.fromisoformat(ds)
    except ValueError:
        return None


def trailing_avg_volume(quotes_asc: List[Dict], as_of: date, window: int) -> Optional[float]:
    """Mean totalVolume over last `window` sessions with date <= as_of (no lookahead)."""
    eligible: List[Dict] = []
    for rec in quotes_asc:
        rd = _bar_date(rec)
        if rd is None or rd > as_of:
            continue
        eligible.append(rec)
    if len(eligible) < window:
        return None
    tail = eligible[-window:]
    vs = [float(r.get("totalVolume") or 0) for r in tail]
    if not vs:
        return None
    return sum(vs) / len(vs)


import httpx

# Local imports (script dir)
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from backtest_scoring import (
    bar_on_date,
    calc_cashflow_score,
    calc_financial_score,
    calc_seasonal_score,
    calc_technical_score,
    forward_pnl_at_horizons,
    get_recommendation,
    prices_as_of,
)

FIREANT_BASE = "https://restv2.fireant.vn"
CAFEF_URL = "https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx"

CANDIDATES = [
    "VCB", "BID", "CTG", "TCB", "MBB", "VIC", "VHM", "VRE", "HPG", "NVL", "MSN", "MWG",
    "FPT", "VNM", "GAS", "PLX", "POW", "VJC", "HVN",
    "ACB", "STB", "VPB", "HDB", "LPB", "SSB", "SHB", "OCB", "TPB", "EIB", "MSB",
    "SSI", "VND", "HCM", "MBS", "VCI", "BSI", "AGR",
    "REE", "PNJ", "DGC", "DPM", "DCM", "PHR", "VHC", "CSV", "BSR",
    "SAB", "BHN", "MCH", "QNS", "VEA", "PAN", "BAF", "HNG", "HAG",
    "BCM", "KDH", "NLG", "DXG", "PDR", "DIG", "CEO", "SCR", "VPI", "KBC", "IDC", "SZC", "SIP",
    "PVS", "PVD", "PVT", "OIL", "GEE",
    "GMD", "VSC", "HAH", "DVP", "STG", "VTO",
    "VGC", "LHG", "HII",
    "NT2", "PGV", "HND", "EVG",
    "EVF", "CTD", "GEG",
]


def normalize_price_to_fireant_thousands(p: Optional[float]) -> float:
    """CafeF often uses full VND; Fireant uses nghìn. Heuristic: large values -> divide by 1000."""
    if p is None:
        return 0.0
    try:
        x = float(p)
    except (TypeError, ValueError):
        return 0.0
    if x > 2500:
        return x / 1000.0
    return x


def parse_cafef_date(s: Any) -> Optional[date]:
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    if "/" in t[:11]:
        for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(t[:10], fmt).date()
            except ValueError:
                continue
    if len(t) >= 10:
        try:
            return date.fromisoformat(t[:10])
        except ValueError:
            pass
    return None


def cafef_row_to_bar(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map one CafeF row to Fireant-like bar."""
    keys = {k.lower(): k for k in row.keys()} if isinstance(row, dict) else {}

    def pick(*names):
        for n in names:
            for cand in (n, n.lower(), n.upper()):
                if isinstance(row, dict) and cand in row:
                    return row[cand]
                lk = cand.lower()
                if lk in keys:
                    return row[keys[lk]]
        return None

    d_raw = pick("Ngay", "Date", "TradingDate", "date")
    d = parse_cafef_date(d_raw)
    if not d:
        return None

    adj = pick("GiaDieuChinh", "GiaDongCua", "ClosePrice", "priceClose", "Close")
    op = pick("GiaMoCua", "OpenPrice", "priceOpen", "Open")
    hi = pick("GiaCaoNhat", "HighPrice", "priceHigh", "High")
    lo = pick("GiaThapNhat", "LowPrice", "priceLow", "Low")

    pc = normalize_price_to_fireant_thousands(float(adj) if adj is not None else 0)
    po = normalize_price_to_fireant_thousands(float(op) if op is not None else pc)
    ph = normalize_price_to_fireant_thousands(float(hi) if hi is not None else pc)
    pl = normalize_price_to_fireant_thousands(float(lo) if lo is not None else pc)

    if pc <= 0:
        return None

    return {
        "date": d.isoformat() + "T00:00:00",
        "priceOpen": po or pc,
        "priceClose": pc,
        "priceHigh": ph or pc,
        "priceLow": pl or pc,
        "totalVolume": float(pick("KhoiLuongKhopLenh", "Volume", "KL") or 0) or 0.0,
        "buyForeignQuantity": 0.0,
        "sellForeignQuantity": 0.0,
        "propTradingNetValue": 0.0,
    }


def parse_cafef_payload(text: str) -> List[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        if isinstance(data.get("d"), str):
            try:
                inner = json.loads(data["d"])
                return parse_cafef_payload(json.dumps(inner))
            except json.JSONDecodeError:
                pass
        for key in ("Data", "data", "Rows", "rows", "Result"):
            chunk = data.get(key)
            if isinstance(chunk, list):
                return [x for x in chunk if isinstance(x, dict)]
            if isinstance(chunk, dict) and "Data" in chunk:
                return parse_cafef_payload(json.dumps(chunk))
    return []


async def fetch_cafef_history(
    client: httpx.AsyncClient, sym: str, start: date, end: date
) -> List[Dict[str, Any]]:
    params = {
        "Symbol": sym,
        "StartDate": start.strftime("%d/%m/%Y"),
        "EndDate": end.strftime("%d/%m/%Y"),
        "PageIndex": 1,
        "PageSize": 5000,
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; vnindex-signal-backtest/1.0)"}
    try:
        r = await client.get(CAFEF_URL, params=params, headers=headers, timeout=60)
        if r.status_code != 200:
            return []
        rows = parse_cafef_payload(r.text)
        bars = []
        for row in rows:
            b = cafef_row_to_bar(row)
            if b:
                bars.append(b)
        return bars
    except Exception:
        return []


async def fetch_fireant_quotes(
    client: httpx.AsyncClient,
    headers: Dict[str, str],
    sym: str,
    start: date,
    end: date,
    limit: int,
) -> List[Dict]:
    try:
        r = await client.get(
            f"{FIREANT_BASE}/symbols/{sym}/historical-quotes",
            params={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "limit": limit,
            },
            headers=headers,
            timeout=45,
        )
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


async def fetch_fireant_financial(
    client: httpx.AsyncClient, headers: Dict[str, str], sym: str, limit: int
) -> Optional[Dict]:
    try:
        r = await client.get(
            f"{FIREANT_BASE}/symbols/{sym}/financial-reports",
            params={"limit": limit, "type": 1},
            headers=headers,
            timeout=45,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "rows" in data:
                return data
    except Exception:
        pass
    return None


async def fetch_fundamental(
    client: httpx.AsyncClient, headers: Dict[str, str], sym: str
) -> Optional[Dict]:
    try:
        r = await client.get(
            f"{FIREANT_BASE}/symbols/{sym}/fundamental",
            headers=headers,
            timeout=20,
        )
        if r.status_code == 200:
            d = r.json()
            mc = d.get("marketCap", 0)
            if mc and mc > 0:
                return {"sym": sym, "marketCap": float(mc)}
    except Exception:
        pass
    return None


def merge_quotes(fireant: List[Dict], cafef: List[Dict]) -> List[Dict]:
    """Ascending by date. Same calendar day: Fireant overwrites CafeF. _fa marks Fireant-sourced row."""
    by_day: Dict[str, Dict] = {}
    for rec in cafef:
        day = (rec.get("date") or "")[:10]
        if day:
            r = dict(rec)
            r["_fa"] = False
            by_day[day] = r
    for rec in fireant:
        day = (rec.get("date") or "")[:10]
        if day:
            r = dict(rec)
            r["_fa"] = True
            by_day[day] = r
    return [by_day[d] for d in sorted(by_day.keys())]


def forward_fill_prop_from_fireant(merged_asc: List[Dict]) -> List[Dict]:
    """
    CafeF-only rows get propTradingNetValue = last value seen on a prior Fireant row
    (same symbol, time ascending). No lookahead. Rows before the first Fireant bar stay 0.
    """
    last_prop: Optional[float] = None
    out: List[Dict] = []
    for rec in merged_asc:
        r = dict(rec)
        is_fa = bool(r.pop("_fa", False))
        if is_fa:
            last_prop = float(r.get("propTradingNetValue") or 0)
            out.append(r)
        else:
            if last_prop is not None:
                r["propTradingNetValue"] = last_prop
            out.append(r)
    return out


def trading_days_union(merged_by_sym: Dict[str, List[Dict]], start: date, end: date, step: int) -> List[date]:
    seen = set()
    for bars in merged_by_sym.values():
        for rec in bars:
            ds = (rec.get("date") or "")[:10]
            try:
                d = date.fromisoformat(ds)
            except ValueError:
                continue
            if start <= d <= end:
                seen.add(d)
    days = sorted(seen)
    if step <= 1:
        return days
    return days[::step]


async def load_universe_data(
    syms: List[str],
    token: str,
    start: date,
    end: date,
    fin_limit: int,
    quote_limit: int,
    use_cafef: bool,
) -> Tuple[Dict[str, List[Dict]], Dict[str, Optional[Dict]]]:
    fa_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    price_data: Dict[str, List[Dict]] = {}
    fin_data: Dict[str, Optional[Dict]] = {}

    limits = httpx.Limits(max_connections=30, max_keepalive_connections=15)
    async with httpx.AsyncClient(limits=limits) as client:

        async def one(sym: str):
            fq, fi = await asyncio.gather(
                fetch_fireant_quotes(client, fa_headers, sym, start, end, quote_limit),
                fetch_fireant_financial(client, fa_headers, sym, fin_limit),
            )
            cf = await fetch_cafef_history(client, sym, start, end) if use_cafef else []
            merged = merge_quotes(fq, cf)
            merged = forward_fill_prop_from_fireant(merged)
            return sym, merged, fi

        results = await asyncio.gather(*[one(s) for s in syms])
        for sym, merged, fi in results:
            price_data[sym] = merged
            fin_data[sym] = fi

    return price_data, fin_data


def _float_cell(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize(rows: List[Dict]) -> None:
    by_rec3 = defaultdict(list)
    by_rec10 = defaultdict(list)
    by_rec20 = defaultdict(list)
    for r in rows:
        recn = r["recommendation"]
        for bucket, key in ((by_rec3, "pnl_d3"), (by_rec10, "pnl_d10"), (by_rec20, "pnl_d20")):
            v = _float_cell(r.get(key))
            if v is not None:
                bucket[recn].append(v)

    def print_block(title: str, by_rec: dict) -> None:
        print(title)
        for rec in sorted(by_rec.keys()):
            xs = by_rec[rec]
            if not xs:
                continue
            wr = sum(1 for v in xs if v > 0) / len(xs)
            avg = sum(xs) / len(xs)
            print(f"  {rec}: n={len(xs)}  win%={wr*100:.1f}  avg={avg:.3f}%")

    print("\n=== Summary by recommendation (rows with valid PnL) ===")
    print_block("--- T+3 ---", by_rec3)
    print_block("--- T+10 ---", by_rec10)
    print_block("--- T+20 ---", by_rec20)

    all3 = [v for r in rows for v in [_float_cell(r.get("pnl_d3"))] if v is not None]
    if all3:
        print(
            f"\n=== All rows T+3: n={len(all3)}  win%={100*sum(1 for v in all3 if v>0)/len(all3):.1f}  avg={sum(all3)/len(all3):.3f}%"
        )


async def async_main(args) -> None:
    token = os.environ.get("FIREANT_TOKEN", "").strip()
    if not token:
        print("Set FIREANT_TOKEN in the environment (same token as run_analysis.py).", file=sys.stderr)
        sys.exit(1)

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if start > end:
        print("--start must be <= --end", file=sys.stderr)
        sys.exit(1)

    pool = CANDIDATES[: args.symbols] if args.symbols > 0 else list(CANDIDATES)

    fa_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        futs = await asyncio.gather(*[fetch_fundamental(client, fa_headers, s) for s in pool])
    valid = [f for f in futs if f]
    mc_map = {x["sym"]: x["marketCap"] for x in valid}

    min_mc_vnd = float(args.min_market_cap_bil) * 1e9
    syms = sorted(
        [x["sym"] for x in valid if x["marketCap"] >= min_mc_vnd],
        key=lambda s: mc_map.get(s, 0),
        reverse=True,
    )
    if args.max_symbols > 0:
        syms = syms[: args.max_symbols]

    if not syms:
        print(
            f"No symbols pass min market cap >= {args.min_market_cap_bil} bil VND (snapshot).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Universe: {len(syms)} symbols | snapshot MC >= {args.min_market_cap_bil} bil VND | "
        f"liquidity: avg volume >= {args.min_avg_volume:,.0f} over {args.liquidity_window} sessions | "
        f"close <= {args.max_price} (k VND)"
    )
    print(f"Symbols: {', '.join(syms)}")

    price_data, fin_data = await load_universe_data(
        syms,
        token,
        start,
        end,
        args.fin_limit,
        args.quote_limit,
        args.use_cafef,
    )

    signal_days = trading_days_union(price_data, start, end, args.step)
    print(f"Signal days in range (step={args.step}): {len(signal_days)}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "run_date",
        "symbol",
        "price_close",
        "market_cap_bil",
        "avg_volume_liq",
        "score_financial",
        "score_seasonal",
        "score_technical",
        "score_cashflow",
        "score_total",
        "recommendation",
        "open_t1",
        "pnl_d3",
        "pnl_d10",
        "pnl_d20",
    ]

    rows_out: List[Dict] = []

    for d in signal_days:
        score_ss, _ = calc_seasonal_score(d)
        for sym in syms:
            qasc = price_data.get(sym) or []
            bar = bar_on_date(qasc, d)
            if not bar:
                continue
            pc = bar.get("priceClose") or 0
            if pc <= 0 or float(pc) > float(args.max_price):
                continue

            pdesc = prices_as_of(qasc, d)
            if len(pdesc) < 60:
                continue

            avg_vol = trailing_avg_volume(qasc, d, args.liquidity_window)
            if avg_vol is None or avg_vol < float(args.min_avg_volume):
                continue

            fin = fin_data.get(sym)
            score_tc, _ = calc_financial_score(sym, fin, d)
            score_kt, _ = calc_technical_score(sym, pdesc)
            score_dt, _ = calc_cashflow_score(sym, pdesc)
            total = score_tc + score_ss + score_kt + score_dt
            rec = get_recommendation(total)

            o1, p3, p10, p20 = forward_pnl_at_horizons(qasc, d)

            mc = mc_map.get(sym, 0) / 1e9
            rows_out.append(
                {
                    "run_date": d.isoformat(),
                    "symbol": sym,
                    "price_close": round(float(pc), 4),
                    "market_cap_bil": round(mc, 2),
                    "avg_volume_liq": round(avg_vol, 2),
                    "score_financial": score_tc,
                    "score_seasonal": score_ss,
                    "score_technical": score_kt,
                    "score_cashflow": score_dt,
                    "score_total": total,
                    "recommendation": rec,
                    "open_t1": f"{o1:.6f}" if o1 is not None else "",
                    "pnl_d3": f"{p3:.4f}" if p3 is not None else "",
                    "pnl_d10": f"{p10:.4f}" if p10 is not None else "",
                    "pnl_d20": f"{p20:.4f}" if p20 is not None else "",
                }
            )

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows_out:
            w.writerow(row)

    print(f"Wrote {len(rows_out)} rows -> {out_path}")
    summarize(rows_out)


def build_argparser():
    p = argparse.ArgumentParser(description="Walk-forward backtest (price-filtered universe).")
    p.add_argument("--start", default="2015-01-01", help="First signal date (ISO)")
    p.add_argument("--end", default="2025-12-31", help="Last signal date (ISO)")
    p.add_argument("--step", type=int, default=1, help="Use every Nth trading day (1=all)")
    p.add_argument("--max-price", type=float, default=30.0, help="Max close in nghìn VND (default 30 = 30k/cp)")
    p.add_argument(
        "--min-market-cap-bil",
        type=float,
        default=8000.0,
        help="Minimum market cap snapshot (bil VND = Fireant marketCap/1e9)",
    )
    p.add_argument(
        "--min-avg-volume",
        type=float,
        default=300_000.0,
        help="Minimum trailing mean totalVolume (cổ phiên/phiên) over --liquidity-window",
    )
    p.add_argument(
        "--liquidity-window",
        type=int,
        default=60,
        help="Sessions for liquidity average (must have >=60 bars anyway for scoring)",
    )
    p.add_argument(
        "--max-symbols",
        type=int,
        default=0,
        help="Optional cap on number of symbols after MC filter (0 = no cap)",
    )
    p.add_argument("--symbols", type=int, default=0, help="If >0, only first N CANDIDATES (debug)")
    p.add_argument("--fin-limit", type=int, default=100, help="Fireant financial-reports limit")
    p.add_argument("--quote-limit", type=int, default=5000, help="Fireant historical-quotes limit")
    p.add_argument("--no-cafef", action="store_true", help="Disable CafeF merge (Fireant only)")
    p.add_argument(
        "--output",
        default=str(_SCRIPT_DIR / "backtest_output.csv"),
        help="Output CSV path",
    )
    return p


if __name__ == "__main__":
    args = build_argparser().parse_args()
    args.use_cafef = not args.no_cafef
    asyncio.run(async_main(args))
