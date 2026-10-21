"""Generate and evaluate a fixed population of 5,000 OHLCV-only strategy candidates.

These are parameterized rule candidates, not independent human analysts or trained AI
models. Only OHLCV-supported families are enabled; on-chain, news, order-book and funding
specialists require their own data feeds and are intentionally not fabricated here.
"""
from __future__ import annotations
from itertools import product
import math
from typing import Any
import numpy as np
import pandas as pd
from .market_data import validate_ohlcv

FAMILIES = ("ema_trend", "rsi_reversion", "breakout", "momentum", "volatility_filtered")
FAST_WINDOWS = (5, 8, 12, 16, 20, 26, 32, 40, 50, 64)
SLOW_WINDOWS = (70, 80, 90, 100, 110, 120, 130, 140, 150, 160)
THRESHOLDS = tuple(round(value / 10, 1) for value in range(1, 11))

def build_population(size: int = 5000) -> list[dict[str, Any]]:
    """Create deterministic unique parameter configurations; supports up to 5,000."""
    if not 1 <= size <= 5000:
        raise ValueError("size must be between 1 and 5000")
    grid = list(product(FAMILIES, FAST_WINDOWS, SLOW_WINDOWS, THRESHOLDS))
    return [
        {"id": f"candidate-{i:05d}", "family": family, "fast_window": fast,
         "slow_window": slow, "threshold": threshold, "status": "executable_ohlcv_candidate"}
        for i, (family, fast, slow, threshold) in enumerate(grid[:size], start=1)
    ]

def _position(close: pd.Series, cfg: dict[str, Any]) -> pd.Series:
    family, fast, slow = cfg["family"], int(cfg["fast_window"]), int(cfg["slow_window"])
    threshold = float(cfg["threshold"])
    if family in {"ema_trend", "momentum", "volatility_filtered"}:
        fast_ema = close.ewm(span=fast, adjust=False).mean()
        slow_ema = close.ewm(span=slow, adjust=False).mean()
        pos = pd.Series(np.where(fast_ema > slow_ema, 1.0,
                                 np.where(fast_ema < slow_ema, -1.0, 0.0)), index=close.index)
        if family == "momentum":
            pos = pos.where(close.pct_change(fast).abs() > threshold / 100.0, 0.0)
        elif family == "volatility_filtered":
            vol = close.pct_change().rolling(fast).std()
            cap = vol.rolling(max(slow, 20)).quantile(0.9)
            pos = pos.where(vol <= cap, 0.0)
        return pos
    if family == "rsi_reversion":
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / fast, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / fast, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100.0 - 100.0 / (1.0 + rs)
        oversold = 20.0 + threshold * 20.0
        overbought = 100.0 - oversold
        return pd.Series(np.where(rsi < oversold, 1.0,
                                  np.where(rsi > overbought, -1.0, 0.0)), index=close.index)
    upper, lower = close.shift(1).rolling(slow).max(), close.shift(1).rolling(slow).min()
    return pd.Series(np.where(close > upper, 1.0, np.where(close < lower, -1.0, 0.0)),
                     index=close.index)

def _metrics(position: pd.Series, returns: pd.Series, cost_rate: float) -> dict[str, float]:
    shifted = position.shift(1).fillna(0.0)
    turnover = shifted.sub(shifted.shift(1).fillna(0.0)).abs()
    net = (shifted * returns - turnover * cost_rate).replace([np.inf, -np.inf], np.nan).dropna()
    if net.empty:
        return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "trades": 0.0}
    equity = (1.0 + net).cumprod()
    std = float(net.std(ddof=1)) if len(net) > 1 else 0.0
    sharpe = float(net.mean() / std * math.sqrt(8760)) if std > 0 else 0.0
    return {"total_return": float(equity.iloc[-1] - 1.0), "sharpe": sharpe,
            "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
            "trades": float((turnover.reindex(net.index).fillna(0.0) > 0).sum())}

def evaluate_population(ohlcv: pd.DataFrame, *, size: int = 5000, fee_bps: float = 10.0,
                       slippage_bps: float = 5.0, train_fraction: float = 0.7,
                       report_top: int = 20) -> dict[str, Any]:
    """Evaluate unique candidates chronologically; rank on training data only."""
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee_bps and slippage_bps must be non-negative")
    if not 0.5 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be in [0.5, 1)")
    if report_top < 1:
        raise ValueError("report_top must be >= 1")
    data = validate_ohlcv(ohlcv)
    if len(data) < 100:
        raise ValueError("At least 100 candles are required for population evaluation")
    close = data["close"].astype(float)
    returns = close.pct_change().fillna(0.0)
    split = int(len(data) * train_fraction)
    cost_rate = (fee_bps + slippage_bps) / 10000.0
    population = build_population(size)
    ranked, positions = [], {}
    for cfg in population:
        pos = _position(close, cfg)
        m = _metrics(pos.iloc[:split], returns.iloc[:split], cost_rate)
        ranked.append({"id": cfg["id"], "family": cfg["family"],
            "fast_window": cfg["fast_window"], "slow_window": cfg["slow_window"],
            "threshold": cfg["threshold"], "train_sharpe": m["sharpe"],
            "train_return": m["total_return"], "train_max_drawdown": m["max_drawdown"]})
        positions[cfg["id"]] = pos
    ranked.sort(key=lambda item: (item["train_sharpe"], item["train_return"]), reverse=True)
    selected = ranked[:min(report_top, len(ranked))]
    for item in selected:
        holdout = _metrics(positions[item["id"]].iloc[split:], returns.iloc[split:], cost_rate)
        item.update({"holdout_return": holdout["total_return"], "holdout_sharpe": holdout["sharpe"],
            "holdout_max_drawdown": holdout["max_drawdown"], "holdout_trades": int(holdout["trades"])})
    return {"candles": len(data), "train_candles": split, "holdout_candles": len(data) - split,
        "population_size": len(population), "unique_configurations": len({(c["family"], c["fast_window"],
        c["slow_window"], c["threshold"]) for c in population}), "evaluated_candidates": len(ranked),
        "selected_by": "training Sharpe then training return",
        "cost_assumptions_bps": {"fee": fee_bps, "slippage": slippage_bps},
        "top_candidates": selected,
        "warning": "OHLCV-only rule candidates, not independent AI experts. Historical holdout results do not guarantee future performance."}
