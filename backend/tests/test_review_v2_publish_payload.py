"""Ensure review-v2 publish payload is compatible with newsfeed BuySignalIn parser."""

import unittest

from routers.review_v2 import _to_newsfeed_buy_signal
from routers.signal_entries import _parse_buy_signals
from schemas.review_v2 import ReviewV2BuySignal


class ReviewV2PublishPayloadTests(unittest.TestCase):
    def test_newsfeed_parses_review_v2_buy_signal(self) -> None:
        sig = ReviewV2BuySignal(
            rank=1,
            symbol="GEX",
            sector="Thiết bị điện, điện tử",
            recommendation="THEO DÕI MUA",
            price=31150.0,
            why_selected=["Dòng tiền ngành dương so với TB5 (10.00%)."],
            sector_flow_pct=1015.65,
        )
        payload = {"buy_signals": [_to_newsfeed_buy_signal(sig)]}
        parsed = _parse_buy_signals(payload)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].symbol, "GEX")
        self.assertNotIn("sector_flow_pct", payload["buy_signals"][0])


if __name__ == "__main__":
    unittest.main()
