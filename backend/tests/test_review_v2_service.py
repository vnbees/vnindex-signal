"""Unit tests for Review v2 display filter and parity helpers."""

import unittest

from services.review_v2_service import passes_review_display_filter


def review_v1_text_filter(why_selected: list[str]) -> bool:
    """Mirror legacy frontend regex filter on why_selected."""
    has_sector = any("Dòng tiền ngành dương" in r for r in why_selected)
    has_vol = any("Khối lượng phiên mới nhất cao hơn trung bình 5 phiên" in r for r in why_selected)
    return has_sector and has_vol


def parity_symbol_sets(
  v1_signals: list[dict],
  v2_rows: list[dict],
) -> dict[str, list[str]]:
    """Compare symbol sets: v1 uses text filter on why_selected; v2 uses struct rows."""
    v1_syms = sorted(
        s["symbol"]
        for s in v1_signals
        if review_v1_text_filter(s.get("why_selected") or [])
    )
    v2_syms = sorted(
        str(r.get("symbol") or "").upper()
        for r in v2_rows
        if passes_review_display_filter(r)
    )
    v1_set, v2_set = set(v1_syms), set(v2_syms)
    return {
        "only_v1": sorted(v1_set - v2_set),
        "only_v2": sorted(v2_set - v1_set),
        "both": sorted(v1_set & v2_set),
    }


class ReviewV2DisplayFilterTests(unittest.TestCase):
    def test_passes_when_sector_positive_and_volume_above_avg5(self) -> None:
        row = {
            "sector_flow_pct": 12.5,
            "indicators": {"total_volume_latest": 200000, "avg_volume_5d": 100000},
        }
        self.assertTrue(passes_review_display_filter(row))

    def test_fails_when_sector_not_positive(self) -> None:
        row = {
            "sector_flow_pct": -1.0,
            "indicators": {"total_volume_latest": 200000, "avg_volume_5d": 100000},
        }
        self.assertFalse(passes_review_display_filter(row))

    def test_fails_when_volume_not_above_avg5(self) -> None:
        row = {
            "sector_flow_pct": 5.0,
            "indicators": {"total_volume_latest": 100000, "avg_volume_5d": 150000},
        }
        self.assertFalse(passes_review_display_filter(row))

    def test_v2_superset_when_v1_text_truncated(self) -> None:
        """Struct v2 can include symbols v1 misses when why_selected lacks both lines (cap 6)."""
        v1_signals = [
            {
                "symbol": "AAA",
                "why_selected": [
                    "RSI14 40.00 nằm trong vùng 30-45.",
                    "MACD histogram dương (1.0).",
                    "Tỷ lệ SMA5/SMA20 đạt 0.980 (>= 0.92).",
                    "ADX14 đạt 20.00 (>= 15).",
                    "Volume ratio 1.20 nằm trong dải 1.0-2.0.",
                    "Thanh khoản đạt 500.000 cổ phiếu (>= 100k).",
                ],
            }
        ]
        v2_rows = [
            {
                "symbol": "AAA",
                "sector_flow_pct": 10.0,
                "indicators": {"total_volume_latest": 600000, "avg_volume_5d": 400000},
            }
        ]
        diff = parity_symbol_sets(v1_signals, v2_rows)
        self.assertEqual(diff["only_v1"], [])
        self.assertEqual(diff["only_v2"], ["AAA"])
        self.assertEqual(diff["both"], [])


if __name__ == "__main__":
    unittest.main()
