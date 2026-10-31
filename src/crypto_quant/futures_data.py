"""Public Binance USD-M futures OHLCV fetch (no API key)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

_INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def fetch_futures_klines(
    symbol: str = "BTCUSDT",
    interval: str = "4h",
    *,
    since: Optional[str] = "2022-01-01",
    timeout: int = 20,
    pause_seconds: float = 0.12,
) -> pd.DataFrame:
    """Paginate Binance USDT-M perpetual klines."""
    if interval not in _INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")

    start_ms = None
    if since:
        start_ms = int(pd.Timestamp(since, tz="UTC").timestamp() * 1000)

    rows: list[list] = []
    cursor = start_ms
    while True:
        params: dict = {"symbol": symbol.upper(), "interval": interval, "limit": 1500}
        if cursor is not None:
            params["startTime"] = cursor
        query = urlencode(params)
        req = Request(
            "https://fapi.binance.com/fapi/v1/klines?" + query,
            headers={"User-Agent": "Vor-Research/1.0"},
        )
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload:
            break
        rows.extend(payload)
        if len(payload) < 1500:
            break
        cursor = int(payload[-1][0]) + 1
        time.sleep(max(0.0, pause_seconds))

    if not rows:
        raise RuntimeError(f"No futures candles for {symbol}")

    frame = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    frame = frame.drop_duplicates(subset="open_time").sort_values("open_time")
    for col in ("open", "high", "low", "close", "volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    frame = frame.dropna(subset=["open", "high", "low", "close"]).set_index("open_time")

    # Drop possibly incomplete last candle
    step = _INTERVAL_MS[interval]
    last_close_ms = int(frame.index[-1].timestamp() * 1000) + step
    if last_close_ms > int(datetime.now(timezone.utc).timestamp() * 1000):
        frame = frame.iloc[:-1]

    return frame[["open", "high", "low", "close", "volume"]].astype(float)
