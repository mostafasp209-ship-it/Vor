"""Simple, transparent baseline signal engine; not a profitability claim."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .market_data import validate_ohlcv

@dataclass(frozen=True)
class Signal:
    action: str
    score: float
    confidence: float
    reasons: tuple[str, ...]

def generate_signal(ohlcv: pd.DataFrame, threshold: float = 0.35) -> Signal:
    """Generate a basic EMA/RSI ensemble signal from validated OHLCV candles."""
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    data = validate_ohlcv(ohlcv)
    if len(data) < 30:
        return Signal("NO_TRADE", 0.0, 0.0, ("insufficient_history",))
    close = data["close"]
    fast = close.ewm(span=12, adjust=False).mean()
    slow = close.ewm(span=26, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] > 0 else 100.0
    rsi = 100 - 100 / (1 + rs)
    trend_vote = 1.0 if fast.iloc[-1] > slow.iloc[-1] else -1.0
    momentum_vote = max(-1.0, min(1.0, (float(rsi) - 50.0) / 25.0))
    score = 0.7 * trend_vote + 0.3 * momentum_vote
    action = "BUY" if score >= threshold else "SELL" if score <= -threshold else "NO_TRADE"
    return Signal(action, float(score), min(1.0, abs(float(score))),
                  ("ema_12_vs_26", f"rsi_14={float(rsi):.2f}", "research_baseline_only"))
