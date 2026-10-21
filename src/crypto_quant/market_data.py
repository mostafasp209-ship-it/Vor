"""Public OHLCV data loading and validation; no API keys required."""
from __future__ import annotations
import pandas as pd

REQUIRED = ("open", "high", "low", "close", "volume")

def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize chronological OHLCV candles, raising on bad input."""
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("OHLCV dataset is empty")
    out = frame.copy().sort_index()
    for col in REQUIRED:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[list(REQUIRED)].isna().any().any():
        raise ValueError("OHLCV contains missing or non-numeric values")
    if (out[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Prices must be positive")
    if (out["volume"] < 0).any():
        raise ValueError("Volume cannot be negative")
    if (out["high"] < out[["open", "low", "close"]].max(axis=1)).any():
        raise ValueError("High must be >= open, low and close")
    if (out["low"] > out[["open", "high", "close"]].min(axis=1)).any():
        raise ValueError("Low must be <= open, high and close")
    if out.index.has_duplicates:
        raise ValueError("Duplicate candle timestamps detected")
    return out

def fetch_public_ohlcv(exchange_id: str = "binance", symbol: str = "BTC/USDT",
                       timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch public exchange candles with optional CCXT dependency."""
    if not 50 <= limit <= 1000:
        raise ValueError("limit must be between 50 and 1000")
    try:
        import ccxt
    except ImportError as exc:
        raise RuntimeError("Install optional dependency with: pip install ccxt") from exc
    exchange_type = getattr(ccxt, exchange_id, None)
    if exchange_type is None:
        raise ValueError(f"Unknown exchange: {exchange_id}")
    exchange = exchange_type({"enableRateLimit": True})
    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not rows:
        raise RuntimeError("Exchange returned no candles")
    frame = pd.DataFrame(rows, columns=["timestamp", *REQUIRED])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    frame = frame.set_index("timestamp")
    return validate_ohlcv(frame)
