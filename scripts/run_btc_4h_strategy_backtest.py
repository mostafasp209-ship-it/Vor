"""Run a one-year BTCUSDT 4h research sweep with a chronological holdout."""
from __future__ import annotations

import json
from pathlib import Path

from crypto_quant.strategy_backtest import fetch_binance_klines, parameter_sweep, backtest_breakout_volume, backtest_multiconfluence_rtm


def main() -> None:
    data = fetch_binance_klines("BTCUSDT", "4h", days=365)
    if len(data) < 300:
        raise RuntimeError(f"Not enough candles returned: {len(data)}")
    split = int(len(data) * 0.70)
    holdout_start = data.index[split]
    train = data.iloc[:split]
    # The full frame supplies indicator warm-up, while start_at prevents pre-holdout entries.
    sweep = parameter_sweep(train, min_trades=5)
    out = Path("reports")
    out.mkdir(exist_ok=True)
    sweep.to_csv(out / "btc_4h_train_sweep.csv", index=False)
    summary = {
        "symbol": "BTCUSDT", "interval": "4h", "candles": len(data),
        "first_candle": str(data.index[0]), "last_candle": str(data.index[-1]),
        "train_candles": len(train), "holdout_candles": len(data) - split,
        "holdout_start": str(holdout_start), "fee_bps_per_side": 10,
        "slippage_bps_per_side": 5,
        "warning": "Public OHLCV backtest only; not a profitability guarantee. Same-candle stop/target assumes stop first.",
        "top_train_candidates": [],
        "holdout_results": [],
    }
    for _, row in sweep.head(10).iterrows():
        strategy = row["strategy"]
        params = {k: row[k].item() if hasattr(row[k], "item") else row[k]
                  for k in ("rr", "vol_mult", "atr_mult", "lookback", "fib_tol") if k in row and row[k] == row[k]}
        summary["top_train_candidates"].append({"strategy": strategy, "params": params,
            "train_trades": int(row["trades"]), "train_win_rate": float(row["win_rate"]),
            "train_mean_r": float(row["mean_r"]), "train_total_r": float(row["total_r"])})
        if strategy == "breakout_volume":
            result = backtest_breakout_volume(data, start_at=holdout_start, **{
                "rr": float(row["rr"]), "vol_mult": float(row["vol_mult"]),
                "atr_mult": float(row["atr_mult"]), "lookback": int(row["lookback"]),
                "fee_bps": 10, "slippage_bps": 5,
            })
        else:
            result = backtest_multiconfluence_rtm(data, start_at=holdout_start, **{
                "rr": float(row["rr"]), "vol_mult": float(row["vol_mult"]),
                "fib_tol": float(row["fib_tol"]), "fee_bps": 10, "slippage_bps": 5,
            })
        summary["holdout_results"].append({"strategy": strategy, "params": params,
            "trades": result["trades"], "win_rate": result["win_rate"],
            "mean_r": result["mean_r"], "total_r": result["total_r"],
            "profit_factor": result["profit_factor"]})
    (out / "btc_4h_backtest_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("Saved reports/btc_4h_train_sweep.csv and reports/btc_4h_backtest_summary.json")


if __name__ == "__main__":
    main()
