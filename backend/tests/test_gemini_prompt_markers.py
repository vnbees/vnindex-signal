"""Lightweight checks for Gemini prompt construction (no API key, no network)."""

import unittest

from services.gemini_smoke_prompt import build_gemini_prompt_for_smoke


class GeminiPromptMarkersTests(unittest.TestCase):
    def test_build_prompt_contains_snapshot_and_sector_blocks(self) -> None:
        snapshot = {
            "found": True,
            "payload": {
                "as_of_date": "2026-01-02",
                "symbols": [
                    {
                        "symbol": "AAA",
                        "sector": "TestSector",
                        "indicators": {"rsi14": 40.0},
                        "posts_recent_7d": [],
                    }
                ],
            },
        }
        sector = {"as_of_date": "2026-01-02", "sessions": 5, "sectors": []}
        base = "INSTRUCTIONS_LINE_ONE"
        prompt = build_gemini_prompt_for_smoke(base, snapshot, sector)
        self.assertIn("INSTRUCTIONS_LINE_ONE", prompt)
        self.assertIn("[DỮ LIỆU SNAPSHOT JSON]", prompt)
        self.assertIn("[DỮ LIỆU SECTOR FLOW 5D JSON]", prompt)
        self.assertIn('"symbol":"AAA"', prompt.replace(" ", ""))
        self.assertIn("selected_signals", prompt)
        self.assertIn("near_miss_signals", prompt)


if __name__ == "__main__":
    unittest.main()
