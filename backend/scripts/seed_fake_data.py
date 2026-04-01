#!/usr/bin/env python3
"""
Seed fake data for local development/testing.
Creates analysis runs with signals and price tracking data for the past 60 days.
"""
import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from config import settings
from models.signal import Signal, AnalysisRun
from models.price_tracking import PriceTracking
from database import Base

# Top 30 HOSE stocks
SYMBOLS = [
    "VCB", "BID", "CTG", "TCB", "MBB", "VIC", "VHM", "HPG", "MSN", "MWG",
    "FPT", "VNM", "GAS", "PLX", "VJC", "ACB", "STB", "VPB", "SSI", "VND",
    "REE", "PNJ", "SAB", "BCM", "KDH", "GMD", "HDB", "LPB", "NVL", "VRE",
]

RECOMMENDATIONS = ["BUY_STRONG", "BUY", "HOLD", "AVOID", "SELL"]
REC_WEIGHTS     = [0.15,         0.30, 0.30,  0.15,    0.10]

# Approximate price ranges (VND)
PRICE_RANGES = {
    "VCB": (80000, 110000), "BID": (40000, 60000), "CTG": (28000, 42000),
    "TCB": (18000, 30000),  "MBB": (18000, 28000), "VIC": (40000, 75000),
    "VHM": (35000, 65000),  "HPG": (22000, 38000), "MSN": (55000, 90000),
    "MWG": (40000, 80000),  "FPT": (85000, 140000),"VNM": (55000, 85000),
    "GAS": (60000, 100000), "PLX": (38000, 58000),  "VJC": (95000, 145000),
    "ACB": (22000, 35000),  "STB": (20000, 32000),  "VPB": (15000, 25000),
    "SSI": (18000, 32000),  "VND": (15000, 28000),  "REE": (45000, 75000),
    "PNJ": (70000, 120000), "SAB": (150000, 220000),"BCM": (35000, 58000),
    "KDH": (22000, 38000),  "GMD": (38000, 65000),  "HDB": (18000, 30000),
    "LPB": (12000, 22000),  "NVL": (8000, 18000),   "VRE": (25000, 42000),
}

MARKET_CAPS = {
    "VCB": 420000, "BID": 280000, "CTG": 240000, "TCB": 180000, "MBB": 160000,
    "VIC": 300000, "VHM": 180000, "HPG": 160000, "MSN": 120000, "MWG": 80000,
    "FPT": 140000, "VNM": 110000, "GAS": 150000, "PLX": 80000,  "VJC": 90000,
    "ACB": 100000, "STB": 70000,  "VPB": 90000,  "SSI": 45000,  "VND": 30000,
    "REE": 35000,  "PNJ": 40000,  "SAB": 80000,  "BCM": 60000,  "KDH": 30000,
    "GMD": 25000,  "HDB": 55000,  "LPB": 40000,  "NVL": 20000,  "VRE": 55000,
}


def is_trading_day(d: date) -> bool:
    """Simple check: Mon-Fri, exclude known holidays."""
    HOLIDAYS_2026 = {
        date(2026, 1, 1), date(2026, 2, 17), date(2026, 2, 18),
        date(2026, 2, 19), date(2026, 2, 20), date(2026, 2, 23),
        date(2026, 4, 16), date(2026, 4, 30), date(2026, 5, 1),
        date(2026, 9, 2),
    }
    if d.weekday() >= 5:
        return False
    if d in HOLIDAYS_2026:
        return False
    return True


