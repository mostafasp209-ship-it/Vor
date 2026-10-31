"""Reference mean-reversion strategy aligned with crypto-signal-bot production logic.

Rules (research mirror of the live signal bot):
- 4H bars, long and short
- RSI recovery from 30 / 70
- Real Stochastic cross in extreme zones (K<38 long, K>62 short)
- Volume > 1.12 × 20-bar average
- Entry at next candle open (± slippage)
- Stop: 5-bar swing vs 1.32×ATR
- Single target at RR 1.5
- Conservative same-bar SL/TP (stop first); gap through stop fills at open

Research only. Not a profitability claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0002
RR = 1.5
VOL_MULT = 1.12
ATR_MULT = 1.32
RSI_LOW = 30.0
RSI_HIGH = 70.0
STOCH_LONG_MAX = 38.0
STOCH_SHORT_MIN = 62.0


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-12)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def _stochastic(
    high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3
) -> tuple[pd.Series, pd.Series]:
    lowest = low.rolling(k_period).min()
    highest = high.rolling(k_period).max()
    k = 100 * (close - lowest) / (highest - lowest + 1e-12)
    return k, k.rolling(d_period).mean()


@dataclass(frozen=True)
class ReferenceGates:
    signal_long: bool
    signal_short: bool
    rsi: Optional[float]
    stoch_k: Optional[float]
    stoch_d: Optional[float]
    volume_ratio: Optional[float]
    atr: Optional[float]


def evaluate_gates(ohlcv: pd.DataFrame) -> ReferenceGates:
    """Evaluate the latest closed bar for long/short gates."""
    required = {"open", "high", "low", "close", "volume"}
    if ohlcv is None or len(ohlcv) < 140 or not required.issubset(ohlcv.columns):
        return ReferenceGates(False, False, None, None, None, None, None)

    work = ohlcv.copy()
    for col in required:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=list(required))
    if len(work) < 140:
        return ReferenceGates(False, False, None, None, None, None, None)

    close, high, low = work["close"], work["high"], work["low"]
    rsi = _rsi(close)
    atr = _atr(high, low, close)
    sk, sd = _stochastic(high, low, close)
    vol_ma = work["volume"].rolling(20, min_periods=20).mean()

    i = len(work) - 1
    vals = [
        rsi.iloc[i - 1],
        rsi.iloc[i],
        atr.iloc[i],
        sk.iloc[i - 1],
        sd.iloc[i - 1],
        sk.iloc[i],
        sd.iloc[i],
        vol_ma.iloc[i],
        work["volume"].iloc[i],
    ]
    if any(pd.isna(v) for v in vals):
        return ReferenceGates(False, False, None, None, None, None, None)

    rp, rn, atr_now, kp, dp, kn, dn, vm, volume = (float(v) for v in vals)
    if vm <= 0 or atr_now <= 0:
        return ReferenceGates(False, False, None, None, None, None, None)

    candle = work.iloc[i]
    long_cross = kp <= dp and kn > dn and kn < STOCH_LONG_MAX
    short_cross = kp >= dp and kn < dn and kn > STOCH_SHORT_MIN
    long_rsi = rp < RSI_LOW and rn >= RSI_LOW
    short_rsi = rp > RSI_HIGH and rn <= RSI_HIGH
    vol_ok = volume > VOL_MULT * vm

    return ReferenceGates(
        signal_long=bool(long_rsi and long_cross and vol_ok and candle["close"] > candle["open"]),
        signal_short=bool(short_rsi and short_cross and vol_ok and candle["close"] < candle["open"]),
        rsi=rn,
        stoch_k=kn,
        stoch_d=dn,
        volume_ratio=volume / vm,
        atr=atr_now,
    )


def backtest_reference(
    ohlcv: pd.DataFrame,
    *,
    rr: float = RR,
    fee_rate: float = FEE_RATE,
    slippage: float = SLIPPAGE_RATE,
    vol_mult: float = VOL_MULT,
    atr_mult: float = ATR_MULT,
) -> dict:
    """Full-series next-open backtest of the reference strategy."""
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(ohlcv.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(ohlcv.columns))}")

    df = ohlcv.copy()
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=list(required))
    if len(df) < 160:
        raise ValueError("Need at least 160 bars")

    df["rsi"] = _rsi(df["close"])
    df["atr"] = _atr(df["high"], df["low"], df["close"])
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["sk"], df["sd"] = _stochastic(df["high"], df["low"], df["close"])
    df = df.dropna().reset_index(drop=True)
    n = len(df)

    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    rsi = df["rsi"].to_numpy(float)
    atr = df["atr"].to_numpy(float)
    vol = df["volume"].to_numpy(float)
    volma = df["vol_ma"].to_numpy(float)
    sk = df["sk"].to_numpy(float)
    sd = df["sd"].to_numpy(float)

    trades: list[float] = []
    sides: list[str] = []
    pos = 0
    entry = stop = target = 0.0
    i = 5
    while i < n - 1:
        if pos != 0:
            exit_p = None
            if pos == 1:
                if o[i] < stop:
                    exit_p = o[i]
                else:
                    hs, ht = l[i] <= stop, h[i] >= target
                    if hs and ht:
                        exit_p = stop
                    elif hs:
                        exit_p = stop
                    elif ht:
                        exit_p = target
            else:
                if o[i] > stop:
                    exit_p = o[i]
                else:
                    hs, ht = h[i] >= stop, l[i] <= target
                    if hs and ht:
                        exit_p = stop
                    elif hs:
                        exit_p = stop
                    elif ht:
                        exit_p = target
            if exit_p is not None:
                exit_p = exit_p * (1 - slippage) if pos == 1 else exit_p * (1 + slippage)
                risk = abs(entry - stop)
                if risk > 1e-12:
                    raw = (exit_p - entry) / risk if pos == 1 else (entry - exit_p) / risk
                    cost = (fee_rate + slippage) * (entry + exit_p) / risk
                    trades.append(raw - cost)
                    sides.append("LONG" if pos == 1 else "SHORT")
                pos = 0
            i += 1
            continue

        vol_ok = vol[i] > vol_mult * volma[i]
        stoch_up = sk[i - 1] <= sd[i - 1] and sk[i] > sd[i] and sk[i] < STOCH_LONG_MAX
        stoch_dn = sk[i - 1] >= sd[i - 1] and sk[i] < sd[i] and sk[i] > STOCH_SHORT_MIN
        rsi_long = rsi[i - 1] < RSI_LOW and rsi[i] >= RSI_LOW
        rsi_short = rsi[i - 1] > RSI_HIGH and rsi[i] <= RSI_HIGH
        long_sig = rsi_long and stoch_up and vol_ok and c[i] > o[i]
        short_sig = rsi_short and stoch_dn and vol_ok and c[i] < o[i]

        if long_sig or short_sig:
            raw_entry = o[i + 1]
            if long_sig:
                pos = 1
                entry = raw_entry * (1 + slippage)
                swing = float(np.min(l[max(0, i - 4) : i + 1]))
                stop = min(swing, entry - atr[i] * atr_mult)
                risk = entry - stop
            else:
                pos = -1
                entry = raw_entry * (1 - slippage)
                swing = float(np.max(h[max(0, i - 4) : i + 1]))
                stop = max(swing, entry + atr[i] * atr_mult)
                risk = stop - entry
            if 0.0035 * entry < risk < 0.038 * entry:
                target = entry + pos * risk * rr
                i += 2
                continue
            pos = 0
        i += 1

    if pos != 0:
        exit_p = c[-1] * (1 - slippage) if pos == 1 else c[-1] * (1 + slippage)
        risk = abs(entry - stop)
        if risk > 1e-12:
            raw = (exit_p - entry) / risk if pos == 1 else (entry - exit_p) / risk
            cost = (fee_rate + slippage) * (entry + exit_p) / risk
            trades.append(raw - cost)
            sides.append("LONG" if pos == 1 else "SHORT")

    if not trades:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "total_r": 0.0,
            "max_dd_r": 0.0,
            "long_trades": 0,
            "short_trades": 0,
            "note": "no trades",
        }

    rs = np.asarray(trades, dtype=float)
    wins = rs > 0
    equity = np.cumsum(rs)
    peak = np.maximum.accumulate(equity)
    max_dd = float((peak - equity).max()) if len(equity) else 0.0
    long_n = sum(1 for s in sides if s == "LONG")
    short_n = sum(1 for s in sides if s == "SHORT")
    return {
        "trades": int(len(rs)),
        "win_rate": float(wins.mean()),
        "expectancy_r": float(rs.mean()),
        "profit_factor": float(
            abs(rs[wins].sum() / rs[~wins].sum()) if (~wins).any() and abs(rs[~wins].sum()) > 1e-9 else 99.0
        ),
        "total_r": float(rs.sum()),
        "max_dd_r": max_dd,
        "long_trades": long_n,
        "short_trades": short_n,
        "note": (
            "Research simulation only. Next-open entry, fee+slippage, stop-first collisions. "
            "Not validated for live trading."
        ),
    }
