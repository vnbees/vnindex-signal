"""Review v2: on-demand candidates from api.fireant.vn with struct display filter."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from schemas.review_v2 import ReviewV2BuySignal, ReviewV2CandidatesResponse
from services.balanced_sector_map import extract_sector_display
from services.balanced_universe import BALANCED_DAILY_UNIVERSE
from services.balanced_sync_service import (
    _enrich_sector_flow_5d,
    _extract_sector_flows_from_icb,
    _indicators_for_symbol,
    _load_prior_all_sectors,
    _passes_balanced_heuristic,
    _resolve_analysis_date_and_symbol_sector,
)
from services.daily_automation_service import _fallback_why_selected
from services import fireant_api_client

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, ReviewV2CandidatesResponse]] = {}
_FETCH_CONCURRENCY = 8
_QUOTE_LOOKBACK_DAYS = 800


def passes_review_display_filter(snapshot_row: dict[str, Any]) -> bool:
    """Struct filter matching review page: sector flow > 0 and latest volume > avg 5d."""
    sector_flow_pct = snapshot_row.get("sector_flow_pct")
    if sector_flow_pct is None or float(sector_flow_pct) <= 0:
        return False
    ind = snapshot_row.get("indicators")
    if not isinstance(ind, dict):
        return False
    vol = ind.get("total_volume_latest")
    avg5 = ind.get("avg_volume_5d")
    if vol is None or avg5 is None:
        return False
    return float(vol) > float(avg5)


def _cache_key(as_of: date | None) -> str:
    return as_of.isoformat() if as_of else "latest"


def _get_cached(key: str) -> ReviewV2CandidatesResponse | None:
    entry = _cache.get(key)
    if not entry:
        return None
    expires_at, payload = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    out = payload.model_copy(deep=True)
    out.cached = True
    return out


def _set_cache(key: str, payload: ReviewV2CandidatesResponse) -> None:
    ttl = max(60, int(settings.review_v2_cache_ttl_seconds))
    _cache[key] = (time.monotonic() + ttl, payload)


async def _fetch_symbol_pack(
    symbol: str,
    token: str,
    start_date: date,
    end_date: date,
    sem: asyncio.Semaphore,
) -> tuple[str, dict[str, Any] | None]:
    async with sem:
        try:
            quotes, profile, meta = await asyncio.gather(
                fireant_api_client.fetch_historical_quotes(symbol, start_date, end_date, token),
                fireant_api_client.fetch_profile(symbol, token),
                fireant_api_client.fetch_symbol_meta(symbol, token),
            )
            sector, icb_code = extract_sector_display(profile or {})
            if isinstance(meta, dict):
                icb_from_meta = meta.get("icbCode") or meta.get("industryCode")
                if icb_from_meta is not None and str(icb_from_meta).strip():
                    icb_code = str(icb_from_meta).strip()
            return (
                symbol,
                {
                    "quotes": quotes,
                    "profile": profile,
                    "symbol_meta": meta,
                    "sector": sector,
                    "icb_code": icb_code,
                },
            )
        except Exception:
            logger.exception("review v2 fetch failed for %s", symbol)
            return symbol, None


def _build_icb_maps(
    icb_catalog: list[dict[str, Any]],
    all_sectors_enriched: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, str], dict[str, str], dict[str, str]]:
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

    icb_catalog_name_by_code = dict(icb_name_by_code)
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

    return icb_level_by_code, icb_name_by_code, icb_catalog_name_by_code, icb_bucket_by_code


def _symbol_rows_for_universe(
    per_sym: dict[str, dict[str, Any]],
    t: date,
    sym_sector: dict[str, str],
    sym_icb_code: dict[str, str | None],
    sector_pct_map: dict[str, float],
    icb_level_by_code: dict[str, int],
    icb_name_by_code: dict[str, str],
    icb_catalog_name_by_code: dict[str, str],
    icb_bucket_by_code: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    symbols_out: list[dict[str, Any]] = []
    screened: list[tuple[float, dict[str, Any]]] = []

    for sym in BALANCED_DAILY_UNIVERSE:
        pack = per_sym.get(sym)
        if not pack or not pack.get("quotes"):
            continue
        ind = _indicators_for_symbol(pack["quotes"], t)
        if not ind:
            continue

        bucket = sym_sector.get(sym, "Khác")
        icb_code = sym_icb_code.get(sym)
        if icb_code:
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
        row = {
            "symbol": sym,
            "sector": sector_display,
            "sector_group": bucket,
            "icb_code": icb_code,
            "sector_flow_pct": sp,
            "indicators": ind,
        }
        symbols_out.append(row)
        if _passes_balanced_heuristic(ind, sp):
            score = (sp or 0) + (ind.get("volume_ratio") or 1) * 2 + (ind.get("adx14") or 0) * 0.1
            screened.append((score, row))

    screened.sort(key=lambda x: x[0], reverse=True)
    return symbols_out, [x[1] for x in screened]


def _rows_to_buy_signals(rows: list[dict[str, Any]]) -> list[ReviewV2BuySignal]:
    out: list[ReviewV2BuySignal] = []
    for rank, row in enumerate(rows, start=1):
        sym = str(row.get("symbol") or "").upper()
        ind = row.get("indicators") if isinstance(row.get("indicators"), dict) else {}
        price = ind.get("price_close_vnd")
        why = _fallback_why_selected(sym, row)
        out.append(
            ReviewV2BuySignal(
                rank=rank,
                symbol=sym,
                sector=str(row.get("sector")) if row.get("sector") is not None else None,
                recommendation="THEO DÕI MUA",
                price=float(price) if price is not None else None,
                why_selected=why,
                sector_flow_pct=float(row["sector_flow_pct"]) if row.get("sector_flow_pct") is not None else None,
            )
        )
    return out


async def compute_review_v2_candidates(
    db: AsyncSession | None = None,
    *,
    refresh: bool = False,
) -> ReviewV2CandidatesResponse:
    from services.fireant_quote_service import require_fireant_token

    if not refresh:
        cached = _get_cached("latest")
        if cached is not None:
            return cached

    token = require_fireant_token()

    end = date.today()
    start = end - timedelta(days=_QUOTE_LOOKBACK_DAYS)

    icb_catalog, icb_rows = await asyncio.gather(
        fireant_api_client.fetch_icb_catalog(token),
        fireant_api_client.fetch_icb_latest_index(token),
    )

    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)
    packs = await asyncio.gather(
        *[_fetch_symbol_pack(sym, token, start, end, sem) for sym in BALANCED_DAILY_UNIVERSE]
    )
    per_sym: dict[str, dict[str, Any]] = {sym: pack for sym, pack in packs if pack}

    t, sym_sector, sym_icb_code = _resolve_analysis_date_and_symbol_sector(per_sym, BALANCED_DAILY_UNIVERSE)
    if t is None:
        raise RuntimeError("Không xác định được ngày phân tích từ dữ liệu FireAnt.")

    if not refresh:
        cached = _get_cached(_cache_key(t))
        if cached is not None:
            return cached

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

    _, sector_pct_map_day, all_sectors = _extract_sector_flows_from_icb(
        icb_rows,
        icb_level_by_code,
        icb_name_by_code,
    )

    sector_pct_map = sector_pct_map_day
    all_sectors_enriched = all_sectors
    if db is not None:
        prior = await _load_prior_all_sectors(db, t)
        if prior:
            all_sectors_enriched, _, sector_pct_map_5d = _enrich_sector_flow_5d(all_sectors, prior)
            if sector_pct_map_5d:
                sector_pct_map = sector_pct_map_5d

    icb_level_by_code, icb_name_by_code, icb_catalog_name_by_code, icb_bucket_by_code = _build_icb_maps(
        icb_catalog,
        all_sectors_enriched,
    )

    _, screened_all = _symbol_rows_for_universe(
        per_sym,
        t,
        sym_sector,
        sym_icb_code,
        sector_pct_map,
        icb_level_by_code,
        icb_name_by_code,
        icb_catalog_name_by_code,
        icb_bucket_by_code,
    )

    display_rows = [row for row in screened_all if passes_review_display_filter(row)]
    buy_signals = _rows_to_buy_signals(display_rows)

    title = f"TÍN HIỆU MUA BALANCED - NGÀY {t.strftime('%d/%m/%Y')}"
    result = ReviewV2CandidatesResponse(
        ok=True,
        reference_date=t,
        as_of_date=t,
        title=title,
        source="api.fireant.vn",
        screened_count=len(screened_all),
        display_count=len(display_rows),
        buy_signals=buy_signals,
        cached=False,
        computed_at=datetime.now(timezone.utc),
    )
    _set_cache(_cache_key(t), result)
    _set_cache("latest", result)
    return result
