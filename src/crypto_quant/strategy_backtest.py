"""OHLCV-only breakout/volume and Fibonacci-rejection short research backtests.

Signals are confirmed on a candle close; entry is the next candle open.
If both stop and target are touched in one candle, the stop is assumed first.
Research only: OHLCV cannot reveal intrabar path or guarantee executable fills.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000,
    "4h": 14_400_000, "6h": 21_600_000, "8h": 28_800_000,
    "12h": 43_200_000, "1d": 86_400_000,
}


def fetch_binance_klines(
    symbol: str = "BTCUSDT",
    interval: str = "4h",
    days: int = 365,
    *,
    timeout: int = 20,
    pause_seconds: float = 0.15,
) -> pd.DataFrame:
    """Fetch public Binance spot candles with pagination; no API key required."""
    if interval not in _INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    if days < 1:
        raise ValueError("days must be positive")
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = end_ms - days * 86_400_000
    cursor = start_ms
    rows: list[list] = []
    step = _INTERVAL_MS[interval]
    while cursor < end_ms:
        query = urlencode({
            "symbol": symbol.upper(), "interval": interval, "limit": 1000,
            "startTime": cursor, "endTime": end_ms,
        })
        req = Request(
            "https://api.binance.com/api/v3/klines?" + query,
            headers={"User-Agent": "Vor-Research/1.0"},
        )
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected Binance response: {payload}")
        if not payload:
            break
        rows.extend(payload)
        next_cursor = int(payload[-1][0]) + step
        if next_cursor <= cursor:
            raise RuntimeError("Binance pagination did not advance")
        cursor = next_cursor
        if len(payload) < 1000:
            break
        time.sleep(max(0.0, pause_seconds))
    if not rows:
        raise RuntimeError("Binance returned no candles")
    frame = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trade_count", "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    frame = frame.drop_duplicates(subset="open_time").sort_values("open_time")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    frame = frame.set_index("open_time")
    # Exclude a possibly incomplete latest candle.
    last_close_ms = int(frame.index[-1].timestamp() * 1000) + step
    if last_close_ms > int(datetime.now(timezone.utc).timestamp() * 1000):
        frame = frame.iloc[:-1]
    return frame[["open", "high", "low", "close", "volume"]].astype(float)


def _features(df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        df = df.sort_index().loc[lambda x: ~x.index.duplicated(keep="last")]
    data = df.copy()
    for col in required:
        data[col] = pd.to_numeric(data[col], errors="raise")
    if len(data) < max(lookback + 2, 30):
        raise ValueError("Insufficient candles for strategy warm-up")
    if (data[["open", "high", "low", "close", "volume"]] < 0).any().any():
        raise ValueError("OHLCV values must be non-negative")
    if (data["high"] < data[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("High is inconsistent with OHLC values")
    if (data["low"] > data[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("Low is inconsistent with OHLC values")
    previous_close = data["close"].shift(1)
    true_range = pd.concat([
        data["high"] - data["low"],
        (data["high"] - previous_close).abs(),
        (data["low"] - previous_close).abs(),
    ], axis=1).max(axis=1)
    data["atr"] = true_range.rolling(14, min_periods=14).mean()
    data["volume_sma"] = data["volume"].rolling(20, min_periods=20).mean().shift(1)
    data["ma200"] = data["close"].rolling(200, min_periods=200).mean()
    data["prior_high"] = data["high"].rolling(lookback).max().shift(1)
    data["prior_low"] = data["low"].rolling(lookback).min().shift(1)
    return data


def _run_signals(
    data: pd.DataFrame,
    signals: pd.Series,
    *,
    rr: float,
    atr_mult: float,
    max_hold: int,
    fee_bps: float,
    slippage_bps: float,
    start_at=None,
) -> dict:
    if rr <= 0 or atr_mult <= 0 or max_hold < 1:
        raise ValueError("rr and atr_mult must be positive; max_hold must be >= 1")
    if fee_bps < 0 or slippage_bps < 0:
        raise ValueError("fee_bps and slippage_bps must be non-negative")
    cost_rate = (fee_bps + slippage_bps) / 10_000.0
    start_pos = 0
    if start_at is not None:
        start_pos = int(data.index.searchsorted(pd.Timestamp(start_at), side="left"))
    trades: list[dict] = []
    i = max(start_pos, 1)
    while i < len(data) - 1:
        direction = int(signals.iloc[i]) if pd.notna(signals.iloc[i]) else 0
        atr_value = float(data["atr"].iloc[i]) if pd.notna(data["atr"].iloc[i]) else np.nan
        if direction == 0 or not np.isfinite(atr_value) or atr_value <= 0:
            i += 1
            continue
        entry_i = i + 1
        entry = float(data["open"].iloc[entry_i])
        risk = atr_mult * atr_value
        if direction > 0:
            stop, target = entry - risk, entry + rr * risk
        else:
            stop, target = entry + risk, entry - rr * risk
        exit_i = min(entry_i + max_hold - 1, len(data) - 1)
        exit_price, reason, actual_exit_i = float(data["close"].iloc[exit_i]), "time", exit_i
        for j in range(entry_i, exit_i + 1):
            high, low = float(data["high"].iloc[j]), float(data["low"].iloc[j])
            if direction > 0:
                if low <= stop:
                    exit_price, reason, actual_exit_i = min(float(data["open"].iloc[j]), stop), "stop", j
                    break
                if high >= target:
                    exit_price, reason, actual_exit_i = max(float(data["open"].iloc[j]), target), "target", j
                    break
            else:
                if high >= stop:
                    exit_price, reason, actual_exit_i = max(float(data["open"].iloc[j]), stop), "stop", j
                    break
                if low <= target:
                    exit_price, reason, actual_exit_i = min(float(data["open"].iloc[j]), target), "target", j
                    break
        gross_pnl = (exit_price - entry) * direction
        round_trip_cost = (entry + exit_price) * cost_rate
        net_r = (gross_pnl - round_trip_cost) / risk
        trades.append({
            "signal_time": data.index[i], "entry_time": data.index[entry_i],
            "exit_time": data.index[actual_exit_i], "side": "LONG" if direction > 0 else "SHORT",
            "entry": entry, "exit": exit_price, "stop": stop, "target": target,
            "exit_reason": reason, "gross_r": gross_pnl / risk, "net_r": net_r,
        })
        i = actual_exit_i + 1
    trade_frame = pd.DataFrame(trades)
    values = trade_frame["net_r"].to_numpy(dtype=float) if not trade_frame.empty else np.array([])
    wins = values[values > 0]
    losses = values[values < 0]
    gross_wins, gross_losses = float(wins.sum()), float(abs(losses.sum()))
    return {
        "trades": int(len(values)),
        "win_rate": float((values > 0).mean()) if len(values) else 0.0,
        "mean_r": float(values.mean()) if len(values) else 0.0,
        "total_r": float(values.sum()) if len(values) else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses > 0 else (None if gross_wins > 0 else 0.0),
        "trades_frame": trade_frame,
        "note": "Stop is assumed first when stop and target are both inside one candle; fees and slippage are estimated.",
    }


def backtest_breakout_volume(
    df: pd.DataFrame, *, rr: float = 3.0, vol_mult: float = 1.5,
    atr_mult: float = 1.5, lookback: int = 20, max_hold: int = 20,
    trend_filter: bool = True, fee_bps: float = 10.0, slippage_bps: float = 5.0,
    start_at=None,
) -> dict:
    """Long/short close-confirmed range break with volume confirmation."""
    if lookback < 2 or vol_mult <= 0:
        raise ValueError("lookback must be >= 2 and vol_mult must be positive")
    data = _features(df, lookback=lookback)
    volume_ok = data["volume"] > vol_mult * data["volume_sma"]
    long_signal = (data["close"] > data["prior_high"]) & volume_ok
    short_signal = (data["close"] < data["prior_low"]) & volume_ok
    if trend_filter:
        long_signal &= data["close"] > data["ma200"]
        short_signal &= data["close"] < data["ma200"]
    signals = pd.Series(0, index=data.index, dtype=int)
    signals.loc[long_signal.fillna(False)] = 1
    signals.loc[short_signal.fillna(False)] = -1
    return _run_signals(
        data, signals, rr=rr, atr_mult=atr_mult, max_hold=max_hold,
        fee_bps=fee_bps, slippage_bps=slippage_bps, start_at=start_at,
    )


def backtest_multiconfluence_rtm(
    df: pd.DataFrame, *, rr: float = 1.5, atr_mult: float = 1.0,
    vol_mult: float = 2.0, fib_tol: float = 0.5, swing_lookback: int = 60,
    max_hold: int = 30, fee_bps: float = 10.0, slippage_bps: float = 5.0,
    start_at=None,
) -> dict:
    """Short a bearish rejection near swing Fibonacci levels with volume confirmation.

    fib_tol is measured in ATR units, not percent of price. The MA200 filter
    follows the submitted idea: only take the short rejection while close > MA200.
    """
    if vol_mult <= 0 or fib_tol <= 0 or swing_lookback < 10:
        raise ValueError("vol_mult/fib_tol must be positive and swing_lookback >= 10")
    data = _features(df, lookback=swing_lookback)
    swing_high = data["high"].rolling(swing_lookback).max().shift(1)
    swing_low = data["low"].rolling(swing_lookback).min().shift(1)
    span = swing_high - swing_low
    # Retracements measured downward from the prior swing high.
    levels = [swing_high - span * ratio for ratio in (0.382, 0.5, 0.618)]
    near_fib = pd.Series(False, index=data.index)
    for level in levels:
        near_fib |= (data["close"] - level).abs() <= fib_tol * data["atr"]
    body = (data["close"] - data["open"]).abs()
    upper_wick = data["high"] - data[["open", "close"]].max(axis=1)
    rejection = (upper_wick > 1.5 * body) & (data["close"] < data["open"])
    high_volume = data["volume"] > vol_mult * data["volume_sma"]
    signal_mask = near_fib & (data["close"] > data["ma200"]) & high_volume & rejection
    signals = pd.Series(0, index=data.index, dtype=int)
    signals.loc[signal_mask.fillna(False)] = -1
    return _run_signals(
        data, signals, rr=rr, atr_mult=atr_mult, max_hold=max_hold,
        fee_bps=fee_bps, slippage_bps=slippage_bps, start_at=start_at,
    )


def parameter_sweep(df: pd.DataFrame, *, start_at=None, fee_bps: float = 10.0,
                    slippage_bps: float = 5.0, min_trades: int = 10) -> pd.DataFrame:
    """Run a modest, explicit parameter grid; rank by net total R, not win rate alone."""
    rows = []
    for rr in (2.0, 3.0):
        for vol_mult in (1.5, 2.0, 2.5):
            for atr_mult in (1.0, 1.5, 2.0):
                for lookback in (20, 40):
                    result = backtest_breakout_volume(
                        df, rr=rr, vol_mult=vol_mult, atr_mult=atr_mult,
                        lookback=lookback, fee_bps=fee_bps, slippage_bps=slippage_bps,
                        start_at=start_at,
                    )
                    if result["trades"] >= min_trades:
                        rows.append({
                            "strategy": "breakout_volume", "rr": rr, "vol_mult": vol_mult,
                            "atr_mult": atr_mult, "lookback": lookback, **{
                                k: result[k] for k in ("trades", "win_rate", "mean_r", "total_r", "profit_factor")
                            },
                        })
    for rr in (1.5, 2.0, 3.0):
        for vol_mult in (1.5, 2.0, 2.5):
            for fib_tol in (0.3, 0.5, 0.8):
                result = backtest_multiconfluence_rtm(
                    df, rr=rr, vol_mult=vol_mult, fib_tol=fib_tol,
                    fee_bps=fee_bps, slippage_bps=slippage_bps, start_at=start_at,
                )
                if result["trades"] >= min_trades:
                    rows.append({
                        "strategy": "multiconfluence_rtm_short", "rr": rr,
                        "vol_mult": vol_mult, "atr_mult": 1.0, "lookback": 60,
                        "fib_tol": fib_tol, **{
                            k: result[k] for k in ("trades", "win_rate", "mean_r", "total_r", "profit_factor")
                        },
                    })
    columns = ["strategy", "rr", "vol_mult", "atr_mult", "lookback", "fib_tol",
               "trades", "win_rate", "mean_r", "total_r", "profit_factor"]
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["total_r", "mean_r"], ascending=False, ignore_index=True
    )
