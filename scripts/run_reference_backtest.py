#!/usr/bin/env python3
"""Run the reference RSI/Stoch RR1.5 strategy on Binance USD-M 4H data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running without install
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crypto_quant.futures_data import fetch_futures_klines  # noqa: E402
from crypto_quant.reference_strategy import backtest_reference  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Reference futures 4H backtest")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT")
    parser.add_argument("--since", default="2022-01-01")
    parser.add_argument("--out", default="research_out/reference_report.json")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    results = []
    for sym in symbols:
        print(f"[fetch] {sym}")
        try:
            df = fetch_futures_klines(sym, "4h", since=args.since)
            print(f"  bars={len(df)}  {df.index[0]} → {df.index[-1]}")
            res = backtest_reference(df)
            res["symbol"] = sym
        except Exception as exc:  # noqa: BLE001
            res = {"symbol": sym, "error": f"{type(exc).__name__}: {exc}"}
        results.append(res)
        print(f"  -> {res}")

    report = {
        "strategy": "REFERENCE_RSI_STOCH_ATR_RR15",
        "status": "RESEARCH_ONLY_NOT_VALIDATED",
        "results": results,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
