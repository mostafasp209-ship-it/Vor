"""Fetch public BTC/USD candles and train/evaluate 5,000 unique ML agents."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from crypto_quant.market_data import fetch_public_ohlcv
from crypto_quant.ai_population import evaluate_ai_population

def main() -> None:
    exchange_id, symbol = "kraken", "BTC/USD"
    candles = fetch_public_ohlcv(exchange_id=exchange_id, symbol=symbol, timeframe="1h", limit=720)
    report = evaluate_ai_population(candles, size=5000, fee_bps=10, slippage_bps=5,
                                    train_fraction=0.7, report_top=20)
    report.update({"symbol": symbol, "exchange": exchange_id, "timeframe": "1h",
                   "latest_candle_utc": candles.index[-1].isoformat(),
                   "generated_at_utc": datetime.now(timezone.utc).isoformat()})
    output = Path("artifacts")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "btc_usd_ai_population_report.json"
    target.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Report saved: {target}")
    print(f"Trained agents: {report['trained_agents']} / {report['population_size']}")
    print(f"Unique model configurations: {report['unique_model_configurations']}")
    print(f"Train candles: {report['train_candles']}; holdout candles: {report['holdout_candles']}")
    for candidate in report["top_agents"][:5]:
        print(json.dumps(candidate, sort_keys=True))

if __name__ == "__main__":
    main()
