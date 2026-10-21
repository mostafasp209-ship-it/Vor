"""Train and evaluate a population of unique lightweight ML trading agents.

Each agent has a distinct feature subset, prediction horizon, regularization and decision
threshold. This is a research baseline, not a claim that these are independent LLMs.
"""
from __future__ import annotations
from itertools import product
from typing import Any
import math
import numpy as np
import pandas as pd
from .market_data import validate_ohlcv

FEATURES = ("ret_1", "ret_3", "ret_6", "ret_12", "ema_gap_8", "ema_gap_21",
            "rsi_scaled", "vol_12", "range_scaled", "volume_change")
HORIZONS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 36)
REGULARIZATIONS = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)
THRESHOLDS = (0.0, 0.05, 0.1, 0.15, 0.2)
FEATURE_GROUPS = (
    ("ret_1", "ret_3", "ret_6"),
    ("ret_3", "ret_6", "ret_12"),
    ("ema_gap_8", "ema_gap_21", "ret_3"),
    ("rsi_scaled", "ret_1", "ret_6"),
    ("vol_12", "range_scaled", "ret_3"),
    ("volume_change", "ret_1", "ret_3"),
    ("ret_1", "ret_3", "ret_6", "ret_12", "ema_gap_8"),
    ("ret_1", "ret_3", "ema_gap_8", "ema_gap_21", "rsi_scaled"),
    ("ret_3", "ret_6", "ret_12", "vol_12", "range_scaled"),
    FEATURES,
)

def build_ai_population(size: int = 5000) -> list[dict[str, Any]]:
    """Return up to 5,000 unique trainable model configurations."""
    if not 1 <= size <= 5000:
        raise ValueError("size must be between 1 and 5000")
    grid = list(product(range(len(FEATURE_GROUPS)), HORIZONS, REGULARIZATIONS, THRESHOLDS))
    agents = []
    for i, (group, horizon, reg, threshold) in enumerate(grid[:size], start=1):
        agents.append({"id": f"ai-agent-{i:05d}", "feature_group": group,
            "features": FEATURE_GROUPS[group], "horizon": horizon, "regularization": reg,
            "threshold": threshold, "model_type": "ridge_return_predictor",
            "status": "trainable_ml_agent"})
    return agents

def make_features(data: pd.DataFrame) -> pd.DataFrame:
    close = data["close"].astype(float)
    returns = close.pct_change()
    ema8 = close.ewm(span=8, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    features = pd.DataFrame(index=data.index)
    for n in (1, 3, 6, 12):
        features[f"ret_{n}"] = close.pct_change(n)
    features["ema_gap_8"] = close / ema8 - 1
    features["ema_gap_21"] = close / ema21 - 1
    features["rsi_scaled"] = (rsi - 50) / 50
    features["vol_12"] = returns.rolling(12).std()
    features["range_scaled"] = (data["high"] - data["low"]) / close
    features["volume_change"] = data["volume"].pct_change().replace([np.inf, -np.inf], np.nan)
    return features.replace([np.inf, -np.inf], np.nan)

def _fit_ridge(x: np.ndarray, y: np.ndarray, regularization: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    means = x.mean(axis=0)
    scales = x.std(axis=0)
    scales[scales < 1e-10] = 1.0
    z = (x - means) / scales
    target_mean = float(y.mean())
    centered_y = y - target_mean
    gram = z.T @ z
    weights = np.linalg.solve(gram + regularization * np.eye(gram.shape[0]), z.T @ centered_y)
    return means, scales, np.append(weights, target_mean)

def evaluate_ai_population(ohlcv: pd.DataFrame, *, size: int = 5000,
                           train_fraction: float = 0.7, fee_bps: float = 10.0,
                           slippage_bps: float = 5.0, report_top: int = 20) -> dict[str, Any]:
    """Fit each unique model on the training segment and score untouched holdout data."""
    if not 0.5 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be in [0.5, 1)")
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("cost assumptions must be non-negative")
    if report_top < 1:
        raise ValueError("report_top must be >= 1")
    data = validate_ohlcv(ohlcv)
    if len(data) < 150:
        raise ValueError("At least 150 candles are required for AI population evaluation")
    features = make_features(data)
    split = int(len(data) * train_fraction)
    costs = (fee_bps + slippage_bps) / 10000.0
    close = data["close"].to_numpy(dtype=float)
    candidates = []
    for agent in build_ai_population(size):
        horizon = agent["horizon"]
        target = pd.Series(close, index=data.index).shift(-horizon) / pd.Series(close, index=data.index) - 1
        cols = list(agent["features"])
        train_mask = (features.iloc[:split][cols].notna().all(axis=1) &
                      target.iloc[:split].notna())
        x = features.iloc[:split].loc[train_mask, cols].to_numpy(dtype=float)
        y = target.iloc[:split].loc[train_mask].to_numpy(dtype=float)
        if len(y) < 30:
            continue
        means, scales, params = _fit_ridge(x, y, agent["regularization"])
        weights, intercept = params[:-1], params[-1]
        usable = features[cols].notna().all(axis=1).to_numpy()
        x_all = features[cols].fillna(0.0).to_numpy(dtype=float)
        pred = ((x_all - means) / scales) @ weights + intercept
        # Position uses only the model's prediction; apply it one candle later.
        position = np.where(pred > agent["threshold"] / 100.0, 1.0,
                   np.where(pred < -agent["threshold"] / 100.0, -1.0, 0.0))
        position[~usable] = 0.0
        position = pd.Series(position, index=data.index).shift(1).fillna(0.0).to_numpy()
        bar_returns = pd.Series(close, index=data.index).pct_change().fillna(0.0).to_numpy()
        turnover = np.abs(np.diff(np.r_[0.0, position]))
        net = position * bar_returns - turnover * costs
        train_net, test_net = net[:split], net[split:]
        def metrics(values: np.ndarray) -> dict[str, float]:
            if not len(values):
                return {"return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
            equity = np.cumprod(1 + values)
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            return {"return": float(equity[-1] - 1),
                    "sharpe": float(np.mean(values) / std * math.sqrt(8760)) if std > 0 else 0.0,
                    "max_drawdown": float(np.min(equity / np.maximum.accumulate(equity) - 1))}
        train_m, test_m = metrics(train_net), metrics(test_net)
        candidates.append({"id": agent["id"], "model_type": agent["model_type"],
            "feature_group": agent["feature_group"], "features": cols, "horizon": horizon,
            "regularization": agent["regularization"], "threshold": agent["threshold"],
            "train_return": train_m["return"], "train_sharpe": train_m["sharpe"],
            "train_max_drawdown": train_m["max_drawdown"],
            "holdout_return": test_m["return"], "holdout_sharpe": test_m["sharpe"],
            "holdout_max_drawdown": test_m["max_drawdown"], "trained_samples": int(len(y))})
    candidates.sort(key=lambda a: (a["train_sharpe"], a["train_return"]), reverse=True)
    selected = candidates[:min(report_top, len(candidates))]
    return {"candles": len(data), "train_candles": split, "holdout_candles": len(data)-split,
        "population_size": size, "trained_agents": len(candidates),
        "unique_model_configurations": len({(a["feature_group"], a["horizon"], a["regularization"], a["threshold"]) for a in build_ai_population(size)}),
        "selected_by": "training Sharpe then training return",
        "cost_assumptions_bps": {"fee": fee_bps, "slippage": slippage_bps},
        "top_agents": selected,
        "warning": "Agents are independently fitted ridge-regression ML configurations, not independent LLMs. Historical holdout performance does not guarantee future returns."}
