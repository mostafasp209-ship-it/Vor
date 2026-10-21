import numpy as np
import pandas as pd
import pytest

from crypto_quant.population import build_population, evaluate_population


def frame(n=160):
    close = 100 * np.exp(np.cumsum(0.0005 + 0.01 * np.sin(np.arange(n) / 5)))
    return pd.DataFrame({
        "open": close * 0.999,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.full(n, 100.0),
    }, index=pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC"))


def test_population_contains_5000_deterministic_candidates():
    candidates = build_population()
    assert len(candidates) == 5000
    assert len({candidate["id"] for candidate in candidates}) == 5000
    assert {candidate["family"] for candidate in candidates} == {
        "ema_trend", "rsi_reversion", "breakout", "momentum", "volatility_filtered"
    }


def test_population_evaluation_separates_train_and_holdout():
    result = evaluate_population(frame(), size=25, report_top=5)
    assert result["evaluated_candidates"] == 25
    assert result["train_candles"] == 112
    assert result["holdout_candles"] == 48
    assert len(result["top_candidates"]) == 5
    assert "holdout_return" in result["top_candidates"][0]


def test_population_rejects_short_data():
    with pytest.raises(ValueError, match="100 candles"):
        evaluate_population(frame(80), size=10)
