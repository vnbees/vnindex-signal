from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.signal_entry import SignalEntry
from schemas.automation import AutomationStepResult, DailyAutomationResponse
from schemas.signal_entry import BuySignalIn


@dataclass
class ParsedSignalText:
    title: str | None
    reference_date: date
    raw_text: str
    buy_signals: list[BuySignalIn]


def _first_non_empty_line(text: str) -> str | None:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return None


def _extract_reference_date(text: str) -> date:
    match = re.search(r"NGÀY\s+(\d{2})/(\d{2})/(\d{4})", text, re.IGNORECASE)
    if not match:
        raise ValueError("Không trích xuất được reference_date")
    day_s, month_s, year_s = match.groups()
    return date(int(year_s), int(month_s), int(day_s))


def _to_number(value: str) -> float | None:
    raw = value.strip().replace(" ", "")
    if not raw:
        return None
    # Accept forms like 10,950 and 10.950 and 10,950.5
    if "," in raw and "." in raw:
        raw = raw.replace(",", "")
    elif "," in raw and "." not in raw:
        raw = raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_buy_signals(text: str, valid_symbols: set[str] | None = None) -> list[BuySignalIn]:
    lines = text.splitlines()
    starts: list[tuple[int, int, str, str | None]] = []
    header_re = re.compile(r"^\s*#\s*(\d+)\.\s*([A-Z0-9]{1,16})(?:\s*-\s*(.+))?\s*$")
    for i, line in enumerate(lines):
        m = header_re.match(line.strip())
        if not m:
            continue
        rank = int(m.group(1))
        symbol = m.group(2).upper()
        sector_raw = m.group(3).strip() if m.group(3) else None
        if sector_raw:
            sector_raw = sector_raw.replace("⭐", "").strip()
        starts.append((i, rank, symbol, sector_raw))

    signals: list[BuySignalIn] = []
    for idx, (start_line, rank, symbol, sector_from_header) in enumerate(starts):
        end_line = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        block = "\n".join(lines[start_line:end_line])

        recommendation = None
        rec_match = re.search(r"Khuyến nghị\s*[:\-]\s*(.+)", block, re.IGNORECASE)
        if rec_match:
            recommendation = rec_match.group(1).strip()[:200]

        sector = sector_from_header
        if not sector:
            sector_match = re.search(r"Ngành\s*[:\-]\s*(.+)", block, re.IGNORECASE)
            if sector_match:
                sector = sector_match.group(1).strip()[:200]

        price = None
        price_patterns = [
            r"Giá hiện tại\s*([0-9][0-9\.,\s]*)\s*VND",
            r"Giá\s*\(VND\)\s*[:\-]?\s*([0-9][0-9\.,\s]*)",
            r"Giá\s*[:\-]\s*([0-9][0-9\.,\s]*)\s*VND",
        ]
        for patt in price_patterns:
            m = re.search(patt, block, re.IGNORECASE)
            if not m:
                continue
            price = _to_number(m.group(1))
            if price is not None:
                break

        if valid_symbols and symbol not in valid_symbols:
            continue
        signals.append(
            BuySignalIn(
                rank=rank,
                symbol=symbol,
                recommendation=recommendation,
                sector=sector,
                price=price,
            )
        )

    if not signals:
        # Fallback: parse any uppercase symbol line with nearby price.
        symbol_candidates: dict[str, float | None] = {}
        symbol_line_re = re.compile(r"\b([A-Z]{2,5})\b")
        price_re = re.compile(r"([0-9][0-9\.,\s]{2,})\s*VND", re.IGNORECASE)
        for line in lines:
            found_syms = [m.group(1) for m in symbol_line_re.finditer(line)]
            if not found_syms:
                continue
            px_match = price_re.search(line)
            price_val = _to_number(px_match.group(1)) if px_match else None
            for sym in found_syms:
                if sym in {"VND", "TOP", "RSI", "MACD", "SMA", "ADX"}:
                    continue
                if valid_symbols and sym not in valid_symbols:
                    continue
                if sym not in symbol_candidates:
                    symbol_candidates[sym] = price_val
        rank = 1
        for sym, px in symbol_candidates.items():
            signals.append(BuySignalIn(rank=rank, symbol=sym, price=px))
            rank += 1
            if rank > 3:
                break

    if not signals:
        raise ValueError("Không tìm thấy buy_signals hợp lệ")
    return signals


