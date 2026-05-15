"""Unit tests cho automation snapshot-only (reference_date + screened_all fallback)."""

from __future__ import annotations

import unittest
from datetime import date

from services.daily_automation_service import (
    _build_snapshot_only_analysis_obj,
    _fallback_signals_from_snapshot,
    _parse_gemini_json_output,
    _reference_date_from_balanced_payloads,
)


class ReferenceDateFromPayloadsTests(unittest.TestCase):
    def test_prefers_snapshot_as_of_date(self) -> None:
        snap = {"as_of_date": "2026-03-10"}
        sector = {"as_of_date": "2026-01-01"}
        self.assertEqual(_reference_date_from_balanced_payloads(snap, sector), date(2026, 3, 10))

    def test_falls_back_to_sector(self) -> None:
        snap: dict = {}
        sector = {"as_of_date": "2026-02-20"}
        self.assertEqual(_reference_date_from_balanced_payloads(snap, sector), date(2026, 2, 20))

    def test_invalid_iso_falls_through(self) -> None:
        snap = {"as_of_date": "not-a-date"}
        sector = {"as_of_date": "2026-04-01"}
        self.assertEqual(_reference_date_from_balanced_payloads(snap, sector), date(2026, 4, 1))


class FallbackScreenedAllTests(unittest.TestCase):
    def _row(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "sector": "Sec",
            "indicators": {"price_close_vnd": 1000.0},
        }

    def test_screened_all_returns_all_passing(self) -> None:
        rows = [self._row("AAA"), self._row("BBB"), self._row("CCC"), self._row("DDD")]
        snap = {"payload": {"screened_all": rows, "screened_top3": rows[:3]}}
        valid = {"AAA", "BBB", "CCC", "DDD"}
        sigs = _fallback_signals_from_snapshot(snap, valid)
        self.assertEqual([s.symbol for s in sigs], ["AAA", "BBB", "CCC", "DDD"])
        self.assertEqual([s.rank for s in sigs], [1, 2, 3, 4])

    def test_legacy_only_top3_max_three(self) -> None:
        rows = [self._row("AAA"), self._row("BBB"), self._row("CCC")]
        snap = {"payload": {"screened_top3": rows}}
        valid = {"AAA", "BBB", "CCC"}
        sigs = _fallback_signals_from_snapshot(snap, valid)
        self.assertEqual(len(sigs), 3)

    def test_empty_screened_all_falls_back_to_top3(self) -> None:
        rows = [self._row("X"), self._row("Y")]
        snap = {"payload": {"screened_all": [], "screened_top3": rows}}
        valid = {"X", "Y"}
        sigs = _fallback_signals_from_snapshot(snap, valid)
        self.assertEqual([s.symbol for s in sigs], ["X", "Y"])


class ParseSnapshotOnlySyntheticTests(unittest.TestCase):
    def test_parse_empty_selected_uses_screened_all(self) -> None:
        ref = date(2026, 5, 1)
        obj = _build_snapshot_only_analysis_obj(ref)
        rows = [
            {"symbol": "AAA", "sector": "S", "indicators": {"price_close_vnd": 1.0}},
            {"symbol": "BBB", "sector": "S", "indicators": {"price_close_vnd": 2.0}},
        ]
        snapshot_payload = {"as_of_date": "2026-05-01", "screened_all": rows, "symbols": [{"symbol": "AAA"}, {"symbol": "BBB"}]}
        sector = {"sectors": []}
        valid = {"AAA", "BBB"}
        out = _parse_gemini_json_output(obj, valid, snapshot_payload, sector)
        self.assertEqual(len(out.buy_signals), 2)
        self.assertIn("AAA", out.raw_text)
        self.assertIn("BBB", out.raw_text)


if __name__ == "__main__":
    unittest.main()
