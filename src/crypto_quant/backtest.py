"""Fee- and slippage-aware close-to-close backtester for the baseline signal engine.

Signals use candles available at time t and are applied to the return from close[t]
to close[t+1], avoiding same-candle look-ahead. Research code only; no profitability
claim, and live execution risks are not fully modeled.
"""
from __future__ import annotations

import math
import pandas as pd

from .market_data import validate_ohlcv
from .signal_engine import generate_signal


def run_backtest(
    ohlcv: pd.DataFrame,
    *,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    threshold: float = 0.35,
    periods_per_year: int = 8760,
) -> dict:
    """Run long/short/flat simulation; costs apply to absolute position turnover."""
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee_bps and slippage_bps must be non-negative")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    data = validate_ohlcv(ohlcv)
    if len(data) < 31:
        raise ValueError("At least 31 candles are required for a one-step backtest")

    close = data["close"].astype(float)
    rows = []
    previous_position = 0.0
    cost_rate = (fee_bps + slippage_bps) / 10_000.0
    for t in range(29, len(data) - 1):
        signal = generate_signal(data.iloc[: t + 1], threshold=threshold)
        position = 1.0 if signal.action == "BUY" else -1.0 if signal.action == "SELL" else 0.0
        turnover = abs(position - previous_position)
        gross = float(close.iloc[t + 1] / close.iloc[t] - 1.0) * position
        cost = turnover * cost_rate
        rows.append({
            "timestamp": data.index[t + 1], "signal": signal.action,
            "position": position, "gross_return": gross, "turnover": turnover,
            "cost": cost, "net_return": gross - cost,
        })
        previous_position = position

    curve = pd.DataFrame(rows).set_index("timestamp")
    curve["equity"] = (1.0 + curve["net_return"]).cumprod()
    peak = curve["equity"].cummax()
    std = float(curve["net_return"].std(ddof=1))
    mean = float(curve["net_return"].mean())
    return {
        "candles": int(len(data)),
        "trades_or_rebalances": int((curve["turnover"] > 0).sum()),
        "total_return": float(curve["equity"].iloc[-1] - 1.0),
        "max_drawdown": float((curve["equity"] / peak - 1.0).min()),
        "sharpe_annualized": float(mean / std * math.sqrt(periods_per_year)) if std > 0 else 0.0,
        "win_rate": float((curve["net_return"] > 0).mean()),
        "total_cost": float(curve["cost"].sum()),
        "equity_curve": curve,
        "note": "Historical simulation only; funding, spread dynamics, market impact, and live execution risk are excluded.",
    }
