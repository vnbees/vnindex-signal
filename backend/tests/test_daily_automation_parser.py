import unittest

from services.daily_automation_service import parse_signal_output_text


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

    def test_parse_missing_date_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "Không trích xuất được reference_date"):
            parse_signal_output_text("#1. TIG - BẤT ĐỘNG SẢN\\nGiá hiện tại 6,700 VND")

    def test_parse_missing_buy_signal_raises(self) -> None:
        text = "TÍN HIỆU MUA BALANCED - NGÀY 22/04/2026\\nKhông có mã hợp lệ"
        with self.assertRaisesRegex(ValueError, "Không tìm thấy buy_signals hợp lệ"):
            parse_signal_output_text(text)


if __name__ == "__main__":
    unittest.main()
