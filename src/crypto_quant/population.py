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


def build_population(size: int = 5000) -> list[dict[str, Any]]:
    """Create a deterministic, diverse population of parameterized strategy candidates."""
    if size < 1:
        raise ValueError("size must be >= 1")
    grid = list(product(
        FAMILIES,
        (5, 8, 12, 16, 20, 26, 32, 40, 50, 64),
        (14, 20, 26, 35, 45, 55, 65, 80, 100, 120),
    ))
    population = []
    for index in range(size):
        family, fast, slow = grid[index % len(grid)]
        # Use family-specific, deterministic variations without random hidden state.
        population.append({
            "id": f"candidate-{index + 1:05d}",
            "family": family,
            "fast_window": fast,
            "slow_window": max(fast + 2, slow),
            "threshold": (0.25, 0.35, 0.45, 0.55)[index % 4],
            "status": "executable_ohlcv_candidate",
        })
    return population


def _position(close: pd.Series, cfg: dict[str, Any]) -> pd.Series:
    family = cfg["family"]
    fast = int(cfg["fast_window"])
    slow = int(cfg["slow_window"])
    if family in {"ema_trend", "momentum", "volatility_filtered"}:
        fast_ema = close.ewm(span=fast, adjust=False).mean()
        slow_ema = close.ewm(span=slow, adjust=False).mean()
        pos = pd.Series(np.where(fast_ema > slow_ema, 1.0,
                                 np.where(fast_ema < slow_ema, -1.0, 0.0)), index=close.index)
        if family == "momentum":
            momentum = close.pct_change(fast)
            pos = pos.where(momentum.abs() > float(cfg["threshold"]) / 100.0, 0.0)
        elif family == "volatility_filtered":
            returns = close.pct_change()
            vol = returns.rolling(fast).std()
            cap = vol.rolling(max(slow, 20)).quantile(0.9)
            pos = pos.where(vol <= cap, 0.0)
        return pos
    if family == "rsi_reversion":
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / fast, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / fast, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return pd.Series(np.where(rsi < 30, 1.0, np.where(rsi > 70, -1.0, 0.0)), index=close.index)
    # Breakout: trade the direction of a close crossing the prior rolling range.
    upper = close.shift(1).rolling(slow).max()
    lower = close.shift(1).rolling(slow).min()
    return pd.Series(np.where(close > upper, 1.0, np.where(close < lower, -1.0, 0.0)), index=close.index)


def _metrics(position: pd.Series, returns: pd.Series, cost_rate: float) -> dict[str, float]:
    shifted = position.shift(1).fillna(0.0)
    turnover = shifted.sub(shifted.shift(1).fillna(0.0)).abs()
    net = shifted * returns - turnover * cost_rate
    net = net.replace([np.inf, -np.inf], np.nan).dropna()
    if net.empty:
        return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "trades": 0.0}
    equity = (1.0 + net).cumprod()
    std = float(net.std(ddof=1)) if len(net) > 1 else 0.0
    sharpe = float(net.mean() / std * math.sqrt(8760)) if std > 0 else 0.0
    drawdown = float((equity / equity.cummax() - 1.0).min())
    return {
        "total_return": float(equity.iloc[-1] - 1.0),
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "trades": float((turnover.reindex(net.index).fillna(0.0) > 0).sum()),
    }


def evaluate_population(
    ohlcv: pd.DataFrame,
    *,
    size: int = 5000,
    fee_bps: float = 10.0,
    slippage_bps: float = 5.0,
    train_fraction: float = 0.7,
    report_top: int = 20,
) -> dict[str, Any]:
    """Evaluate 5,000 candidate configurations with chronological train/holdout split.

    Candidates are ranked using training Sharpe only. Holdout metrics are reported for
    the training-selected top candidates and must not be used repeatedly to tune selection.
    """
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
    cost_rate = (fee_bps + slippage_bps) / 10_000.0
    population = build_population(size)
    ranked = []
    positions: dict[str, pd.Series] = {}
    for cfg in population:
        pos = _position(close, cfg)
        train_metrics = _metrics(pos.iloc[:split], returns.iloc[:split], cost_rate)
        ranked.append({
            "id": cfg["id"], "family": cfg["family"], "fast_window": cfg["fast_window"],
            "slow_window": cfg["slow_window"], "threshold": cfg["threshold"],
            "train_sharpe": train_metrics["sharpe"],
            "train_return": train_metrics["total_return"],
            "train_max_drawdown": train_metrics["max_drawdown"],
        })
        positions[cfg["id"]] = pos
    ranked.sort(key=lambda item: (item["train_sharpe"], item["train_return"]), reverse=True)
    selected = ranked[:min(report_top, len(ranked))]
    for item in selected:
        pos = positions[item["id"]].iloc[split:]
        holdout = _metrics(pos, returns.iloc[split:], cost_rate)
        item.update({
            "holdout_return": holdout["total_return"],
            "holdout_sharpe": holdout["sharpe"],
            "holdout_max_drawdown": holdout["max_drawdown"],
            "holdout_trades": int(holdout["trades"]),
        })
    return {
        "candles": len(data),
        "train_candles": split,
        "holdout_candles": len(data) - split,
        "population_size": len(population),
        "evaluated_candidates": len(ranked),
        "selected_by": "training Sharpe then training return",
        "cost_assumptions_bps": {"fee": fee_bps, "slippage": slippage_bps},
        "top_candidates": selected,
        "warning": "OHLCV-only research candidates, not 5,000 independent AI experts. Holdout results are historical and do not guarantee future performance.",
    }
