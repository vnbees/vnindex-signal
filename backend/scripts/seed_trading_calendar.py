#!/usr/bin/env python3
"""
Seed trading_calendar with all days from 2015 to 2027.
Convention: ALL days are seeded. is_trading=FALSE for weekends and Vietnamese public holidays.
Trading days are Monday-Friday excluding public holidays.
"""
import asyncio
from datetime import date, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert
from config import settings
from models.trading_calendar import TradingCalendar
from database import Base

# Vietnamese public holidays (approximate - fixed dates, lunar holidays vary)
# Format: (month, day) - recurring yearly
FIXED_HOLIDAYS = [
    (1, 1),   # New Year's Day
    (4, 30),  # Reunification Day
    (5, 1),   # Labor Day
    (9, 2),   # National Day
]

# Specific holiday dates (including Lunar New Year - Tet, etc.)
# These need to be maintained yearly
SPECIFIC_HOLIDAYS = {
    # 2015
    date(2015, 2, 18): "Tet Eve",
    date(2015, 2, 19): "Tet Day 1",
    date(2015, 2, 20): "Tet Day 2",
    date(2015, 2, 21): "Tet Day 3",
    date(2015, 2, 22): "Tet Day 4",
    date(2015, 2, 23): "Tet Day 5",
    date(2015, 4, 2): "Hung Kings Festival",
    # 2016
    date(2016, 2, 7): "Tet Eve",
    date(2016, 2, 8): "Tet Day 1",
    date(2016, 2, 9): "Tet Day 2",
    date(2016, 2, 10): "Tet Day 3",
    date(2016, 2, 11): "Tet Day 4",
    date(2016, 2, 12): "Tet Day 5",
    date(2016, 4, 16): "Hung Kings Festival",
    # 2017
    date(2017, 1, 26): "Tet Eve",
    date(2017, 1, 27): "Tet Day 1",
    date(2017, 1, 28): "Tet Day 2",
    date(2017, 1, 29): "Tet Day 3",
    date(2017, 1, 30): "Tet Day 4",
    date(2017, 1, 31): "Tet Day 5",
    date(2017, 4, 6): "Hung Kings Festival",
    # 2018
    date(2018, 2, 14): "Tet Eve",
    date(2018, 2, 15): "Tet Day 1",
    date(2018, 2, 16): "Tet Day 2",
    date(2018, 2, 17): "Tet Day 3",
    date(2018, 2, 18): "Tet Day 4",
    date(2018, 2, 19): "Tet Day 5",
    date(2018, 4, 25): "Hung Kings Festival",
    # 2019
    date(2019, 2, 4): "Tet Eve",
    date(2019, 2, 5): "Tet Day 1",
    date(2019, 2, 6): "Tet Day 2",
    date(2019, 2, 7): "Tet Day 3",
    date(2019, 2, 8): "Tet Day 4",
    date(2019, 2, 9): "Tet Day 5",
    date(2019, 4, 14): "Hung Kings Festival",
    # 2020
    date(2020, 1, 23): "Tet Eve",
    date(2020, 1, 24): "Tet Day 1",
    date(2020, 1, 25): "Tet Day 2",
    date(2020, 1, 26): "Tet Day 3",
    date(2020, 1, 27): "Tet Day 4",
    date(2020, 1, 28): "Tet Day 5",
    date(2020, 4, 2): "Hung Kings Festival",
    # 2021
    date(2021, 2, 10): "Tet Eve",
    date(2021, 2, 11): "Tet Day 1",
    date(2021, 2, 12): "Tet Day 2",
    date(2021, 2, 13): "Tet Day 3",
    date(2021, 2, 14): "Tet Day 4",
    date(2021, 2, 15): "Tet Day 5",
    date(2021, 4, 21): "Hung Kings Festival",
    # 2022
    date(2022, 1, 29): "Tet Eve",
    date(2022, 1, 30): "Tet Day 1",
    date(2022, 1, 31): "Tet Day 2",
    date(2022, 2, 1): "Tet Day 3",
    date(2022, 2, 2): "Tet Day 4",
    date(2022, 2, 3): "Tet Day 5",
    date(2022, 4, 10): "Hung Kings Festival",
    # 2023
    date(2023, 1, 20): "Tet Eve",
    date(2023, 1, 21): "Tet Day 1",
    date(2023, 1, 22): "Tet Day 2",
    date(2023, 1, 23): "Tet Day 3",
    date(2023, 1, 24): "Tet Day 4",
    date(2023, 1, 25): "Tet Day 5",
    date(2023, 4, 29): "Hung Kings Festival",
    # 2024
    date(2024, 2, 8): "Tet Eve",
    date(2024, 2, 9): "Tet Day 1",
    date(2024, 2, 10): "Tet Day 2",
    date(2024, 2, 11): "Tet Day 3",
    date(2024, 2, 12): "Tet Day 4",
    date(2024, 2, 13): "Tet Day 5",
    date(2024, 4, 18): "Hung Kings Festival",
    # 2025
    date(2025, 1, 27): "Tet Eve",
    date(2025, 1, 28): "Tet Day 1",
    date(2025, 1, 29): "Tet Day 2",
    date(2025, 1, 30): "Tet Day 3",
    date(2025, 1, 31): "Tet Day 4",
    date(2025, 2, 3): "Tet Day 5",
    date(2025, 4, 7): "Hung Kings Festival",
    # 2026
    date(2026, 2, 16): "Tet Eve",
    date(2026, 2, 17): "Tet Day 1",
    date(2026, 2, 18): "Tet Day 2",
    date(2026, 2, 19): "Tet Day 3",
    date(2026, 2, 20): "Tet Day 4",
    date(2026, 2, 23): "Tet Day 5",
    date(2026, 4, 16): "Hung Kings Festival",
    # 2027
    date(2027, 2, 5): "Tet Eve",
    date(2027, 2, 6): "Tet Day 1",
    date(2027, 2, 7): "Tet Day 2",
    date(2027, 2, 8): "Tet Day 3",
    date(2027, 2, 9): "Tet Day 4",
    date(2027, 2, 10): "Tet Day 5",
    date(2027, 4, 6): "Hung Kings Festival",
}

