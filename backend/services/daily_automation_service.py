from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from sqlalchemy import select
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


@dataclass
class ParsedGeminiJson:
    title: str | None
    reference_date: date
    buy_signals: list[BuySignalIn]
    raw_text: str


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


def _parse_reference_date_value(value: Any) -> date:
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return date.fromisoformat(s)
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s)
        if m:
            dd, mm, yyyy = m.groups()
            return date(int(yyyy), int(mm), int(dd))
    raise ValueError("Không trích xuất được reference_date")


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
        "BẮT BUỘC trả về JSON object hợp lệ (không markdown, không text ngoài JSON) theo schema sau:\n"
        "{\n"
        '  "title": "string",\n'
        '  "reference_date": "YYYY-MM-DD",\n'
        '  "reason": "string (tiếng Việt, BẮT BUỘC, tối thiểu 200 ký tự sau khi trim): giải thích chi tiết toàn bộ suy luận — '
        "cách áp dụng 8 điều kiện bắt buộc + loại trừ tin tức, cách xếp hạng selected_signals, "
        "mối liên hệ với sector-flow-5d và screened_candidates (nếu có), vì sao loại các mã gần đạt; "
        "nếu selected_signals rỗng thì giải thích rõ vì sao không có mã đạt hoặc vì sao không thể điền danh sách.\",\n"
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
        "Ràng buộc: selected_signals không giới hạn số lượng, symbol phải thuộc dữ liệu snapshot; "
        'trường "reason" không được rút gọn hoặc bỏ qua — phải là đoạn văn đầy đủ, có thể nhiều câu và xuống dòng (\\n).'
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


def _fallback_signals_from_snapshot(snapshot: dict[str, Any], valid_symbols: set[str]) -> list[BuySignalIn]:
    payload = snapshot.get("payload") if isinstance(snapshot.get("payload"), dict) else snapshot
    if not isinstance(payload, dict):
        return []
    screened = payload.get("screened_candidates") or payload.get("screened_top3")
    if not isinstance(screened, list):
        return []
    out: list[BuySignalIn] = []
    rank = 1
    symbol_map = _snapshot_symbol_map(snapshot)
    for row in screened:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym or (valid_symbols and sym not in valid_symbols):
            continue
        indicators = row.get("indicators") if isinstance(row.get("indicators"), dict) else {}
        out.append(
            BuySignalIn(
                rank=rank,
                symbol=sym,
                sector=str(row.get("sector")).strip() if row.get("sector") is not None else None,
                price=float(indicators.get("price_close_vnd")) if indicators.get("price_close_vnd") is not None else None,
                recommendation="THEO DÕI MUA",
                why_selected=_fallback_why_selected(sym, symbol_map.get(sym)),
            )
        )
        rank += 1
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


