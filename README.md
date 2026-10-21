# Crypto Quant Lab

A research-first framework for cryptocurrency market analysis and signal evaluation. The project combines 50 narrowly scoped specialist modules into a transparent ensemble; it does **not** assume that more agents automatically means better predictions.

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

## Initial roadmap

1. Define data contracts and specialist interfaces.
2. Add data validation and reproducible feature generation.
3. Implement specialists incrementally, each with tests and a documented hypothesis.
4. Build a weighted, regime-aware ensemble with a `NO_TRADE` path.
5. Backtest chronologically and run paper trading before considering live use.

## Status

Initial project scaffold. No profitable edge has been established; all strategies require independent validation. This software is for research and is not financial advice.


## Running the baseline backtest

Install the base dependencies and the optional public-market data connector:

```bash
pip install -e '.[dev,market-data]'
```

From the repository root, load public hourly BTC/USDT candles and evaluate the current EMA/RSI baseline:

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

The backtester only uses candles available at each signal timestamp and applies that signal to the following close-to-close return. Returns are historical simulation results, not a forecast. This first version does not model funding, dynamic spreads, market impact, or live execution, and has not yet been run against live-fetched data in this environment.


## Specialist ensemble

The first executable ensemble contains two transparent signal specialists (EMA trend and RSI momentum) and a volatility gate. It records each specialist's vote and rationale, and abstains with `NO_TRADE` when history is too short or volatility is unusually high:

```python
from crypto_quant.ensemble import analyze_ensemble

decision = analyze_ensemble(candles)
print(decision.action, decision.score, decision.confidence)
for opinion in decision.opinions:
    print(opinion.name, opinion.vote, opinion.confidence, opinion.reason)
print(decision.reasons)
```

The registry describes 5,000 virtual slots across 50 research domains, but those slots are placeholders—not 5,000 trained models or real analysts. Only the specialists with implemented and tested logic should contribute to decisions. Automated tests run through GitHub Actions on pushes and pull requests.


## Evaluate a 5,000-candidate OHLCV population

The research population now generates 5,000 deterministic parameter configurations across five executable OHLCV strategy families: EMA trend, RSI reversion, breakout, momentum, and volatility-filtered trend. This is a 5,000-candidate search, not 5,000 independent AI experts.

```python
from crypto_quant.market_data import fetch_public_ohlcv
from crypto_quant.population import evaluate_population

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
print("evaluated:", report["evaluated_candidates"])
print("train/holdout:", report["train_candles"], report["holdout_candles"])
for candidate in report["top_candidates"]:
    print(candidate)
```

Candidates are ranked on the first 70% of the chronological series; the final 30% is reported as holdout for the training-selected candidates. This reduces, but does not eliminate, overfitting. The available OHLCV feed cannot substantiate strategies requiring news, order-book, funding, derivatives, or on-chain data; those must not be simulated as if real inputs existed.
