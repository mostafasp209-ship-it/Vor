import numpy as np
import pandas as pd
import pytest
from crypto_quant.ai_population import build_ai_population, evaluate_ai_population

def frame(n=220):
    t = np.arange(n)
    close = 100 * np.exp(np.cumsum(0.0002 + 0.008 * np.sin(t / 7) + 0.002 * np.cos(t / 3)))
    return pd.DataFrame({"open": close * 0.999, "high": close * 1.01,
        "low": close * 0.99, "close": close, "volume": 100 + 10 * np.sin(t / 4)},
        index=pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC"))

def test_builds_5000_unique_trainable_ai_configs():
    agents = build_ai_population()
    assert len(agents) == 5000
    assert len({a["id"] for a in agents}) == 5000
    assert len({(a["feature_group"], a["horizon"], a["regularization"], a["threshold"])
                for a in agents}) == 5000
    assert all(a["model_type"] == "ridge_return_predictor" for a in agents)

def test_ai_population_trains_and_reports_holdout():
    result = evaluate_ai_population(frame(), size=20, report_top=5)
    assert result["trained_agents"] == 20
    assert result["unique_model_configurations"] == 20
    assert len(result["top_agents"]) == 5
    assert "holdout_return" in result["top_agents"][0]
    assert result["holdout_candles"] == 66

def test_rejects_too_short_data():
    with pytest.raises(ValueError, match="150 candles"):
        evaluate_ai_population(frame(100), size=5)
