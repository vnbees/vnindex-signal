from decimal import Decimal
from typing import Optional

CORPORATE_ACTION_THRESHOLD = Decimal("30.0")

def derive_signal_type(recommendation: str) -> str:
    """Derive signal_type from recommendation."""
    if recommendation in ("BUY_STRONG", "BUY"):
        return "BUY"
    elif recommendation in ("AVOID", "SELL"):
        return "SELL"
    return "HOLD"

def calculate_pnl_pct(price_close: Optional[Decimal], price_open_t1: Optional[Decimal]) -> Optional[Decimal]:
    """Calculate PnL percentage from price_open_t1."""
    if price_close is None or price_open_t1 is None or price_open_t1 == 0:
        return None
    return ((price_close / price_open_t1) - 1) * 100

def is_corporate_action(pnl_pct: Optional[Decimal]) -> bool:
    """Flag if absolute PnL > 30%."""
    if pnl_pct is None:
        return False
    return abs(pnl_pct) > CORPORATE_ACTION_THRESHOLD
