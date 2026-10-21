"""Small, auditable specialist ensemble for research signals.

The implemented specialists are simple rule-based baselines, not independent people or
validated predictive models. Placeholder registry slots must not be treated as votes.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .market_data import validate_ohlcv


@dataclass(frozen=True)
class SpecialistOpinion:
    name: str
    vote: float
    confidence: float
    reason: str


@dataclass(frozen=True)
class EnsembleDecision:
    action: str
    score: float
    confidence: float
    opinions: tuple[SpecialistOpinion, ...]
    reasons: tuple[str, ...]


def _trend_specialist(close: pd.Series) -> SpecialistOpinion:
    fast = close.ewm(span=12, adjust=False).mean().iloc[-1]
    slow = close.ewm(span=26, adjust=False).mean().iloc[-1]
    vote = 1.0 if fast > slow else -1.0 if fast < slow else 0.0
    return SpecialistOpinion("trend", vote, min(1.0, abs(float(fast / slow - 1.0)) * 100),
                             "ema_12_vs_26")


def _momentum_specialist(close: pd.Series) -> SpecialistOpinion:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    last_loss = float(loss.iloc[-1])
    rsi = 100.0 if last_loss == 0 else 100.0 - 100.0 / (1.0 + float(gain.iloc[-1]) / last_loss)
    vote = max(-1.0, min(1.0, (rsi - 50.0) / 20.0))
    return SpecialistOpinion("momentum", vote, min(1.0, abs(rsi - 50.0) / 30.0),
                             f"rsi_14={rsi:.2f}")


def _volatility_gate(close: pd.Series) -> tuple[bool, str]:
    returns = close.pct_change().dropna()
    rolling = returns.rolling(20).std().dropna()
    if len(rolling) < 20:
        return True, "volatility_history_insufficient"
    current = float(rolling.iloc[-1])
    cutoff = float(rolling.iloc[-min(100, len(rolling)):].quantile(0.90))
    if current > cutoff:
        return False, "volatility_above_rolling_90th_percentile"
    return True, "volatility_within_historical_range"


def analyze_ensemble(ohlcv: pd.DataFrame, threshold: float = 0.35) -> EnsembleDecision:
    """Combine trend and momentum, abstaining during unusually high volatility."""
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be in (0, 1]")
    data = validate_ohlcv(ohlcv)
    if len(data) < 40:
        return EnsembleDecision("NO_TRADE", 0.0, 0.0, (), ("insufficient_history",))

    close = data["close"].astype(float)
    opinions = (_trend_specialist(close), _momentum_specialist(close))
    weights = {"trend": 0.65, "momentum": 0.35}
    score = sum(weights[o.name] * o.vote for o in opinions)
    allowed, volatility_reason = _volatility_gate(close)
    action = ("BUY" if score >= threshold else "SELL" if score <= -threshold else "NO_TRADE")
    reasons = tuple(o.reason for o in opinions) + (volatility_reason,)
    if not allowed:
        action = "NO_TRADE"
    confidence = min(1.0, abs(float(score))) if action != "NO_TRADE" else 0.0
    return EnsembleDecision(action, float(score), confidence, opinions, reasons)
