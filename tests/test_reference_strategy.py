from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_quant.reference_strategy import backtest_reference, evaluate_gates


def _frame(n=180, side="BUY"):
    close = np.full(n, 100.0)
    op = np.full(n, 99.8)
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    vol = np.full(n, 100.0)
    # mild wander so indicators are finite
    close = close + np.sin(np.arange(n) / 8.0)
    op = close - 0.2
    high = close + 1.0
    low = close - 1.0
    if side == "BUY":
        # force oversold recovery + bullish body on last bar
        close[-2] = 98.0
        close[-1] = 99.5
        op[-1] = 98.5
        low[-5:] = 97.0
        vol[-1] = 250.0
    else:
        close[-2] = 102.0
        close[-1] = 100.5
        op[-1] = 101.5
        high[-5:] = 103.0
        vol[-1] = 250.0
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    return pd.DataFrame({"open": op, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def test_evaluate_gates_returns_structure():
    gates = evaluate_gates(_frame())
    assert hasattr(gates, "signal_long")
    assert hasattr(gates, "signal_short")


def test_backtest_runs_without_error():
    result = backtest_reference(_frame(220))
    assert "trades" in result
    assert "win_rate" in result
    assert "expectancy_r" in result
    assert 0 <= result["win_rate"] <= 1


def test_backtest_rejects_short_history():
    with pytest.raises(ValueError):
        backtest_reference(_frame(50))


def test_backtest_rejects_missing_columns():
    df = _frame()[["open", "high", "close"]]
    with pytest.raises(ValueError):
        backtest_reference(df)
