# Crypto Quant Lab (Vor)

A research-first framework for cryptocurrency market analysis and signal evaluation. The project combines narrowly scoped specialist modules into a transparent ensemble; it does **not** assume that more agents automatically means better predictions.

## Current scope

- Produce `LONG`, `SHORT`, or `NO_TRADE` candidates with confidence, rationale, invalidation, and risk metadata.
- Keep specialist outputs separate and auditable before combining them.
- Validate ideas with walk-forward backtests, fees, slippage, and out-of-sample tests.
- Default to research and paper trading. Live execution is out of scope until explicit safeguards and tests exist.

## Design principles

1. No look-ahead or survivorship leakage.
2. Compare every model with simple baselines.
3. Include fees, spread, funding, slippage, and latency where applicable.
4. Calibrate confidence; abstain when evidence is weak or specialists disagree.
5. Cap portfolio risk independently of signal confidence.
6. Never put API keys, exchange secrets, or account identifiers in source control.

## Status

Research scaffold with executable baselines. **No profitable edge has been established.** All strategies require independent validation. This software is not financial advice.

## Install

```bash
pip install -e '.[dev,market-data]'
```

## Reference strategy (RSI / Stochastic RR 1.5)

Aligned with the production logic used in `crypto-signal-bot`:

| Rule | Value |
|------|--------|
| Market data | Binance USD-M perpetual 4H |
| Direction | Long + Short |
| Entry | Next candle open |
| RSI | Recovery from 30 / 70 |
| Stochastic | Real cross in extreme zones |
| Volume | > 1.12 × 20-bar MA |
| Stop | 5-bar swing vs 1.32×ATR |
| Target | 1.5R single target |
| Costs | Fee 0.05% + slippage 0.02% |

```bash
python scripts/run_reference_backtest.py --symbols BTCUSDT,ETHUSDT --since 2022-01-01
```

Or in Python:

```python
from crypto_quant.futures_data import fetch_futures_klines
from crypto_quant.reference_strategy import backtest_reference, evaluate_gates

df = fetch_futures_klines("BTCUSDT", "4h", since="2022-01-01")
print(evaluate_gates(df))
print(backtest_reference(df))
```

Results are historical simulations only. Same-bar SL/TP collisions are treated stop-first. Funding is not fully event-synced in this light path.

## Baseline EMA/RSI backtest

```python
from crypto_quant.market_data import fetch_public_ohlcv
from crypto_quant.backtest import run_backtest

candles = fetch_public_ohlcv(
    exchange_id="binance",
    symbol="BTC/USDT",
    timeframe="1h",
    limit=500,
)
result = run_backtest(candles, fee_bps=10, slippage_bps=5)
for key in ("candles", "total_return", "max_drawdown", "sharpe_annualized",
            "win_rate", "total_cost", "trades_or_rebalances"):
    print(f"{key}: {result[key]}")
```

## Specialist ensemble

```python
from crypto_quant.ensemble import analyze_ensemble

decision = analyze_ensemble(candles)
print(decision.action, decision.score, decision.confidence)
```

The registry may describe many virtual specialist slots; only implemented and tested logic should contribute to decisions.

## Tests

```bash
pytest -q
```

GitHub Actions runs the suite on pushes and pull requests.