def parse_signal_output_text(text: str, valid_symbols: set[str] | None = None) -> ParsedSignalText:
    raw_text = text
    if not raw_text or not raw_text.strip():
        raise ValueError("Không tìm thấy buy_signals hợp lệ")
    title = _first_non_empty_line(raw_text)
    ref_date = _extract_reference_date(raw_text)
    signals = _parse_buy_signals(raw_text, valid_symbols=valid_symbols)
    return ParsedSignalText(
        title=title[:200] if title else None,
        reference_date=ref_date,
        raw_text=raw_text,
        buy_signals=signals,
    )


def _build_gemini_prompt(base_prompt: str, snapshot: dict[str, Any], sector_flow: dict[str, Any]) -> str:
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
        "Hãy trả kết quả đúng format phân tích và danh sách TOP tín hiệu mua theo prompt."
    )


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


def _extract_valid_symbols(snapshot: dict[str, Any]) -> set[str]:
    payload = snapshot.get("payload") if isinstance(snapshot.get("payload"), dict) else snapshot
    if not isinstance(payload, dict):
        return set()
    symbols = payload.get("symbols")
    if not isinstance(symbols, list):
        return set()
    out: set[str] = set()
    for item in symbols:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("symbol") or "").strip().upper()
        if sym:
            out.add(sym)
    return out


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


