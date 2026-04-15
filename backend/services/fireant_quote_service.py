from __future__ import annotations

import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

FIREANT_BASE = "https://restv2.fireant.vn"
RUN_ANALYSIS = Path(__file__).resolve().parent.parent / "scripts" / "run_analysis.py"
# Mặc định dev (khớp _DEFAULT_FIREANT trong run_analysis.py) — production nên set FIREANT_TOKEN trong .env
FIREANT_TOKEN_FALLBACK = (
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


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _price_to_vnd(value: Any) -> Decimal | None:
    """
    Fireant historical quote prices are in 'thousand VND' units.
    Convert to VND to match newsfeed entry prices.
    """
    d = _to_decimal(value)
    if d is None:
        return None
    return d * Decimal("1000")


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        try:
            return datetime.fromisoformat(txt.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _default_fireant_token() -> str | None:
    try:
        text_content = RUN_ANALYSIS.read_text(encoding="utf-8")
    except Exception:
        return None
    m = re.search(
        r"_DEFAULT_FIREANT = \(\s*(.*?)\s*\)\s*\nFIREANT_TOKEN",
        text_content,
        re.DOTALL,
    )
    if not m:
        return None
    parts = re.findall(r'"([A-Za-z0-9_.+/=-]+)"', m.group(1))
    token = "".join(parts)
    if not token.startswith("eyJ"):
        return None
    return token


def get_fireant_token() -> str | None:
    """
    JWT Fireant (REST không Bearer → 401).
    Thứ tự: biến môi trường FIREANT_TOKEN → FIREANT_TOKEN_FALLBACK → parse _DEFAULT_FIREANT trong run_analysis.py.
    """
    token = (os.environ.get("FIREANT_TOKEN") or "").strip()
    if token:
        return token
    if FIREANT_TOKEN_FALLBACK:
        return FIREANT_TOKEN_FALLBACK
    return _default_fireant_token()


def require_fireant_token() -> str:
    """Giống get_fireant_token nhưng raise nếu vẫn không có token hợp lệ."""
    t = get_fireant_token()
    if not t:
        raise RuntimeError("Missing Fireant JWT — set FIREANT_TOKEN or keep run_analysis.py _DEFAULT_FIREANT.")
    return t


async def fetch_profile(symbol: str, token: str) -> dict[str, Any] | None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{FIREANT_BASE}/symbols/{symbol}/profile", headers=headers)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data if isinstance(data, dict) else None


async def fetch_symbol_posts(
    symbol: str,
    token: str,
    page: int = 1,
    page_size: int = 50,
) -> list[dict[str, Any]]:
    """GET /symbols/{sym}/posts, ưu tiên tab 'Bài viết' và loại trừ 'Cộng đồng'."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # Thử hint cho phía API chọn tab bài viết; nếu API bỏ qua thì vẫn có filter phía client.
    params = {
        "page": page,
        "pageSize": page_size,
        "tab": "articles",
        "type": "article",
    }

    def _extract_items(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ("items", "data", "results", "posts"):
                inner = data.get(key)
                if isinstance(inner, list):
                    return [x for x in inner if isinstance(x, dict)]
        return []

    def _is_article(item: dict[str, Any]) -> bool:
        """
        Giữ bài viết tin tức/editorial; loại post cộng đồng/discussion.
        Fireant có thể đổi tên field, nên check nhiều key và fallback theo source/title.
        """
        text_fields = []
        for k in (
            "type",
            "postType",
            "contentType",
            "category",
            "group",
            "sourceType",
            "feedType",
            "origin",
            "source",
        ):
            v = item.get(k)
            if v is not None:
                text_fields.append(str(v).strip().lower())
        merged = " | ".join(text_fields)
        community_tags = (
            "community",
            "cong dong",
            "discussion",
            "forum",
            "chat",
            "social",
            "user",
        )
        article_tags = ("article", "news", "bao", "tin tuc", "editorial", "analysis")

        if any(tag in merged for tag in community_tags):
            return False
        if any(tag in merged for tag in article_tags):
            return True

        # Fallback theo URL/source domain: nếu từ báo chí thường không phải community.
        url = str(item.get("url") or item.get("link") or "").lower()
        if "community" in url or "forum" in url:
            return False
        if url:
            return True
        # Không đủ metadata: mặc định giữ lại để tránh mất dữ liệu.
        return True

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{FIREANT_BASE}/symbols/{symbol}/posts",
            params=params,
            headers=headers,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = _extract_items(data)
        return [x for x in items if _is_article(x)]


async def fetch_historical_quotes(
    symbol: str,
    start_date: date,
    end_date: date,
    token: str,
) -> list[dict[str, Any]]:
    params = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "limit": 5000,
    }
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{FIREANT_BASE}/symbols/{symbol}/historical-quotes",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload if isinstance(payload, list) else []


async def upsert_quotes(
    db: AsyncSession,
    symbol: str,
    quotes: list[dict[str, Any]],
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO fireant_symbol (symbol, universe_131)
            VALUES (:symbol, FALSE)
            ON CONFLICT (symbol) DO NOTHING
            """
        ),
        {"symbol": symbol},
    )
    stmt = text(
        """
        INSERT INTO fireant_quote_daily (symbol, trade_date, price_close, source_ts)
        VALUES (:symbol, :trade_date, :price_close, :source_ts)
        ON CONFLICT (symbol, trade_date) DO UPDATE
        SET
          price_close = EXCLUDED.price_close,
          source_ts = EXCLUDED.source_ts,
          ingested_at = now()
        """
    )
    for bar in quotes:
        ds = (bar.get("date") or "")[:10]
        if not ds:
            continue
        try:
            trade_date = date.fromisoformat(ds)
        except ValueError:
            continue
        price_close = _price_to_vnd(bar.get("priceClose"))
        if price_close is None:
            continue
        await db.execute(
            stmt,
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "price_close": price_close,
                "source_ts": _to_datetime(bar.get("date")),
            },
        )