def is_fixed_holiday(d: date) -> bool:
    return (d.month, d.day) in FIXED_HOLIDAYS

async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    start = date(2015, 1, 1)
    end = date(2027, 12, 31)

    rows = []
    current = start
    while current <= end:
        is_weekend = current.weekday() >= 5  # Saturday=5, Sunday=6
        is_holiday = is_fixed_holiday(current) or current in SPECIFIC_HOLIDAYS
        is_trading = not (is_weekend or is_holiday)

        note = None
        if is_weekend:
            note = "Weekend"
        elif current in SPECIFIC_HOLIDAYS:
            note = SPECIFIC_HOLIDAYS[current]
        elif is_fixed_holiday(current):
            note = "Public Holiday"

        rows.append({
            "trade_date": current,
            "is_trading": is_trading,
            "note": note
        })
        current += timedelta(days=1)

    async with AsyncSession() as session:
        # Batch insert with upsert
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            stmt = pg_insert(TradingCalendar).values(batch).on_conflict_do_update(
                index_elements=['trade_date'],
                set_={"is_trading": pg_insert(TradingCalendar).excluded.is_trading,
                      "note": pg_insert(TradingCalendar).excluded.note}
            )
            await session.execute(stmt)
        await session.commit()
        print(f"Seeded {len(rows)} days from {start} to {end}")
        trading_count = sum(1 for r in rows if r["is_trading"])
        print(f"Trading days: {trading_count}, Non-trading: {len(rows) - trading_count}")

    await engine.dispose()

async def generate_api_key(label: str = "default"):
    """Generate a new API key and store bcrypt hash."""
    import bcrypt
    import secrets

    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    from models.signal import ApiKey

    raw_key = secrets.token_urlsafe(32)
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt(rounds=12)).decode()

    async with AsyncSession() as session:
        api_key = ApiKey(key_hash=key_hash, label=label, is_active=True)
        session.add(api_key)
        await session.commit()
        print(f"API Key created:")
        print(f"  Label: {label}")
        print(f"  Raw key (save this!): {raw_key}")
        print(f"  Hash stored in DB")

    await engine.dispose()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-key", action="store_true", help="Generate a new API key")
    parser.add_argument("--label", default="default", help="API key label")
    args = parser.parse_args()

    if args.generate_key:
        asyncio.run(generate_api_key(args.label))
    else:
        asyncio.run(seed())
