import numpy as np
import pandas as pd
import pytest

from crypto_quant.backtest import backtest
from crypto_quant.risk import allow_trade, position_size
from crypto_quant.signals import add_indicators, combine_votes
from crypto_quant.specialists import DOMAINS, specialist_slots


def sample_data(n=100):
    close = pd.Series(np.linspace(100, 130, n) + np.sin(np.arange(n) / 3))
    return pd.DataFrame({"open": close.to_numpy(), "high": (close + 1).to_numpy(), "low": (close - 1).to_numpy(),
                         "close": close.to_numpy(), "volume": np.full(n, 1000.0)},
                        index=pd.date_range("2024-01-01", periods=n, freq="h"))


def test_indicators_and_backtest_are_finite():
    frame = add_indicators(sample_data())
    assert "ema_fast" in frame and "rsi" in frame
    result = backtest(sample_data())
    assert np.isfinite(result["total_return"])
    assert result["max_drawdown"] <= 0


def test_ensemble_can_hold():
    assert combine_votes([(0.1, 1.0, "weak")]).action == "HOLD"


def test_risk_controls():
    assert position_size(10_000, 100, 95) == pytest.approx(10)
    assert allow_trade("BUY", 0.01)
    assert not allow_trade("BUY", 0.02)
    assert not allow_trade("HOLD", 0.0)


def test_registry_has_5000_slots():
    assert len(DOMAINS) == 50
    assert len(specialist_slots()) == 5000
    assert all(s["status"] == "placeholder" for s in specialist_slots()[:2])