async def _run_gemini(prompt: str) -> dict[str, Any]:
    if not settings.google_gemini_api_key:
        raise RuntimeError("Missing GOOGLE_GEMINI_API_KEY")
    model = settings.gemini_model.strip() or "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.google_gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.05,
            "responseMimeType": "application/json",
            "maxOutputTokens": 8192,
        },
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
    try:
        obj = json.loads(out)
    except Exception:
        repair_payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Convert the following malformed JSON-like text into VALID JSON object only. "
                                "Do not add markdown. Preserve all keys from the original if possible; "
                                'if the object lacks a top-level string field "reason" with at least 200 characters '
                                "of Vietnamese explanation of the analysis outcome, synthesize one from the content.\n\n"
                                f"{out}"
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
                "maxOutputTokens": 8192,
            },
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            repaired_data = await _http_json(client, "POST", url, json=repair_payload)
        repaired_candidates = repaired_data.get("candidates")
        if not isinstance(repaired_candidates, list) or not repaired_candidates:
            raise RuntimeError("Gemini JSON repair failed: no candidates")
        repaired_content = repaired_candidates[0].get("content") if isinstance(repaired_candidates[0], dict) else None
        repaired_parts = repaired_content.get("parts") if isinstance(repaired_content, dict) else None
        repaired_text = ""
        if isinstance(repaired_parts, list):
            repaired_text = "\n".join(
                [p.get("text") for p in repaired_parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
            ).strip()
        try:
            obj = json.loads(repaired_text)
        except Exception as e:
            raise RuntimeError(f"Gemini JSON parse failed: {e}") from e
    if not isinstance(obj, dict):
        raise RuntimeError("Gemini response is not a JSON object")
    return obj


def _extract_required_reason(obj: dict[str, Any]) -> str:
    """Gemini bắt buộc trả `reason` — giải thích tổng hợp kết quả JSON."""
    r = obj.get("reason")
    if not isinstance(r, str):
        raise ValueError(
            'Thiếu trường JSON "reason" (kiểu string). AI phải giải thích chi tiết vì sao có kết quả output như vậy.'
        )
    s = r.strip()
    if len(s) < 200:
        raise ValueError(
            'Trường "reason" phải dài tối thiểu 200 ký tự (sau trim) — mô tả đầy đủ suy luận: điều kiện, ưu tiên, loại trừ, sector-flow.'
        )
    return s


def _render_raw_text_from_json(
    title: str,
    ref_date: date,
    sector_flow_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    near_miss_rows: list[dict[str, Any]],
    analysis_notes: str | None,
    output_reason: str | None = None,
) -> str:
    lines: list[str] = [title, f"Phân tích dựa trên dữ liệu ngày {ref_date.strftime('%d/%m/%Y')}", ""]
    if output_reason and output_reason.strip():
        lines.append("## Giải thích kết quả (AI)")
        lines.append(output_reason.strip())
        lines.append("")
    lines.append("## Dòng tiền ngành phiên chạy vs trung bình 5 phiên")
    for row in sector_flow_rows:
        sector = str(row.get("sector") or "N/A")
        flow_today = row.get("flow_today_vnd")
        avg5 = row.get("avg_5d_vnd")
        pct = row.get("pct_vs_5d")
        lines.append(f"- {sector}: today={flow_today}, avg5={avg5}, pct_vs_5d={pct}")
    lines.append("")
    lines.append("## Cổ phiếu được chọn và lý do")
    for idx, row in enumerate(selected_rows, start=1):
        sym = str(row.get("symbol") or "").upper()
        sec = row.get("sector")
        rec = row.get("recommendation")
        price = row.get("price")
        why = row.get("why_selected") if isinstance(row.get("why_selected"), list) else []
        lines.append(f"#{idx}. {sym}" + (f" - {sec}" if sec else ""))
        lines.append(f"Khuyến nghị: {rec}" if rec else "Khuyến nghị: N/A")
        lines.append(f"Giá hiện tại {price} VND" if price is not None else "Giá hiện tại N/A")
        if why:
            for reason in why:
                lines.append(f"- {reason}")
    lines.append("")
    lines.append("## Cổ phiếu gần đạt điều kiện")
    for row in near_miss_rows:
        sym = str(row.get("symbol") or "").upper()
        sec = row.get("sector")
        fails = row.get("failed_conditions") if isinstance(row.get("failed_conditions"), list) else []
        lines.append(f"- {sym}" + (f" ({sec})" if sec else ""))
        for f in fails:
            lines.append(f"  - {f}")
    if analysis_notes:
        lines.append("")
        lines.append("## Ghi chú phân tích")
        lines.append(analysis_notes)
    return "\n".join(lines).strip()


def _build_default_sector_flow_rows(sector_flow_payload: dict[str, Any], top_n: int = 8) -> list[dict[str, Any]]:
    sectors = sector_flow_payload.get("sectors")
    if not isinstance(sectors, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in sectors:
        if not isinstance(item, dict):
            continue
        points = item.get("points") if isinstance(item.get("points"), list) else []
        vals = [float(p.get("positive_money_flow_vnd")) for p in points if isinstance(p, dict) and p.get("positive_money_flow_vnd") is not None]
        if not vals:
            continue
        flow_today = vals[-1]
        avg_5d = sum(vals[-5:]) / min(5, len(vals))
        pct = ((flow_today - avg_5d) / avg_5d * 100.0) if avg_5d != 0 else None
        rows.append(
            {
                "sector": item.get("sector"),
                "flow_today_vnd": round(flow_today, 4),
                "avg_5d_vnd": round(avg_5d, 4),
                "pct_vs_5d": round(pct, 4) if pct is not None else None,
            }
        )
    rows.sort(key=lambda x: x.get("pct_vs_5d") if x.get("pct_vs_5d") is not None else -999999, reverse=True)
    return rows[:top_n]


def _build_default_near_miss(snapshot_payload: dict[str, Any], selected_symbols: set[str], top_n: int = 5) -> list[dict[str, Any]]:
    payload = snapshot_payload.get("payload") if isinstance(snapshot_payload.get("payload"), dict) else snapshot_payload
    if not isinstance(payload, dict):
        return []
    symbols = payload.get("symbols")
    if not isinstance(symbols, list):
        return []
    candidates: list[tuple[int, dict[str, Any]]] = []
    for item in symbols:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").strip().upper()
        if not symbol or symbol in selected_symbols:
            continue
        ind = item.get("indicators") if isinstance(item.get("indicators"), dict) else {}
        sector_flow_pct = item.get("sector_flow_pct")
        checks = {
            "RSI 30-45": ind.get("rsi14") is not None and 30 <= float(ind.get("rsi14")) <= 45,
            "Dòng tiền ngành > 0": sector_flow_pct is not None and float(sector_flow_pct) > 0,
            "Volume > TB5": ind.get("total_volume_latest") is not None and ind.get("avg_volume_5d") is not None and float(ind.get("total_volume_latest")) > float(ind.get("avg_volume_5d")),
            "Volume ratio 1.0-2.0": ind.get("volume_ratio") is not None and 1.0 <= float(ind.get("volume_ratio")) <= 2.0,
            "Volume >=100k": ind.get("total_volume_latest") is not None and float(ind.get("total_volume_latest")) >= 100000,
            "MACD > 0": ind.get("macd_hist") is not None and float(ind.get("macd_hist")) > 0,
            "SMA5/SMA20 >= 0.92": ind.get("sma5_over_sma20") is not None and float(ind.get("sma5_over_sma20")) >= 0.92,
            "ADX >= 15": ind.get("adx14") is not None and float(ind.get("adx14")) >= 15,
        }
        passed = sum(1 for v in checks.values() if v)
        if passed >= 8:
            continue
        failed = [k for k, v in checks.items() if not v]
        candidates.append((passed, {"symbol": symbol, "sector": item.get("sector"), "failed_conditions": failed[:4]}))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in candidates[:top_n]]


def _snapshot_symbol_map(snapshot_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = snapshot_payload.get("payload") if isinstance(snapshot_payload.get("payload"), dict) else snapshot_payload
    if not isinstance(payload, dict):
        return {}
    symbols = payload.get("symbols")
    if not isinstance(symbols, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in symbols:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "").strip().upper()
        if sym:
            out[sym] = row
    return out


def _f(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def _fallback_why_selected(symbol: str, snapshot_row: dict[str, Any] | None) -> list[str]:
    if not snapshot_row:
        return ["Đạt bộ lọc kỹ thuật/sector-flow theo snapshot hiện tại."]
    ind = snapshot_row.get("indicators") if isinstance(snapshot_row.get("indicators"), dict) else {}
    reasons: list[str] = []
    rsi = _f(ind.get("rsi14"))
    if rsi is not None and 30 <= rsi <= 45:
        reasons.append(f"RSI14 {rsi:.2f} nằm trong vùng 30-45.")
    macd = _f(ind.get("macd_hist"))
    if macd is not None and macd > 0:
        reasons.append(f"MACD histogram dương ({macd:.4f}).")
    sma_ratio = _f(ind.get("sma5_over_sma20"))
    if sma_ratio is not None and sma_ratio >= 0.92:
        reasons.append(f"Tỷ lệ SMA5/SMA20 đạt {sma_ratio:.3f} (>= 0.92).")
    adx = _f(ind.get("adx14"))
    if adx is not None and adx >= 15:
        reasons.append(f"ADX14 đạt {adx:.2f} (>= 15).")
    vol_ratio = _f(ind.get("volume_ratio"))
    if vol_ratio is not None and 1.0 <= vol_ratio <= 2.0:
        reasons.append(f"Volume ratio {vol_ratio:.2f} nằm trong dải 1.0-2.0.")
    vol = _f(ind.get("total_volume_latest"))
    avg5 = _f(ind.get("avg_volume_5d"))
    if vol is not None and vol >= 100000:
        reasons.append(f"Thanh khoản đạt {int(vol):,} cổ phiếu (>= 100k).".replace(",", "."))
    if vol is not None and avg5 is not None and vol > avg5:
        reasons.append(
            f"Khối lượng phiên mới nhất cao hơn trung bình 5 phiên ({int(vol):,} > {int(avg5):,}).".replace(",", ".")
        )
    sector_flow_pct = _f(snapshot_row.get("sector_flow_pct"))
    if sector_flow_pct is not None and sector_flow_pct > 0:
        reasons.append(f"Dòng tiền ngành dương so với TB5 ({sector_flow_pct:.2f}%).")
    return reasons[:6] if reasons else ["Đạt bộ lọc kỹ thuật/sector-flow theo snapshot hiện tại."]


def _parse_gemini_json_output(
    obj: dict[str, Any],
    valid_symbols: set[str],
    snapshot_payload: dict[str, Any],
    sector_flow_payload: dict[str, Any],
) -> ParsedGeminiJson:
    title = str(obj.get("title") or "").strip() or "TÍN HIỆU MUA BALANCED"
    ref_date = _parse_reference_date_value(obj.get("reference_date"))
    output_reason = _extract_required_reason(obj)
    selected = obj.get("selected_signals") if isinstance(obj.get("selected_signals"), list) else []
    symbol_map = _snapshot_symbol_map(snapshot_payload)
    buy_signals: list[BuySignalIn] = []
    selected_rows: list[dict[str, Any]] = []
    for row in selected:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym or (valid_symbols and sym not in valid_symbols):
            continue
        rank = row.get("rank")
        price = row.get("price")
        try:
            price_val = float(price) if price is not None else None
        except Exception:
            price_val = None
        why = (
            [str(x).strip() for x in row.get("why_selected", []) if str(x).strip()]
            if isinstance(row.get("why_selected"), list)
            else []
        )
        if not why:
            why = _fallback_why_selected(sym, symbol_map.get(sym))

        signal = BuySignalIn(
            rank=int(rank) if isinstance(rank, (int, float)) else None,
            symbol=sym,
            recommendation=str(row.get("recommendation")).strip() if row.get("recommendation") is not None else None,
            sector=str(row.get("sector")).strip() if row.get("sector") is not None else None,
            price=price_val,
            why_selected=why,
        )
        buy_signals.append(signal)
        selected_row = dict(row)
        selected_row["why_selected"] = why
        selected_rows.append(selected_row)
    if not buy_signals:
        buy_signals = _fallback_signals_from_snapshot(snapshot_payload, valid_symbols)
    if not buy_signals:
        raise ValueError("Không tìm thấy buy_signals hợp lệ")
    sector_flow_rows = obj.get("sector_flow_analysis") if isinstance(obj.get("sector_flow_analysis"), list) else []
    near_miss_rows = obj.get("near_miss_signals") if isinstance(obj.get("near_miss_signals"), list) else []
    if not sector_flow_rows:
        sector_flow_rows = _build_default_sector_flow_rows(sector_flow_payload)
    if not near_miss_rows:
        near_miss_rows = _build_default_near_miss(snapshot_payload, selected_symbols={s.symbol for s in buy_signals})
    analysis_notes = str(obj.get("analysis_notes")).strip() if obj.get("analysis_notes") is not None else None
    raw_text = _render_raw_text_from_json(
        title=title,
        ref_date=ref_date,
        sector_flow_rows=[x for x in sector_flow_rows if isinstance(x, dict)],
        selected_rows=selected_rows,
        near_miss_rows=[x for x in near_miss_rows if isinstance(x, dict)],
        analysis_notes=analysis_notes,
        output_reason=output_reason,
    )
    return ParsedGeminiJson(title=title[:200], reference_date=ref_date, buy_signals=buy_signals, raw_text=raw_text)


async def _already_ingested(db: AsyncSession, ref_date: date) -> bool:
    """Any existing automation-generated row for this date counts as already run.

    We treat both pending-review (data_extracted=False) and published rows as
    "already ingested" so the job runs at most once per day.
    """
    q = select(SignalEntry.id, SignalEntry.payload).where(
        SignalEntry.reference_date == ref_date,
        SignalEntry.deleted_at.is_(None),
    )
    rows = (await db.execute(q)).all()
    for row_id, payload in rows:
        if not row_id:
            continue
        if not isinstance(payload, dict):
            continue
        source = str(payload.get("source") or "").strip().lower()
        if source in {"cursor-agent", "automation-daily-gemini"}:
            return True
    return False


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
                "và danh sách '#<rank>. <SYMBOL> - <SECTOR>' kèm giá hiện tại VND."
            )
        full_prompt = _build_gemini_prompt(base_prompt, snapshot_payload, sector_data)
        valid_symbols = _extract_valid_symbols(snapshot_payload)
        if use_mock_result:
            today_iso = date.today().isoformat()
            gemini_obj: dict[str, Any] = {
                "title": f"TÍN HIỆU MUA BALANCED - NGÀY {date.today().strftime('%d/%m/%Y')}",
                "reference_date": today_iso,
                "reason": (
                    "Đây là chế độ mock: pipeline không gọi Gemini thật. "
                    "Trong production, trường `reason` bắt buộc phải là đoạn văn tiếng Việt dài đủ (≥200 ký tự) "
                    "giải thích tổng thể vì sao danh sách `selected_signals` được chọn theo đúng 8 điều kiện bắt buộc + loại trừ tin tức, "
                    "cách đối chiếu sector-flow 5 phiên và screened_candidates, vì sao xếp thứ tự rank như vậy, "
                    "và nếu không có mã đạt thì phải nêu rõ nguyên nhân từng nhóm điều kiện thiếu hoặc vi phạm."
                ),
                "sector_flow_analysis": [],
                "selected_signals": [
                    {
                        "rank": 1,
                        "symbol": "TIG" if "TIG" in valid_symbols else next(iter(valid_symbols), "VCB"),
                        "sector": "Bất động sản",
                        "price": 6700,
                        "recommendation": "THEO DÕI MUA",
                        "why_selected": ["Mock test"],
                    }
                ],
                "near_miss_signals": [],
                "analysis_notes": "Mock mode",
            }
        else:
            gemini_obj = await _run_gemini(full_prompt)
        gemini_json_str = json.dumps(gemini_obj, ensure_ascii=False)
        steps.append(
            AutomationStepResult(
                name="run_gemini",
                ok=True,
                detail="Gemini generated analysis output" if not use_mock_result else "Mock analysis output generated",
                payload={"chars": len(gemini_json_str), "mock_mode": use_mock_result},
            )
        )

        parsed_json = _parse_gemini_json_output(
            gemini_obj,
            valid_symbols=valid_symbols,
            snapshot_payload=snapshot_payload,
            sector_flow_payload=sector_data,
        )
        parsed = ParsedSignalText(
            title=parsed_json.title,
            reference_date=parsed_json.reference_date,
            raw_text=parsed_json.raw_text,
            buy_signals=parsed_json.buy_signals,
        )
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
            meta["review_required"] = True
            meta["gemini_output"] = gemini_obj
            new_payload["meta"] = meta
            row.payload = new_payload
            row.data_extracted = False
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
