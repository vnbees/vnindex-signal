"""HTTP client for FireAnt REST at api.fireant.vn (Review v2 on-demand)."""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import httpx

from config import settings
from services.fireant_quote_service import require_fireant_token

logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://api.fireant.vn"
_MAX_RETRIES = 3
_RETRY_STATUS = {429, 500, 502, 503, 504}


def fireant_api_base() -> str:
    return (settings.fireant_api_base or DEFAULT_BASE).rstrip("/")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _extract_list(data: Any, keys: tuple[str, ...] = ("items", "data", "results", "rows", "icbIndices")) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in keys:
            inner = data.get(key)
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
    return []


async def _request_json(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    token: str,
) -> Any:
    url = f"{fireant_api_base()}{path}"
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.request(method, url, params=params, headers=_auth_headers(token))
            if resp.status_code in _RETRY_STATUS and attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError(f"FireAnt request failed: {path}")


async def fetch_icb_catalog(token: str | None = None) -> list[dict[str, Any]]:
    token = token or require_fireant_token()
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = await _request_json(client, "GET", "/icb", token=token)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return _extract_list(data)


async def fetch_icb_latest_index(token: str | None = None) -> list[dict[str, Any]]:
    token = token or require_fireant_token()
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = await _request_json(client, "GET", "/icb/latest-index", token=token)
        return _extract_list(data)


async def fetch_historical_quotes(
    symbol: str,
    start_date: date,
    end_date: date,
    token: str | None = None,
    *,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    token = token or require_fireant_token()
    params = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = await _request_json(
            client,
            "GET",
            f"/symbols/{symbol}/historical-quotes",
            params=params,
            token=token,
        )
        return data if isinstance(data, list) else []


async def fetch_profile(symbol: str, token: str | None = None) -> dict[str, Any] | None:
    token = token or require_fireant_token()
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = await _request_json(client, "GET", f"/symbols/{symbol}/profile", token=token)
        return data if isinstance(data, dict) else None


async def fetch_symbol_meta(symbol: str, token: str | None = None) -> dict[str, Any] | None:
    token = token or require_fireant_token()
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = await _request_json(client, "GET", f"/symbols/{symbol}", token=token)
        return data if isinstance(data, dict) else None