async def _http_json(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    response = await client.request(method, url, **kwargs)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected JSON payload from {url}")
    return data


async def _run_gemini(prompt: str) -> str:
    if not settings.google_gemini_api_key:
        raise RuntimeError("Missing GOOGLE_GEMINI_API_KEY")
    model = settings.gemini_model.strip() or "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.google_gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    timeout = max(30, int(settings.automation_http_timeout_seconds))
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = await _http_json(client, "POST", url, json=payload)

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Gemini response has no candidates")
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        raise RuntimeError("Gemini response has invalid content parts")
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    out = "\n".join(chunks).strip()
    if not out:
        raise RuntimeError("Gemini returned empty text")
    return out


async def _already_ingested(db: AsyncSession, ref_date: date) -> bool:
    q = select(SignalEntry.id).where(
        SignalEntry.reference_date == ref_date,
        SignalEntry.deleted_at.is_(None),
        SignalEntry.data_extracted.is_(True),
        text("payload->>'source' = 'automation-daily-gemini'"),
    )
    row = (await db.execute(q)).first()
    return row is not None


async def run_daily_balanced_automation(
    db: AsyncSession,
    *,
    dry_run: bool = False,
    force: bool = False,
    use_mock_result: bool = False,
    prompt_file_path: str | None,
) -> DailyAutomationResponse:
    run_id = uuid.uuid4().hex
    steps: list[AutomationStepResult] = []
    base_url = settings.automation_base_url.rstrip("/")
    timeout = max(30, int(settings.automation_http_timeout_seconds))

    async with httpx.AsyncClient(timeout=timeout) as client:
        refresh_url = f"{base_url}/api/v1/newfeeds/refresh-prices"
        refresh_data = await _http_json(client, "GET", refresh_url)
        steps.append(
            AutomationStepResult(
                name="refresh_prices",
                ok=True,
                detail="Price refresh completed",
                payload={"total": refresh_data.get("total")},
            )
        )

        sync_url = f"{base_url}/api/v1/balanced/sync"
        sync_data = await _http_json(client, "GET", sync_url)
        steps.append(
            AutomationStepResult(
                name="balanced_sync",
                ok=True,
                detail="Balanced sync completed",
                payload={
                    "as_of_date": sync_data.get("as_of_date"),
                    "symbols_ok": sync_data.get("symbols_ok"),
                },
            )
        )

        snapshot_url = f"{base_url}/api/v1/balanced/snapshot"
        snapshot_data = await _http_json(client, "GET", snapshot_url)
        snapshot_payload = snapshot_data.get("payload") if isinstance(snapshot_data.get("payload"), dict) else snapshot_data

        sector_url = f"{base_url}/api/v1/balanced/sector-flow-5d"
        sector_data = await _http_json(client, "GET", sector_url)
        steps.append(
            AutomationStepResult(
                name="load_balanced_data",
                ok=True,
                detail="Loaded snapshot + sector flow",
                payload={"snapshot_found": bool(snapshot_data.get("found")), "sector_found": bool(sector_data.get("found"))},
            )
        )

        if prompt_file_path:
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                base_prompt = f.read()
        else:
            base_prompt = (
                "Tìm TOP tín hiệu mua BALANCED theo dữ liệu snapshot và sector-flow-5d. "
                "Bắt buộc xuất tiêu đề có mẫu 'TÍN HIỆU MUA BALANCED - NGÀY dd/mm/yyyy' "
                "và danh sách #1/#2/#3 theo format '#<rank>. <SYMBOL> - <SECTOR>' kèm giá hiện tại VND."
            )
        full_prompt = _build_gemini_prompt(base_prompt, snapshot_payload, sector_data)
        if use_mock_result:
            today = date.today().strftime("%d/%m/%Y")
            ai_text = (
                f"TÍN HIỆU MUA BALANCED - NGÀY {today}\n"
                f"Phân tích dựa trên dữ liệu ngày {today}\n\n"
                "#1. TIG - BẤT ĐỘNG SẢN\n"
                "Giá hiện tại 6,700 VND\n\n"
                "#2. HPA - THỰC PHẨM VÀ ĐỒ UỐNG\n"
                "Giá hiện tại 37,500 VND\n"
            )
        else:
            ai_text = await _run_gemini(full_prompt)
        steps.append(
            AutomationStepResult(
                name="run_gemini",
                ok=True,
                detail="Gemini generated analysis output" if not use_mock_result else "Mock analysis output generated",
                payload={"chars": len(ai_text), "mock_mode": use_mock_result},
            )
        )

        valid_symbols = _extract_valid_symbols(snapshot_payload)
        parsed = parse_signal_output_text(ai_text, valid_symbols=valid_symbols)
        steps.append(
            AutomationStepResult(
                name="parse_output",
                ok=True,
                detail="Parsed AI output into ingest payload",
                payload={"reference_date": parsed.reference_date.isoformat(), "buy_signal_count": len(parsed.buy_signals)},
            )
        )

        if not force and await _already_ingested(db, parsed.reference_date):
            return DailyAutomationResponse(
                ok=True,
                run_id=run_id,
                skipped=True,
                reason=f"Entry for {parsed.reference_date.isoformat()} already ingested",
                reference_date=parsed.reference_date,
                title=parsed.title,
                buy_signals=parsed.buy_signals,
                raw_text_preview=parsed.raw_text[:500],
                steps=steps,
            )

        if dry_run:
            return DailyAutomationResponse(
                ok=True,
                run_id=run_id,
                skipped=True,
                reason="dry_run=true, skip ingest step",
                reference_date=parsed.reference_date,
                title=parsed.title,
                buy_signals=parsed.buy_signals,
                raw_text_preview=parsed.raw_text[:500],
                steps=steps,
            )

        ingest_url = f"{base_url}/api/v1/admin/signal-entries/ingest-agent"
        ingest_payload = {
            "title": parsed.title,
            "reference_date": parsed.reference_date.isoformat(),
            "raw_text": parsed.raw_text,
            "buy_signals": [item.model_dump(mode="json") for item in parsed.buy_signals],
        }
        ingest_data = await _http_json(client, "POST", ingest_url, json=ingest_payload)
        created_id = ingest_data.get("id")

    if created_id is not None:
        row = await db.get(SignalEntry, created_id)
        if row and isinstance(row.payload, dict):
            new_payload = dict(row.payload)
            new_payload["source"] = "automation-daily-gemini"
            meta = new_payload.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta["run_id"] = run_id
            new_payload["meta"] = meta
            row.payload = new_payload
            await db.commit()

    steps.append(
        AutomationStepResult(
            name="ingest_entry",
            ok=True,
            detail="Ingested parsed result into signal entries",
            payload={"entry_id": created_id},
        )
    )

    return DailyAutomationResponse(
        ok=True,
        run_id=run_id,
        reference_date=parsed.reference_date,
        title=parsed.title,
        buy_signals=parsed.buy_signals,
        raw_text_preview=parsed.raw_text[:500],
        steps=steps,
    )
