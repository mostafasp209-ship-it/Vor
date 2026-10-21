"""Fetch public BTC/USDT candles and evaluate the 5,000-candidate population."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from crypto_quant.market_data import fetch_public_ohlcv
from crypto_quant.population import evaluate_population


def main() -> None:
    candles = fetch_public_ohlcv(
        exchange_id="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        limit=1000,
    )
    report = evaluate_population(
        candles,
        size=5000,
        fee_bps=10,
        slippage_bps=5,
        train_fraction=0.7,
        report_top=20,
    )
    report["symbol"] = "BTC/USDT"
    report["exchange"] = "binance"
    report["timeframe"] = "1h"
    report["latest_candle_utc"] = candles.index[-1].isoformat()
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    output = Path("artifacts")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "btc_usdt_population_report.json"
    target.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Report saved: {target}")
    print(f"Candles: {report['candles']}; candidates evaluated: {report['evaluated_candidates']}")
    print(f"Training candles: {report['train_candles']}; holdout candles: {report['holdout_candles']}")
    for candidate in report["top_candidates"][:5]:
        print(json.dumps(candidate, sort_keys=True))


if __name__ == "__main__":
    main()
