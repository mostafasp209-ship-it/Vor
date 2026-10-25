# BTCUSDT 4h breakout and RTM research backtest

This implementation replaces the malformed pasted snippet with a reproducible OHLCV-only baseline for:

1. Breakout + volume: close breaks the prior rolling high/low (current candle excluded), with volume above its rolling mean and optional MA200 trend filter.
2. Multi-confluence RTM short: bearish upper-wick rejection near prior-swing Fibonacci retracement levels, high relative volume, and close above MA200 as in the submitted hypothesis.

## Run a one-year public-data evaluation

Install the project and test dependencies:

```bash
pip install -e '.[dev]'
python scripts/run_btc_4h_strategy_backtest.py
```

The script fetches public BTCUSDT spot candles from Binance without an API key, sweeps parameters on the first 70% of the chronological series, and reports the top training candidates on the final 30% holdout. It writes:
- `reports/btc_4h_train_sweep.csv`
- `reports/btc_4h_backtest_summary.json`

Cost assumptions default to 10 bps fee plus 5 bps slippage **per side**. The stop distance is ATR-based. Signals are confirmed at close and entered at the next candle open. If stop and target are both crossed within the same OHLC candle, stop is conservatively assumed first. Gaps are filled at the worse of the open and the relevant level.

## Interpretation and limitations

- Ranking is by net total R, not win rate alone; only training data selects parameters.
- A small trade count, especially for the RTM setup, is weak evidence; increase the history and report uncertainty.
- This is not a tick/order-book simulator and does not model spread dynamics, partial fills, latency, funding, or market impact.
- OHLCV-based backtests do not establish future profitability. Never select a strategy solely to force a 70% win rate or a 1:3 risk/reward target.
- Network fetch may fail because of local connectivity or exchange API availability; unit tests are offline.
