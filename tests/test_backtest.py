from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_quant.backtest import run_backtest
from crypto_quant.market_data import validate_ohlcv
from crypto_quant.risk import allow_trade, position_size
from crypto_quant.specialists import DOMAINS, specialist_slots


def candles(count: int = 100) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=count, freq="h", tz="UTC")
    close = np.linspace(100.0, 150.0, count)
    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(count, 100.0),
        },
        index=index,
    )


def test_validate_ohlcv_rejects_bad_high() -> None:
    frame = candles(3)
    frame.iloc[0, frame.columns.get_loc("high")] = 1.0
    with pytest.raises(ValueError, match="High must"):
        validate_ohlcv(frame)


def test_backtest_reports_metrics_and_costs() -> None:
    result = run_backtest(candles(), fee_bps=10, slippage_bps=5)
    assert result["candles"] == 100
    assert -1.0 <= result["total_return"]
    assert result["max_drawdown"] <= 0.0
    assert result["total_cost"] >= 0.0
    assert len(result["equity_curve"]) > 0


def test_backtest_rejects_short_history() -> None:
    with pytest.raises(ValueError, match="31 candles"):
        run_backtest(candles(30))


def test_risk_helpers_fail_closed() -> None:
    assert position_size(10_000, 100, 95) == pytest.approx(10.0)
    assert allow_trade("BUY", 0.01)
    assert not allow_trade("BUY", 0.02)
    assert not allow_trade("NO_TRADE", 0.0)


def test_specialist_registry_has_5000_slots() -> None:
    slots = specialist_slots()
    assert len(DOMAINS) == 50
    assert len(slots) == 5000
    assert all(slot["status"] == "placeholder" for slot in slots)
