"""Transparent baseline indicators and ensemble signal scoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Signal:
    action: str  # BUY, SELL, or HOLD
    score: float
    confidence: float
    reasons: tuple[str, ...]


def add_indicators(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Return OHLCV plus EMA, RSI and rolling-volume indicators.

    Required columns: open, high, low, close, volume. Input must be chronological.
    """
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(ohlcv.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if ohlcv.empty:
        raise ValueError("OHLCV data is empty")
    out = ohlcv.copy().sort_index()
    close = pd.to_numeric(out["close"], errors="coerce")
    if close.isna().any() or (close <= 0).any():
        raise ValueError("Close prices must be numeric, non-null and positive")
    out["ema_fast"] = close.ewm(span=12, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=26, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = 100 - (100 / (1 + rs))
    out["volume_ratio"] = out["volume"] / out["volume"].rolling(20).mean()
    return out


def baseline_votes(frame: pd.DataFrame) -> list[tuple[float, float, str]]:
    """Return (vote, weight, explanation) from simple, non-predictive heuristics."""
    if len(frame) < 30:
        return [(0.0, 1.0, "insufficient_history")]
    row = frame.iloc[-1]
    votes: list[tuple[float, float, str]] = []
    trend = 1.0 if row.ema_fast > row.ema_slow else -1.0
    votes.append((trend, 1.0, "ema_trend"))
    if pd.notna(row.rsi):
        # RSI is used as a bounded momentum vote, not a standalone trade trigger.
        momentum = float(np.clip((float(row.rsi) - 50.0) / 25.0, -1.0, 1.0))
        votes.append((momentum, 0.6, "rsi_momentum"))
    if pd.notna(row.volume_ratio) and row.volume_ratio >= 1.5:
        votes.append((trend, 0.4, "elevated_volume_confirms_trend"))
    return votes


def combine_votes(votes: Iterable[tuple[float, float, str]], threshold: float = 0.35) -> Signal:
    """Combine weighted votes. HOLD is intentional when evidence is weak or conflicting."""
    votes = list(votes)
    if not votes:
        return Signal("HOLD", 0.0, 0.0, ("no_votes",))
    denom = sum(max(0.0, weight) for _, weight, _ in votes)
    if denom <= 0:
        return Signal("HOLD", 0.0, 0.0, ("invalid_weights",))
    score = float(sum(float(v) * max(0.0, float(w)) for v, w, _ in votes) / denom)
    confidence = min(1.0, abs(score))
    action = "BUY" if score >= threshold else "SELL" if score <= -threshold else "HOLD"
    return Signal(action, score, confidence, tuple(reason for _, _, reason in votes))


def generate_signal(ohlcv: pd.DataFrame) -> Signal:
    enriched = add_indicators(ohlcv)
    return combine_votes(baseline_votes(enriched))
