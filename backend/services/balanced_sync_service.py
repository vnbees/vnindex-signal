"""Đồng bộ Fireant → DB + build snapshot JSON cho prompt Balanced."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.balanced_indicators import BarCloseVol, compute_from_bars
from services.balanced_sector_map import extract_sector_display, sector_flow_bucket
from services.balanced_universe import BALANCED_DAILY_UNIVERSE
from database import AsyncSessionLocal
from services.fireant_quote_service import (
    fetch_icb_catalog,
    fetch_icb_latest_index,
    fetch_historical_quotes,
    fetch_profile,
    fetch_symbol_meta,
    fetch_symbol_posts,
    upsert_quotes_full,
)

logger = logging.getLogger(__name__)

NEWS_WINDOW_DAYS = 7


def _parse_bar_date(bar: dict[str, Any]) -> date | None:
    ds = (bar.get("date") or "")[:10]
    try:
        return date.fromisoformat(ds)
    except ValueError:
        return None


def _post_external_id(symbol: str, item: dict[str, Any]) -> str:
    for k in ("id", "postId", "postID", "articleId"):
        v = item.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()[:128]
    raw = json.dumps(item, ensure_ascii=False, sort_keys=True)[:2000]
    h = hashlib.sha256(f"{symbol}|{raw}".encode("utf-8")).hexdigest()[:40]
    return f"h_{h}"


def _post_published_at(item: dict[str, Any]) -> datetime | None:
    for k in ("publishedDate", "publishedAt", "createdDate", "createdAt", "date"):
        v = item.get(k)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            try:
                return datetime.fromtimestamp(float(v) / 1000.0, tz=timezone.utc)
            except Exception:
                continue
        if isinstance(v, str) and v.strip():
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _post_title_summary(item: dict[str, Any]) -> tuple[str | None, str | None]:
    title = item.get("title") or item.get("name") or item.get("subject")
    if title is not None:
        title = str(title)[:4000]
    summary = item.get("summary") or item.get("description") or item.get("content")
    if summary is not None and not isinstance(summary, str):
        summary = str(summary)[:8000]
    elif isinstance(summary, str):
        summary = summary[:8000]
    return title, summary


async def _persist_profile(
    db: AsyncSession,
    symbol: str,
    profile: dict[str, Any] | None,
) -> None:
    if not profile:
        return
    sector, icb = extract_sector_display(profile)
    await db.execute(
        text(
            """
            INSERT INTO fireant_symbol_profile (symbol, sector_display, icb_code, raw_json, fetched_at)
            VALUES (:symbol, :sector, :icb, CAST(:raw AS jsonb), now())
            ON CONFLICT (symbol) DO UPDATE SET
              sector_display = EXCLUDED.sector_display,
              icb_code = EXCLUDED.icb_code,
              raw_json = EXCLUDED.raw_json,
              fetched_at = now()
            """
        ),
        {
            "symbol": symbol,
            "sector": sector,
            "icb": icb,
            "raw": json.dumps(profile, ensure_ascii=False),
        },
    )


async def _persist_posts(
    db: AsyncSession,
    symbol: str,
    items: list[dict[str, Any]],
    cutoff: date,
) -> int:
    n = 0
    cutoff_dt = datetime(cutoff.year, cutoff.month, cutoff.day, tzinfo=timezone.utc)
    start_cut = cutoff_dt - timedelta(days=NEWS_WINDOW_DAYS)
    for item in items:
        pub = _post_published_at(item)
        if pub is not None and pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub is not None and (pub < start_cut or pub > cutoff_dt + timedelta(days=1)):
            continue
        ext = _post_external_id(symbol, item)
        title, summary = _post_title_summary(item)
        await db.execute(
            text(
                """
                INSERT INTO fireant_symbol_post (symbol, external_id, title, summary, published_at, raw_json)
                VALUES (:symbol, :ext, :title, :summary, :published_at, CAST(:raw AS jsonb))
                ON CONFLICT (symbol, external_id) DO UPDATE SET
                  title = COALESCE(EXCLUDED.title, fireant_symbol_post.title),
                  summary = COALESCE(EXCLUDED.summary, fireant_symbol_post.summary),
                  published_at = COALESCE(EXCLUDED.published_at, fireant_symbol_post.published_at),
                  raw_json = EXCLUDED.raw_json,
                  ingested_at = now()
                """
            ),
            {
                "symbol": symbol,
                "ext": ext,
                "title": title,
                "summary": summary,
                "published_at": pub,
                "raw": json.dumps(item, ensure_ascii=False),
            },
        )
        n += 1
    return n


async def _sync_one_symbol(
    db: AsyncSession,
    symbol: str,
    token: str,
    start_date: date,
    end_date: date,
    as_of_cutoff: date,
) -> tuple[str, dict[str, Any] | None, str | None]:
    try:
        quotes = await fetch_historical_quotes(symbol, start_date, end_date, token)
        if quotes:
            await upsert_quotes_full(db, symbol, quotes)
        symbol_meta = await fetch_symbol_meta(symbol, token)
        profile = await fetch_profile(symbol, token)
        await _persist_profile(db, symbol, profile)
        posts = await fetch_symbol_posts(symbol, token, page=1, page_size=50)
        await _persist_posts(db, symbol, posts, as_of_cutoff)
        await db.commit()
        sector, icb_code = extract_sector_display(profile or {})
        # Ưu tiên ICB code từ endpoint /symbols/{symbol} vì ổn định hơn profile text.
        if isinstance(symbol_meta, dict):
            icb_from_meta = symbol_meta.get("icbCode") or symbol_meta.get("industryCode")
            if icb_from_meta is not None and str(icb_from_meta).strip():
                icb_code = str(icb_from_meta).strip()
        return (
            symbol,
            {
                "quotes": quotes,
                "profile": profile,
                "symbol_meta": symbol_meta,
                "sector": sector,
                "icb_code": icb_code,
                "posts": posts,
            },
            None,
        )
    except Exception as e:
        await db.rollback()
        logger.exception("balanced sync failed for %s", symbol)
        return symbol, None, str(e)


def _serialize_posts_recent(
    items: list[dict[str, Any]],
    as_of_cutoff: date,
    max_items: int = 10,
) -> list[dict[str, Any]]:
    """Trả các bài trong 7 ngày gần nhất, đủ cho AI chấm sentiment."""
    cutoff_dt = datetime(as_of_cutoff.year, as_of_cutoff.month, as_of_cutoff.day, tzinfo=timezone.utc)
    start_cut = cutoff_dt - timedelta(days=NEWS_WINDOW_DAYS)
    enriched: list[dict[str, Any]] = []
    for item in items:
        pub = _post_published_at(item)
        if pub is None:
            continue
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub < start_cut or pub > cutoff_dt + timedelta(days=1):
            continue
        title, summary = _post_title_summary(item)
        source = item.get("source") or item.get("publisher") or item.get("site")
        url = item.get("url") or item.get("link")
        enriched.append(
            {
                "title": title,
                "summary": summary,
                "published_at": pub.isoformat(),
                "source": str(source) if source is not None else None,
                "url": str(url) if url is not None else None,
            }
        )
    enriched.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    return enriched[:max_items]


def _resolve_analysis_date_and_symbol_sector(
    per_sym: dict[str, dict[str, Any]],
    universe: tuple[str, ...],
) -> tuple[date | None, dict[str, str], dict[str, str | None]]:
    """Trả (as_of_date T, symbol->sector_bucket, symbol->icb_code)."""
    latest: dict[str, date] = {}
    sym_sector: dict[str, str] = {}
    sym_icb_code: dict[str, str | None] = {}
    all_dates: set[date] = set()

    for sym in universe:
        pack = per_sym.get(sym)
        if not pack or not pack.get("quotes"):
            continue
        quotes: list[dict[str, Any]] = pack["quotes"]
        sector_raw = pack.get("sector") or "Khác"
        bucket = sector_flow_bucket(str(sector_raw))
        sym_sector[sym] = bucket
        raw_icb = pack.get("icb_code")
        sym_icb_code[sym] = str(raw_icb).strip() if raw_icb is not None and str(raw_icb).strip() else None
        dates_sym: list[date] = []
        for bar in quotes:
            d = _parse_bar_date(bar)
            if d:
                dates_sym.append(d)
                all_dates.add(d)
        if dates_sym:
            latest[sym] = max(dates_sym)

    if not latest:
        return None, sym_sector, sym_icb_code

    t_target = min(latest.values())
    sorted_asc = sorted(all_dates)
    if not sorted_asc:
        return None, sym_sector, sym_icb_code
    if t_target in all_dates:
        t = t_target
    else:
        older = [d for d in sorted_asc if d <= t_target]
        t = older[-1] if older else sorted_asc[-1]
    return t, sym_sector, sym_icb_code


def _to_float_safe(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _flatten_icb_row(item: dict[str, Any]) -> dict[str, Any]:
    """FireAnt /icb/latest-index: mỗi phần tử có industryCode, date, indexValues{...}."""
    iv = item.get("indexValues")
    if isinstance(iv, dict):
        merged = {**item, **iv}
        return merged
    return item


def _icb_positive_money_flow(flat: dict[str, Any]) -> float | None:
    for key in ("PositiveMoneyFlow", "positiveMoneyFlow"):
        v = _to_float_safe(flat.get(key))
        if v is not None:
            return v
    return None


def _icb_index_change_pct_day(flat: dict[str, Any]) -> float | None:
    """% biến động chỉ số ngày — dùng gán sector_flow_pct (cùng thang % với heuristic cũ)."""
    prev = _to_float_safe(flat.get("IndexPrev") or flat.get("indexPrev"))
    close = _to_float_safe(flat.get("IndexClose") or flat.get("indexClose"))
    if prev is not None and close is not None and prev != 0:
        return (close - prev) / prev * 100.0
    for key in ("pctChange5d", "changePct", "percentChange", "pct", "change"):
        v = _to_float_safe(flat.get(key))
        if v is not None:
            return v
    return None


def _icb_sector_display_name(flat: dict[str, Any]) -> str | None:
    raw = (
        flat.get("ICBName")
        or flat.get("icbName")
        or flat.get("name")
        or flat.get("industryName")
        or flat.get("title")
        or flat.get("label")
    )
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    code = flat.get("ICBCode") or flat.get("icbCode") or flat.get("industryCode")
    if code is not None and str(code).strip():
        return f"ICB_{code}"
    return None


def _extract_sector_flows_from_icb(
    rows: list[dict[str, Any]],
    level_by_code: dict[str, int],
    name_by_code: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, float], list[dict[str, Any]]]:
    """
    - top9: 9 dòng ICB chi tiết (ngành con như FireAnt), không gộp bucket.
    - pct_all: theo sector_flow_bucket (nhóm prompt) để map sector_flow_pct từng mã CP.
    """
    parsed: list[dict[str, Any]] = []
    by_bucket: dict[str, tuple[float | None, float | None]] = {}

    for item in rows:
        if not isinstance(item, dict):
            continue
        flat = _flatten_icb_row(item)
        raw_code = flat.get("ICBCode") or flat.get("icbCode") or flat.get("industryCode")
        code = str(raw_code).strip() if raw_code is not None else ""
        if not code:
            continue
        # Chuẩn hoá về level 3: nếu row là level 4 thì quy về mã level 3 tiền tố.
        level = level_by_code.get(code)
        level3_code = code
        if level != 3:
            level3_code = ""
            for i in range(len(code), 0, -1):
                cand = code[:i]
                if level_by_code.get(cand) == 3:
                    level3_code = cand
                    break
            if not level3_code:
                continue
        raw_name = name_by_code.get(level3_code) or _icb_sector_display_name(flat)
        if raw_name is None:
            continue
        pmf = _icb_positive_money_flow(flat)
        day_pct = _icb_index_change_pct_day(flat)
        # Chuẩn nhất: dùng đúng tên ngành ICB level 3 làm sector_group.
        bucket = str(raw_name).strip()
        parsed.append(
            {
                "raw_name": raw_name,
                "icb_code": level3_code,
                "bucket": bucket,
                "pmf": pmf,
                "day_pct": day_pct,
            }
        )
        prev = by_bucket.get(bucket)
        if prev is None:
            by_bucket[bucket] = (pmf, day_pct)
        else:
            best_pmf, best_day = prev
            if pmf is not None and (best_pmf is None or pmf > best_pmf):
                best_pmf = pmf
                best_day = day_pct
            by_bucket[bucket] = (best_pmf, best_day)

    parsed.sort(
        key=lambda r: (
            r["pmf"] if r["pmf"] is not None else float("-inf"),
            r["day_pct"] if r["day_pct"] is not None else float("-inf"),
        ),
        reverse=True,
    )

    top9: list[dict[str, Any]] = []
    all_sectors: list[dict[str, Any]] = []
    for r in parsed:
        pmf = r["pmf"]
        day_pct = r["day_pct"]
        all_sectors.append(
            {
                "sector": r["raw_name"],
                "icb_code": r["icb_code"],
                "sector_group": r["bucket"],
                "positive_money_flow_vnd": round(pmf, 4) if pmf is not None else None,
                "index_change_pct_day": round(day_pct, 4) if day_pct is not None else None,
                "pct_change_vs_5d_avg": round(day_pct, 4) if day_pct is not None else None,
            }
        )

    for r in parsed[:9]:
        pmf = r["pmf"]
        day_pct = r["day_pct"]
        entry = {
            "sector": r["raw_name"],
            "icb_code": r["icb_code"],
            "sector_group": r["bucket"],
            "positive_money_flow_vnd": round(pmf, 4) if pmf is not None else None,
            "index_change_pct_day": round(day_pct, 4) if day_pct is not None else None,
            "pct_change_vs_5d_avg": round(day_pct, 4) if day_pct is not None else None,
        }
        top9.append(entry)

    pct_all: dict[str, float] = {}
    for b, t in by_bucket.items():
        _, day_pct = t
        if day_pct is not None:
            pct_all[b] = round(day_pct, 4)
    return top9, pct_all, all_sectors


async def _load_prior_all_sectors(
    db: AsyncSession,
    as_of_date: date,
    lookback: int = 5,
) -> list[list[dict[str, Any]]]:
    """Load prior snapshots' all_sectors (newest -> oldest), excluding current as_of_date."""
    rows = (
        await db.execute(
            text(
                """
                SELECT payload
                FROM balanced_daily_snapshot
                WHERE as_of_date < :as_of_date
                ORDER BY as_of_date DESC
                LIMIT :lim
                """
            ),
            {"as_of_date": as_of_date, "lim": lookback},
        )
    ).all()
    out: list[list[dict[str, Any]]] = []
    for row in rows:
        p = row[0]
        if isinstance(p, str):
            try:
                p = json.loads(p)
            except Exception:
                continue
        if not isinstance(p, dict):
            continue
        all_sectors = p.get("all_sectors")
        if isinstance(all_sectors, list):
            out.append([x for x in all_sectors if isinstance(x, dict)])
    return out