def get_trading_days(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        if is_trading_day(current):
            days.append(current)
        current += timedelta(days=1)
    return days


def fake_price(symbol: str, base_price=None) -> float:
    lo, hi = PRICE_RANGES.get(symbol, (20000, 80000))
    if base_price:
        # random walk ±3%
        change = random.uniform(-0.03, 0.03)
        price = base_price * (1 + change)
        price = max(lo * 0.8, min(hi * 1.2, price))
    else:
        price = random.uniform(lo, hi)
    return round(price / 100) * 100  # round to nearest 100 VND


def fake_scores(rec: str) -> dict:
    """Generate plausible scores for a given recommendation."""
    score_map = {
        "BUY_STRONG": (7, 10),
        "BUY":        (5, 8),
        "HOLD":       (4, 6),
        "AVOID":      (2, 5),
        "SELL":       (0, 3),
    }
    lo, hi = score_map[rec]
    sf = random.randint(lo, hi)
    ss = random.randint(lo, hi)
    st = random.randint(lo, hi)
    sc = random.randint(lo, hi)
    total = sf + ss + st + sc
    return dict(score_financial=sf, score_seasonal=ss, score_technical=st,
                score_cashflow=sc, score_total=total)


def fake_detail_financial(symbol: str) -> dict:
    return {
        "pe_ratio": round(random.uniform(5, 25), 1),
        "pb_ratio": round(random.uniform(0.5, 4), 2),
        "roe": round(random.uniform(0.05, 0.30), 3),
        "revenue_growth_yoy": round(random.uniform(-0.1, 0.4), 3),
        "net_profit_margin": round(random.uniform(0.05, 0.25), 3),
        "debt_to_equity": round(random.uniform(0.1, 2.5), 2),
        "eps": round(random.uniform(500, 8000)),
    }


def fake_detail_technical(price: float) -> dict:
    ma20 = price * random.uniform(0.95, 1.05)
    ma50 = price * random.uniform(0.90, 1.10)
    return {
        "rsi_14": round(random.uniform(25, 75), 1),
        "macd": round(random.uniform(-500, 500), 0),
        "macd_signal": round(random.uniform(-400, 400), 0),
        "ma20": round(ma20 / 100) * 100,
        "ma50": round(ma50 / 100) * 100,
        "volume_ratio": round(random.uniform(0.5, 2.5), 2),
        "bb_upper": round(price * 1.05 / 100) * 100,
        "bb_lower": round(price * 0.95 / 100) * 100,
    }


def fake_detail_cashflow() -> dict:
    return {
        "operating_cf_growth": round(random.uniform(-0.2, 0.5), 3),
        "free_cash_flow_bil": round(random.uniform(-500, 5000)),
        "fcf_yield": round(random.uniform(0.01, 0.10), 3),
        "capex_to_revenue": round(random.uniform(0.02, 0.15), 3),
    }


def fake_detail_seasonal(symbol: str) -> dict:
    month = date.today().month
    return {
        "seasonal_score_hist": random.randint(3, 9),
        "month": month,
        "avg_return_this_month": round(random.uniform(-0.03, 0.06), 4),
        "win_rate_this_month": round(random.uniform(0.4, 0.75), 2),
    }


async def seed_fake_data(num_days: int = 30, symbols_per_run: int = 20):
    """
    Seed fake analysis runs for the last `num_days` trading days.
    Each run picks `symbols_per_run` random symbols.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    today = date.today()
    start = today - timedelta(days=90)  # look back 90 calendar days to get ~60 trading days
    trading_days = get_trading_days(start, today)
    run_dates = trading_days[-num_days:]  # last N trading days

    print(f"Seeding {len(run_dates)} analysis runs ({run_dates[0]} → {run_dates[-1]})")

    # Base prices — will random-walk across dates
    base_prices: dict[str, float] = {sym: fake_price(sym) for sym in SYMBOLS}

    async with AsyncSession() as session:
        for run_date in run_dates:
            # Check if run already exists
            existing = await session.execute(
                select(AnalysisRun).where(
                    AnalysisRun.run_date == run_date,
                    AnalysisRun.portfolio_kind == "top_cap",
                )
            )
            if existing.scalar_one_or_none():
                print(f"  {run_date}: already exists, skipping")
                continue

            symbols = random.sample(SYMBOLS, k=symbols_per_run)
            run = AnalysisRun(
                run_date=run_date,
                portfolio_kind="top_cap",
                top_n=symbols_per_run,
                hold_days=20,
            )
            session.add(run)
            await session.flush()  # get run.id

            for sym in symbols:
                rec = random.choices(RECOMMENDATIONS, weights=REC_WEIGHTS, k=1)[0]
                scores = fake_scores(rec)
                # signal_type: BUY→"LONG", SELL→"SHORT", else "NEUTRAL"
                if rec in ("BUY_STRONG", "BUY"):
                    signal_type = "LONG"
                elif rec == "SELL":
                    signal_type = "SHORT"
                else:
                    signal_type = "NEUTRAL"

                price_close = fake_price(sym, base_prices[sym])
                base_prices[sym] = price_close  # update for next day

                signal = Signal(
                    run_id=run.id,
                    run_date=run_date,
                    symbol=sym,
                    status="active",
                    recommendation=rec,
                    signal_type=signal_type,
                    price_close_signal_date=Decimal(str(price_close)),
                    price_open_t1=Decimal(str(fake_price(sym, price_close))),
                    market_cap_bil=Decimal(str(MARKET_CAPS.get(sym, 50000))),
                    has_corporate_action=random.random() < 0.05,
                    detail_financial=fake_detail_financial(sym),
                    detail_technical=fake_detail_technical(price_close),
                    detail_cashflow=fake_detail_cashflow(),
                    detail_seasonal=fake_detail_seasonal(sym),
                    **scores,
                )
                session.add(signal)
                await session.flush()  # get signal.id

                # Seed price tracking for completed periods
                # Find trading days after signal date that have passed
                future_trading = get_trading_days(
                    run_date + timedelta(days=1),
                    today
                )
                tracking_price = price_close
                for days_idx, track_date in enumerate(future_trading[:20], start=1):
                    tracking_price = fake_price(sym, tracking_price)
                    pnl_pct = (tracking_price - price_close) / price_close * 100
                    pt = PriceTracking(
                        signal_id=signal.id,
                        run_date=run_date,
                        symbol=sym,
                        track_date=track_date,
                        days_after=days_idx,
                        price_close=Decimal(str(tracking_price)),
                        pnl_pct=Decimal(str(round(pnl_pct, 4))),
                    )
                    session.add(pt)

            await session.commit()
            print(f"  {run_date}: {len(symbols)} signals seeded ✓")

    # Refresh materialized view
    async with engine.connect() as conn:
        await conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY signal_pnl_summary"))
        await conn.commit()
    print("Materialized view refreshed ✓")

    await engine.dispose()
    print("\nDone! Fake data seeded successfully.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed fake data for local dev")
    parser.add_argument("--days", type=int, default=30, help="Number of trading days to seed (default: 30)")
    parser.add_argument("--symbols", type=int, default=20, help="Symbols per run (default: 20)")
    args = parser.parse_args()
    asyncio.run(seed_fake_data(num_days=args.days, symbols_per_run=args.symbols))
