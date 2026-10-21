"""Optional OHLCV retrieval using CCXT; public market data only."""
from __future__ import annotations

import pandas as pd


def fetch_ohlcv(exchange_id: str, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch public candles. Install the optional dependency with pip install -e '.[data]'."""
    if limit < 50 or limit > 1000:
        raise ValueError("limit must be between 50 and 1000")
    try:
        import ccxt  # type: ignore
    except ImportError as exc:
        raise RuntimeError("CCXT is optional; install with pip install -e '.[data]'") from exc
    if not hasattr(ccxt, exchange_id):
        raise ValueError(f"Unknown CCXT exchange: {exchange_id}")
    exchange_cls = getattr(ccxt, exchange_id)
    exchange = exchange_cls({"enableRateLimit": True})
    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not rows:
        raise RuntimeError("Exchange returned no candles")
    frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    return frame.set_index("timestamp").sort_index()
