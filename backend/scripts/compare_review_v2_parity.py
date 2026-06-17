#!/usr/bin/env python3
"""So sánh symbol set review v1 (text filter) vs review v2 (struct filter) trên cùng payload."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Allow `python scripts/compare_review_v2_parity.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.review_v2_service import passes_review_display_filter


def v1_text_filter(why_selected: list[str]) -> bool:
    has_sector = any(re.search(r"Dòng tiền ngành dương", r, re.I) for r in why_selected)
    has_vol = any(
        re.search(r"Khối lượng phiên mới nhất cao hơn trung bình 5 phiên", r, re.I)
        for r in why_selected
    )
    return has_sector and has_vol


def symbols_from_entry_payload(payload: dict) -> tuple[list[str], list[str]]:
    buy_signals = payload.get("buy_signals") if isinstance(payload.get("buy_signals"), list) else []
    v1: list[str] = []
    struct_rows: list[dict] = []
    for raw in buy_signals:
        if not isinstance(raw, dict):
            continue
        sym = str(raw.get("symbol") or "").strip().upper()
        if not sym:
            continue
        why = [str(x) for x in (raw.get("why_selected") or []) if str(x).strip()]
        if v1_text_filter(why):
            v1.append(sym)
        struct_rows.append(
            {
                "symbol": sym,
                "sector_flow_pct": raw.get("sector_flow_pct"),
                "indicators": {
                    "total_volume_latest": None,
                    "avg_volume_5d": None,
                },
            }
        )
    return sorted(set(v1)), struct_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare review v1 vs v2 symbol sets from signal entry JSON")
    parser.add_argument("payload_file", type=Path, help="JSON file with buy_signals[]")
    args = parser.parse_args()
    payload = json.loads(args.payload_file.read_text(encoding="utf-8"))
    v1_syms, _ = symbols_from_entry_payload(payload)
    print("v1_text_symbols", v1_syms)
    print("count", len(v1_syms))
    print("note: v2 live symbols require compute_review_v2_candidates() — run against API for full parity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
