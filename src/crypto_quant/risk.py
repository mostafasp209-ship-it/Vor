"""Conservative risk helpers; not financial advice."""
from __future__ import annotations


def position_size(equity: float, entry: float, stop: float, risk_fraction: float = 0.005) -> float:
    """Units sized so the entry-to-stop loss is at most risk_fraction of equity."""
    if equity <= 0 or entry <= 0 or stop <= 0:
        raise ValueError("equity, entry and stop must be positive")
    if not 0 < risk_fraction <= 0.02:
        raise ValueError("risk_fraction must be in (0, 0.02]; default is 0.5%")
    distance = abs(entry - stop)
    if distance == 0:
        raise ValueError("entry and stop must differ")
    return equity * risk_fraction / distance


def allow_trade(signal_action: str, daily_loss_fraction: float, max_daily_loss: float = 0.02) -> bool:
    """Fail closed on HOLD/unknown signals or when daily loss limit is reached."""
    if signal_action not in {"BUY", "SELL"}:
        return False
    if daily_loss_fraction >= max_daily_loss:
        return False
    return True