def _enrich_sector_flow_5d(
    all_sectors: list[dict[str, Any]],
    prior_all_sectors: list[list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    """
    Add 5-day cash-flow context:
    - positive_money_flow_avg_5d_vnd
    - positive_money_flow_pct_vs_5d_avg
    Return (all_enriched, top9_by_5d, bucket_pct_map_for_symbols)
    """
    hist_by_sector: dict[str, list[float]] = {}
    for daily in prior_all_sectors:
        for item in daily:
            sec = item.get("sector")
            pmf = _to_float_safe(item.get("positive_money_flow_vnd"))
            if sec is None or pmf is None:
                continue
            s = str(sec).strip()
            if not s:
                continue
            hist_by_sector.setdefault(s, []).append(pmf)

    enriched: list[dict[str, Any]] = []
    for item in all_sectors:
        sec = str(item.get("sector") or "").strip()
        cur = _to_float_safe(item.get("positive_money_flow_vnd"))
        prior = hist_by_sector.get(sec, [])
        avg5 = (sum(prior) / len(prior)) if prior else None
        pct5 = ((cur - avg5) / avg5 * 100.0) if (cur is not None and avg5 is not None and avg5 > 0) else None
        row = dict(item)
        row["positive_money_flow_avg_5d_vnd"] = round(avg5, 4) if avg5 is not None else None
        row["positive_money_flow_pct_vs_5d_avg"] = round(pct5, 4) if pct5 is not None else None
        if pct5 is not None:
            # Keep backward-compatible key but now truly vs 5d avg.
            row["pct_change_vs_5d_avg"] = round(pct5, 4)
        enriched.append(row)

    def _rank_key(x: dict[str, Any]) -> tuple[float, float]:
        pct = _to_float_safe(x.get("positive_money_flow_pct_vs_5d_avg"))
        pmf = _to_float_safe(x.get("positive_money_flow_vnd"))
        return (
            pct if pct is not None else float("-inf"),
            pmf if pmf is not None else float("-inf"),
        )

    top9 = sorted(enriched, key=_rank_key, reverse=True)[:9]

    bucket_map: dict[str, float] = {}
    for item in enriched:
        bucket = str(item.get("sector_group") or "").strip()
        pct = _to_float_safe(item.get("positive_money_flow_pct_vs_5d_avg"))
        if not bucket or pct is None:
            continue
        prev = bucket_map.get(bucket)
        if prev is None or pct > prev:
            bucket_map[bucket] = pct

    return enriched, top9, {k: round(v, 4) for k, v in bucket_map.items()}


def _indicators_for_symbol(quotes: list[dict[str, Any]], t: date) -> dict[str, Any] | None:
    dated: list[tuple[date, BarCloseVol]] = []
    for bar in quotes:
        d = _parse_bar_date(bar)
        if d is None or d > t:
            continue
        try:
            c = float(bar.get("priceClose") or 0) * 1000.0
            h = float(bar.get("priceHigh") or 0) * 1000.0
            l = float(bar.get("priceLow") or 0) * 1000.0
            v = float(bar.get("totalVolume") or 0)
        except (TypeError, ValueError):
            continue
        dated.append((d, BarCloseVol(close=c, high=h, low=l, volume=v)))
    dated.sort(key=lambda x: x[0], reverse=True)
    bars_desc = [b for _, b in dated]
    if len(bars_desc) < 30:
        return None
    ind = compute_from_bars(bars_desc)
    close_t = bars_desc[0].close
    vol_latest = bars_desc[0].volume
    vol_avg_5 = sum(b.volume for b in bars_desc[:5]) / 5.0 if len(bars_desc) >= 5 else None
    vol_avg_20 = sum(b.volume for b in bars_desc[:20]) / 20.0 if len(bars_desc) >= 20 else None
    return {
        **ind,
        "price_close_vnd": round(close_t, 2),
        "trade_date": t.isoformat(),
        "total_volume_latest": round(vol_latest, 4),
        "avg_volume_5d": round(vol_avg_5, 4) if vol_avg_5 is not None else None,
        "avg_volume_20d": round(vol_avg_20, 4) if vol_avg_20 is not None else None,
    }


def _passes_balanced_heuristic(
    ind: dict[str, Any],
    sector_pct: float | None,
) -> bool:
    rsi = ind.get("rsi14") or 50.0
    macd = ind.get("macd_hist") or 0.0
    ratio = ind.get("sma5_over_sma20")
    vr = ind.get("volume_ratio")
    if rsi < 25 or rsi > 55:
        return False
    if macd <= 0:
        return False
    if ratio is not None and ratio < 0.95:
        return False
    if vr is not None and vr < 0.75:
        return False
    if sector_pct is not None and sector_pct < -30.0:
        return False
    return True


async def run_balanced_sync(db: AsyncSession, token: str) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=800)
    per_sym: dict[str, dict[str, Any] | None] = {}
    errors: list[dict[str, str]] = []
    sem = asyncio.Semaphore(6)

    async def wrapped(sym: str) -> None:
        async with sem:
            async with AsyncSessionLocal() as session:
                s, data, err = await _sync_one_symbol(session, sym, token, start, end, end)
            if err:
                errors.append({"symbol": s, "error": err})
            elif data:
                per_sym[s] = data

    await asyncio.gather(*(wrapped(s) for s in BALANCED_DAILY_UNIVERSE))

    t, sym_sector, sym_icb_code = _resolve_analysis_date_and_symbol_sector(
        {k: v for k, v in per_sym.items() if v},
        BALANCED_DAILY_UNIVERSE,
    )
    icb_catalog = await fetch_icb_catalog(token)
    icb_rows = await fetch_icb_latest_index(token)
    icb_level_by_code: dict[str, int] = {}
    icb_name_by_code: dict[str, str] = {}
    for item in icb_catalog:
        code = item.get("industryCode") or item.get("icbCode")
        name = item.get("name") or item.get("industryName")
        level = item.get("level")
        if code is None:
            continue
        code_s = str(code).strip()
        if not code_s:
            continue
        if isinstance(level, (int, float)):
            icb_level_by_code[code_s] = int(level)
        if isinstance(name, str) and name.strip():
            icb_name_by_code[code_s] = name.strip()
    top9, sector_pct_map, all_sectors = _extract_sector_flows_from_icb(
        icb_rows,
        icb_level_by_code,
        icb_name_by_code,
    )
    prior_all_sectors = await _load_prior_all_sectors(db, t) if t is not None else []
    all_sectors_enriched, top9_5d, sector_pct_map_5d = _enrich_sector_flow_5d(all_sectors, prior_all_sectors)
    if top9_5d:
        top9 = top9_5d
    if sector_pct_map_5d:
        sector_pct_map = sector_pct_map_5d

    icb_catalog_name_by_code: dict[str, str] = {}
    for item in icb_catalog:
        code = item.get("industryCode") or item.get("icbCode")
        name = item.get("name") or item.get("industryName")
        if code is None or name is None:
            continue
        code_s = str(code).strip()
        name_s = str(name).strip()
        if code_s and name_s:
            icb_catalog_name_by_code[code_s] = name_s

    icb_name_by_code: dict[str, str] = {}
    icb_bucket_by_code: dict[str, str] = {}
    for item in all_sectors_enriched:
        code = item.get("icb_code")
        name = item.get("sector")
        bucket = item.get("sector_group")
        if code is None:
            continue
        code_s = str(code).strip()
        if not code_s:
            continue
        if isinstance(name, str) and name.strip():
            icb_name_by_code[code_s] = name.strip()
        if isinstance(bucket, str) and bucket.strip():
            icb_bucket_by_code[code_s] = bucket.strip()

    symbols_out: list[dict[str, Any]] = []
    candidates: list[tuple[float, dict[str, Any]]] = []
    for sym in BALANCED_DAILY_UNIVERSE:
        pack = per_sym.get(sym)
        if not pack or not pack.get("quotes") or t is None:
            continue
        ind = _indicators_for_symbol(pack["quotes"], t)
        if not ind:
            continue
        bucket = sym_sector.get(sym, "Khác")
        icb_code = sym_icb_code.get(sym)
        if icb_code:
            # Hiển thị và map theo ngành level 3 để nhất quán toàn bộ pipeline.
            level3_code = icb_code
            if icb_level_by_code.get(level3_code) != 3:
                for i in range(len(icb_code), 0, -1):
                    cand = icb_code[:i]
                    if icb_level_by_code.get(cand) == 3:
                        level3_code = cand
                        break
            level3_name = icb_catalog_name_by_code.get(level3_code) or icb_name_by_code.get(level3_code)
            bucket = icb_bucket_by_code.get(level3_code, (level3_name or bucket))
        sector_display = bucket
        if icb_code:
            level3_code = icb_code
            if icb_level_by_code.get(level3_code) != 3:
                for i in range(len(icb_code), 0, -1):
                    cand = icb_code[:i]
                    if icb_level_by_code.get(cand) == 3:
                        level3_code = cand
                        break
            sector_display = icb_catalog_name_by_code.get(
                level3_code,
                icb_name_by_code.get(level3_code, sector_display),
            )
        sp = sector_pct_map.get(bucket)
        posts_recent = _serialize_posts_recent(pack.get("posts") or [], t)
        row = {
            "symbol": sym,
            "sector": sector_display,
            "sector_group": bucket,
            "icb_code": icb_code,
            "sector_flow_pct": sp,
            "indicators": ind,
            "posts_recent_7d": posts_recent,
            "posts_ingested_note": f"Last {NEWS_WINDOW_DAYS}d window ending {t.isoformat()} — review raw_json in DB for sentiment.",
        }
        symbols_out.append(row)
        if _passes_balanced_heuristic(ind, sp):
            score = (sp or 0) + (ind.get("volume_ratio") or 1) * 2 + (ind.get("adx14") or 0) * 0.1
            candidates.append((score, row))

    candidates.sort(key=lambda x: x[0], reverse=True)
    top3 = [x[1] for x in candidates[:3]]

    synced_at = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "as_of_date": t.isoformat() if t else None,
        "synced_at": synced_at,
        "universe_size": len(BALANCED_DAILY_UNIVERSE),
        "symbols_ok": len([s for s in BALANCED_DAILY_UNIVERSE if per_sym.get(s)]),
        "top9_sectors": top9,
        "all_sectors": all_sectors_enriched,
        "sector_flow": {
            "source": "restv2.fireant.vn/icb/latest-index",
            "top9_rank_by": "positive_money_flow_pct_vs_5d_avg descending when available; fallback to positive_money_flow_vnd",
            "top9_sector_field": "sector = ICBName đầy đủ; sector_group = map thô cho prompt Balanced",
            "symbol_sector_pct_field": "positive_money_flow_pct_vs_5d_avg theo sector_group (bucket) -> sector_flow_pct",
            "lookback_days_for_avg": 5,
        },
        "symbols": symbols_out,
        "screened_top3": top3,
        "sync_errors": errors,
        "news_policy": {
            "window_days": NEWS_WINDOW_DAYS,
            "source": "fireant_symbol_post",
            "auto_negative_filter": False,
            "note": "Store posts for AI/human; no auto negative flag in pipeline.",
        },
        "disclaimer": "Phân tích kỹ thuật; không phải tư vấn đầu tư. Tham số chỉ báo: RSI14 Wilder, MACD(12,26,9) hist, SMA5/20, ADX14, volume vs SMA20.",
    }

    if t is not None:
        await db.execute(
            text(
                """
                INSERT INTO balanced_daily_snapshot (as_of_date, synced_at, payload)
                VALUES (:as_of_date, now(), CAST(:payload AS jsonb))
                ON CONFLICT (as_of_date) DO UPDATE SET
                  synced_at = now(),
                  payload = EXCLUDED.payload
                """
            ),
            {"as_of_date": t, "payload": json.dumps(payload, ensure_ascii=False)},
        )
        await db.commit()

    return {
        "synced_at": synced_at,
        "as_of_date": t.isoformat() if t else None,
        "symbols_total": len(BALANCED_DAILY_UNIVERSE),
        "symbols_ok": payload["symbols_ok"],
        "errors_count": len(errors),
        "errors": errors[:50],
        "snapshot_top9_count": len(top9),
        "screened_top3_symbols": [r["symbol"] for r in top3],
    }


