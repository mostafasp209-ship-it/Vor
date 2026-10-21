from __future__ import annotations

import numpy as np
import pandas as pd

from crypto_quant.ensemble import analyze_ensemble


def make_candles(close: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({
        "open": close * 0.999,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.full(len(close), 100.0),
    }, index=pd.date_range("2026-01-01", periods=len(close), freq="h", tz="UTC"))


def test_ensemble_abstains_with_insufficient_history() -> None:
    result = analyze_ensemble(make_candles(np.linspace(100, 110, 20)))
    assert result.action == "NO_TRADE"
    assert "insufficient_history" in result.reasons


def test_ensemble_returns_auditable_opinions() -> None:
    result = analyze_ensemble(make_candles(np.linspace(100, 140, 100)))
    assert len(result.opinions) == 2
    assert {opinion.name for opinion in result.opinions} == {"trend", "momentum"}
    assert -1.0 <= result.score <= 1.0
    assert result.action in {"BUY", "SELL", "NO_TRADE"}
    assert any(reason.startswith("volatility_") for reason in result.reasons)
