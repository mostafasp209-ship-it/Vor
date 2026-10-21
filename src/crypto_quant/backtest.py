"""Minimal long-only close-to-close backtest; educational baseline, not production execution."""
from __future__ import annotations

import pandas as pd

from .signals import add_indicators


def backtest(ohlcv: pd.DataFrame, fee_rate: float = 0.001, slippage_rate: float = 0.0005) -> dict[str, float | int]:
    """Test EMA trend exposure shifted one bar to avoid same-bar lookahead.

    Returns compounded return, max drawdown, number of position changes and final equity.
    Costs are charged on exposure changes. Shorting and funding are not modeled.
    """
    if fee_rate < 0 or slippage_rate < 0:
        raise ValueError("cost assumptions cannot be negative")
    frame = add_indicators(ohlcv)
    desired = (frame.ema_fast > frame.ema_slow).astype(float)
    exposure = desired.shift(1).fillna(0.0)
    returns = frame.close.pct_change().fillna(0.0)
    changes = exposure.diff().abs().fillna(exposure.abs())
    net = exposure * returns - changes * (fee_rate + slippage_rate)
    equity = (1.0 + net).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return {
        "total_return": float(equity.iloc[-1] - 1.0),
        "max_drawdown": float(drawdown.min()),
        "position_changes": int((changes > 0).sum()),
        "final_equity_multiple": float(equity.iloc[-1]),
    }
