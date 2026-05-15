"""Legacy Gemini prompt builder — chỉ dùng cho script smoke test `scripts/debug_gemini_daily_io.py`.

Daily automation production **không** import module này; pipeline snapshot-only không gọi Gemini.
"""

from __future__ import annotations

import json
from typing import Any


def _compact_snapshot_for_ai(snapshot: dict[str, Any]) -> dict[str, Any]:
    payload = snapshot.get("payload") if isinstance(snapshot.get("payload"), dict) else snapshot
    if not isinstance(payload, dict):
        return {}
    symbols = payload.get("symbols")
    compact_symbols: list[dict[str, Any]] = []
    if isinstance(symbols, list):
        for item in symbols:
            if not isinstance(item, dict):
                continue
            indicators = item.get("indicators") if isinstance(item.get("indicators"), dict) else {}
            posts = item.get("posts_recent_7d") if isinstance(item.get("posts_recent_7d"), list) else []
            compact_posts: list[dict[str, Any]] = []
            for p in posts[:3]:
                if isinstance(p, dict):
                    compact_posts.append(
                        {
                            "title": p.get("title"),
                            "summary": p.get("summary"),
                            "published_at": p.get("published_at"),
                        }
                    )
            compact_symbols.append(
                {
                    "symbol": item.get("symbol"),
                    "sector": item.get("sector"),
                    "indicators": {
                        "trade_date": indicators.get("trade_date"),
                        "price_close_vnd": indicators.get("price_close_vnd"),
                        "rsi14": indicators.get("rsi14"),
                        "macd_hist": indicators.get("macd_hist"),
                        "sma5_over_sma20": indicators.get("sma5_over_sma20"),
                        "adx14": indicators.get("adx14"),
                        "volume_ratio": indicators.get("volume_ratio"),
                        "total_volume_latest": indicators.get("total_volume_latest"),
                        "avg_volume_5d": indicators.get("avg_volume_5d"),
                    },
                    "posts_recent_7d": compact_posts,
                }
            )
    return {
        "as_of_date": payload.get("as_of_date"),
        "symbols": compact_symbols,
    }


def _compact_sector_flow_for_ai(sector_flow: dict[str, Any]) -> dict[str, Any]:
    sectors = sector_flow.get("sectors")
    compact: list[dict[str, Any]] = []
    if isinstance(sectors, list):
        for item in sectors:
            if not isinstance(item, dict):
                continue
            points = item.get("points") if isinstance(item.get("points"), list) else []
            compact.append(
                {
                    "sector": item.get("sector"),
                    "points": [
                        {
                            "date": p.get("date"),
                            "positive_money_flow_vnd": p.get("positive_money_flow_vnd"),
                        }
                        for p in points[-5:]
                        if isinstance(p, dict)
                    ],
                }
            )
    return {"as_of_date": sector_flow.get("as_of_date"), "sessions": sector_flow.get("sessions"), "sectors": compact}


def build_gemini_prompt_for_smoke(base_prompt: str, snapshot: dict[str, Any], sector_flow: dict[str, Any]) -> str:
    """Ghép prompt như bản cũ trong `daily_automation_service` (chỉ phục vụ smoke test)."""
    compact_snapshot = _compact_snapshot_for_ai(snapshot)
    compact_sector_flow = _compact_sector_flow_for_ai(sector_flow)
    snapshot_json = json.dumps(compact_snapshot, ensure_ascii=False, separators=(",", ":"))
    sector_json = json.dumps(compact_sector_flow, ensure_ascii=False, separators=(",", ":"))
    return (
        f"{base_prompt}\n\n"
        "[DỮ LIỆU SNAPSHOT JSON]\n"
        f"{snapshot_json}\n\n"
        "[DỮ LIỆU SECTOR FLOW 5D JSON]\n"
        f"{sector_json}\n\n"
        "BẮT BUỘC trả về JSON object hợp lệ (không markdown, không text ngoài JSON) theo schema sau:\n"
        "{\n"
        '  "title": "string",\n'
        '  "reference_date": "YYYY-MM-DD",\n'
        '  "sector_flow_analysis": [\n'
        "    {\n"
        '      "sector": "string",\n'
        '      "flow_today_vnd": number,\n'
        '      "avg_5d_vnd": number,\n'
        '      "pct_vs_5d": number\n'
        "    }\n"
        "  ],\n"
        '  "selected_signals": [\n'
        "    {\n"
        '      "rank": number,\n'
        '      "symbol": "AAA",\n'
        '      "sector": "string|null",\n'
        '      "price": number|null,\n'
        '      "recommendation": "string|null",\n'
        '      "why_selected": ["string", "..."]\n'
        "    }\n"
        "  ],\n"
        '  "near_miss_signals": [\n'
        "    {\n"
        '      "symbol": "AAA",\n'
        '      "sector": "string|null",\n'
        '      "failed_conditions": ["string", "..."]\n'
        "    }\n"
        "  ],\n"
        '  "analysis_notes": "string"\n'
        "}\n"
        "Ràng buộc: selected_signals không giới hạn số lượng, symbol phải thuộc dữ liệu snapshot."
    )
