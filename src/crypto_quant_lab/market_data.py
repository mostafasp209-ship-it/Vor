"""Public OHLCV ingestion with validation; no trading or private credentials required."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if self.timestamp_ms < 0:
            raise ValueError("timestamp_ms must be non-negative")
        if any(not _is_finite(value) for value in values):
            raise ValueError("OHLCV values must be finite numbers")
        if min(self.open, self.high, self.low, self.close, self.volume) < 0:
            raise ValueError("OHLCV values must be non-negative")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be at least open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be at most open, close, and high")


def _is_finite(value: float) -> bool:
    # Avoid importing math into the public API and reject NaN/inf explicitly.
    return value == value and value not in (float("inf"), float("-inf"))


def validate_candles(candles: list[Candle]) -> list[Candle]:
    """Return candles in chronological order; reject duplicate timestamps."""
    ordered = sorted(candles, key=lambda candle: candle.timestamp_ms)
    timestamps = [candle.timestamp_ms for candle in ordered]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("duplicate candle timestamps detected")
    return ordered


class CcxtMarketDataClient:
    """Small adapter for public exchange OHLCV endpoints using the optional ccxt package."""

    def __init__(self, exchange_id: str = "binance") -> None:
        try:
            import ccxt  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("Install the market-data extra: pip install -e '.[market-data]'") from exc
        exchange_class: Any = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unsupported ccxt exchange id: {exchange_id}")
        self._exchange = exchange_class({"enableRateLimit": True})

    def fetch_ohlcv(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        limit: int = 200,
        since: int | None = None,
    ) -> list[Candle]:
        if not symbol.strip():
            raise ValueError("symbol must not be empty")
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        rows = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        candles = [Candle(int(row[0]), float(row[1]), float(row[2]), float(row[3]),
                          float(row[4]), float(row[5])) for row in rows]
        return validate_candles(candles)

    def close(self) -> None:
        close = getattr(self._exchange, "close", None)
        if callable(close):
            close()