async def load_snapshot_payload(
    db: AsyncSession,
    as_of: date | None,
) -> dict[str, Any] | None:
    if as_of is None:
        row = (
            await db.execute(
                text(
                    """
                    SELECT payload FROM balanced_daily_snapshot
                    ORDER BY as_of_date DESC LIMIT 1
                    """
                )
            )
        ).first()
    else:
        row = (
            await db.execute(
                text("SELECT payload FROM balanced_daily_snapshot WHERE as_of_date = :d"),
                {"d": as_of},
            )
        ).first()
    if not row:
        return None
    p = row[0]
    if isinstance(p, dict):
        return p
    if isinstance(p, str):
        return json.loads(p)
    return dict(p)


async def load_sector_flow_5d_payload(
    db: AsyncSession,
    as_of: date | None = None,
    sessions: int = 5,
) -> dict[str, Any] | None:
    """
    Return sector cash-flow time series for latest N sessions from stored snapshots.
    This is intended for AI-side analysis without recomputing from a single-day snapshot.
    """
    if sessions < 2:
        sessions = 2
    if sessions > 20:
        sessions = 20

    if as_of is None:
        anchor_row = (
            await db.execute(
                text("SELECT as_of_date FROM balanced_daily_snapshot ORDER BY as_of_date DESC LIMIT 1")
            )
        ).first()
    else:
        anchor_row = (
            await db.execute(
                text("SELECT as_of_date FROM balanced_daily_snapshot WHERE as_of_date = :d LIMIT 1"),
                {"d": as_of},
            )
        ).first()
    if not anchor_row:
        return None

    anchor_date: date = anchor_row[0]
    rows = (
        await db.execute(
            text(
                """
                SELECT as_of_date, payload
                FROM balanced_daily_snapshot
                WHERE as_of_date <= :anchor_date
                ORDER BY as_of_date DESC
                LIMIT :lim
                """
            ),
            {"anchor_date": anchor_date, "lim": sessions},
        )
    ).all()
    if not rows:
        return None

    ordered = list(reversed(rows))
    session_dates: list[str] = []
    sector_map: dict[str, dict[str, Any]] = {}

    for as_of_date, payload_raw in ordered:
        session_dates.append(as_of_date.isoformat())
        payload = payload_raw
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}
        all_sectors = payload.get("all_sectors")
        if not isinstance(all_sectors, list):
            continue

        by_name: dict[str, dict[str, Any]] = {}
        for item in all_sectors:
            if not isinstance(item, dict):
                continue
            sector_name = str(item.get("sector") or "").strip()
            if not sector_name:
                continue
            by_name[sector_name] = item
            if sector_name not in sector_map:
                sector_map[sector_name] = {
                    "sector": sector_name,
                    "sector_group": item.get("sector_group"),
                    "icb_code": item.get("icb_code"),
                    "points": [],
                }

        for sector_name, row in sector_map.items():
            cur = by_name.get(sector_name)
            if cur is None:
                row["points"].append(
                    {
                        "date": as_of_date.isoformat(),
                        "positive_money_flow_vnd": None,
                        "positive_money_flow_pct_vs_5d_avg": None,
                    }
                )
                continue
            row["points"].append(
                {
                    "date": as_of_date.isoformat(),
                    "positive_money_flow_vnd": _to_float_safe(cur.get("positive_money_flow_vnd")),
                    "positive_money_flow_pct_vs_5d_avg": _to_float_safe(
                        cur.get("positive_money_flow_pct_vs_5d_avg")
                    ),
                }
            )

    sectors = sorted(sector_map.values(), key=lambda x: x["sector"])
    return {
        "found": True,
        "as_of_date": anchor_date.isoformat(),
        "sessions": session_dates,
        "sectors": sectors,
    }
