import unittest
from services.daily_automation_service import _parse_gemini_json_output, parse_signal_output_text


SAMPLE_TEXT = """🎯 TÍN HIỆU MUA BALANCED - NGÀY 22/04/2026
Phân tích dựa trên dữ liệu ngày 22/04/2026

#1. TIG - BẤT ĐỘNG SẢN ⭐
Giá hiện tại 6,700 VND

#2. HPA - THỰC PHẨM VÀ ĐỒ UỐNG ⭐
Giá hiện tại 37,500 VND
"""


class DailyAutomationParserTests(unittest.TestCase):
    def test_parse_valid_text(self) -> None:
        parsed = parse_signal_output_text(SAMPLE_TEXT)
        self.assertEqual(parsed.reference_date.isoformat(), "2026-04-22")
        self.assertTrue(parsed.title and "22/04/2026" in parsed.title)
        self.assertEqual(len(parsed.buy_signals), 2)
        self.assertEqual(parsed.buy_signals[0].symbol, "TIG")
        self.assertEqual(parsed.buy_signals[0].price, 6700.0)
        self.assertEqual(parsed.buy_signals[1].symbol, "HPA")

    def test_gemini_reason_must_reference_each_symbol(self) -> None:
        snap = {"payload": {"symbols": [{"symbol": "FPT", "sector": "Test", "indicators": {"rsi14": 34.0}}]}}
        sector = {"sectors": []}
        base = {
            "title": "T",
            "reference_date": "2026-01-01",
            "selected_signals": [{"rank": 1, "symbol": "FPT", "why_selected": ["RSI 34"]}],
            "sector_flow_analysis": [],
            "near_miss_signals": [],
            "analysis_notes": "n",
        }
        vague = {**base, "reason": "Áp dụng tám điều kiện bắt buộc và loại trừ tin tức theo chiến lược balanced. " * 12}
        with self.assertRaisesRegex(ValueError, "reason"):
            _parse_gemini_json_output(vague, {"FPT"}, snap, sector)

        ok = {
            **base,
            "reason": (
                "Kết quả: chọn FPT vì RSI14=34 đạt 30-45, MACD histogram dương trong snapshot, "
                "volume_ratio và ADX thỏa; sector-flow ngành của FPT dương so với TB5. Nhắc lại mã FPT là cổ lõi output. "
                "Thêm chi tiết để đủ độ dài tối thiểu: FPT xếp rank 1, không vi phạm loại trừ tin 7 ngày. "
                "Đối chiếu screened_candidates: FPT được giữ. Padding — " + ("x" * 120)
            ),
        }
        parsed = _parse_gemini_json_output(ok, {"FPT"}, snap, sector)
        self.assertEqual(len(parsed.buy_signals), 1)
        self.assertEqual(parsed.buy_signals[0].symbol, "FPT")
        self.assertIn("FPT", parsed.raw_text)

    def test_parse_missing_date_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "Không trích xuất được reference_date"):
            parse_signal_output_text("#1. TIG - BẤT ĐỘNG SẢN\\nGiá hiện tại 6,700 VND")

    def test_parse_missing_buy_signal_raises(self) -> None:
        text = "BÁO CÁO CHIẾN LƯỢC BALANCED - NGÀY 22/04/2026\nKhông có mã hợp lệ"
        with self.assertRaisesRegex(ValueError, "Không tìm thấy buy_signals hợp lệ"):
            parse_signal_output_text(text)


if __name__ == "__main__":
    unittest.main()
