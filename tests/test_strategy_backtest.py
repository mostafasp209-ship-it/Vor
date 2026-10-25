from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_quant.strategy_backtest import (
    backtest_breakout_volume,
    backtest_multiconfluence_rtm,
    fetch_binance_klines,
    parameter_sweep,
)


def _candles(n=500):
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    close = 30000 + np.arange(n) * 8.0 + 200 * np.sin(np.arange(n) / 5.0)
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) + 120
    low = np.minimum(open_, close) - 120
    volume = np.full(n, 100.0)
    # periodic volume spikes to exercise volume filters
    volume[::17] = 500.0
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": volume}, index=idx)


def test_breakout_backtest_returns_metrics_and_trade_records():
    result = backtest_breakout_volume(_candles(), trend_filter=False, vol_mult=1.2, min_trades=0)
    assert result["trades"] >= 0
    assert 0 <= result["win_rate"] <= 1
    assert "trades_frame" in result
    assert "total_r" in result


def test_rtm_short_backtest_returns_metrics():
    result = backtest_multiconfluence_rtm(_candles(), vol_mult=1.2)
    assert result["trades"] >= 0
    assert 0 <= result["win_rate"] <= 1
    assert "trades_frame" in result


def test_sweep_has_expected_columns_even_when_no_candidates_pass():
    result = parameter_sweep(_candles(), min_trades=10_000)
    assert result.empty
    assert "total_r" in result.columns


@pytest.mark.parametrize("kwargs", [
    {"lookback": 1}, {"vol_mult": 0},
])
def test_breakout_rejects_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        backtest_breakout_volume(_candles(), **kwargs)


def test_fetch_rejects_invalid_interval_without_network():
    with pytest.raises(ValueError, match="Unsupported interval"):
        fetch_binance_klines(interval="4hour")