async def upsert_quotes_full(
    db: AsyncSession,
    symbol: str,
    quotes: list[dict[str, Any]],
) -> None:
    """
    Ghi đủ OHLCV + total_value; giá lưu **VND** (×1000) giống upsert_quotes price_close.
    """
    await db.execute(
        text(
            """
            INSERT INTO fireant_symbol (symbol, universe_131)
            VALUES (:symbol, FALSE)
            ON CONFLICT (symbol) DO NOTHING
            """
        ),
        {"symbol": symbol},
    )
    stmt = text(
        """
        INSERT INTO fireant_quote_daily (
            symbol, trade_date,
            price_open, price_high, price_low, price_close,
            price_average, price_basic, total_volume, total_value,
            source_ts
        )
        VALUES (
            :symbol, :trade_date,
            :price_open, :price_high, :price_low, :price_close,
            :price_average, :price_basic, :total_volume, :total_value,
            :source_ts
        )
        ON CONFLICT (symbol, trade_date) DO UPDATE SET
          price_open = EXCLUDED.price_open,
          price_high = EXCLUDED.price_high,
          price_low = EXCLUDED.price_low,
          price_close = EXCLUDED.price_close,
          price_average = EXCLUDED.price_average,
          price_basic = EXCLUDED.price_basic,
          total_volume = EXCLUDED.total_volume,
          total_value = EXCLUDED.total_value,
          source_ts = EXCLUDED.source_ts,
          ingested_at = now()
        """
    )
    for bar in quotes:
        ds = (bar.get("date") or "")[:10]
        if not ds:
            continue
        try:
            trade_date = date.fromisoformat(ds)
        except ValueError:
            continue
        po = _price_to_vnd(bar.get("priceOpen"))
        ph = _price_to_vnd(bar.get("priceHigh"))
        pl = _price_to_vnd(bar.get("priceLow"))
        pc = _price_to_vnd(bar.get("priceClose"))
        if pc is None:
            continue
        pa = _price_to_vnd(bar.get("priceAverage"))
        pb = _price_to_vnd(bar.get("priceBasic"))
        tvol = _to_decimal(bar.get("totalVolume"))
        tval = _to_decimal(bar.get("totalValue"))
        await db.execute(
            stmt,
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "price_open": po,
                "price_high": ph,
                "price_low": pl,
                "price_close": pc,
                "price_average": pa,
                "price_basic": pb,
                "total_volume": tvol,
                "total_value": tval,
                "source_ts": _to_datetime(bar.get("date")),
            },
        )


async def get_trade_dates_with_close(
    db: AsyncSession,
    symbol: str,
    from_date: date,
) -> list[tuple[date, Decimal]]:
    stmt = text(
        """
        SELECT trade_date, price_close
        FROM fireant_quote_daily
        WHERE symbol = :symbol
          AND trade_date >= :from_date
          AND price_close IS NOT NULL
        ORDER BY trade_date ASC
        """
    )
    rows = (await db.execute(stmt, {"symbol": symbol, "from_date": from_date})).all()
    result: list[tuple[date, Decimal]] = []
    for row in rows:
        trade_date = row[0]
        close = _to_decimal(row[1])
        if trade_date is None or close is None:
            continue
        result.append((trade_date, close))
    return result


async def get_latest_close(
    db: AsyncSession,
    symbol: str,
) -> tuple[date, Decimal] | None:
    stmt = text(
        """
        SELECT trade_date, price_close
        FROM fireant_quote_daily
        WHERE symbol = :symbol
          AND price_close IS NOT NULL
        ORDER BY trade_date DESC
        LIMIT 1
        """
    )
    row = (await db.execute(stmt, {"symbol": symbol})).first()
    if not row:
        return None
    close = _to_decimal(row[1])
    if close is None:
        return None
    return row[0], close


def pnl_percent(entry_price: Decimal, target_price: Decimal) -> float | None:
    if entry_price == 0:
        return None
    return float(((target_price - entry_price) / entry_price) * Decimal("100"))
