# Initial architecture

## Pipeline

1. **Ingestion:** fetch market and alternative data with source timestamps.
2. **Validation:** check gaps, duplicates, timezone consistency, outliers, and stale feeds.
3. **Features:** calculate reproducible features using only information available at decision time.
4. **Specialists:** run the 50 isolated analytical modules.
5. **Ensemble:** normalize outputs, discount correlated evidence, account for regime and data quality, and measure disagreement.
6. **Risk gate:** enforce liquidity, exposure, drawdown, and reward-to-risk constraints.
7. **Signal record:** emit a versioned decision or abstain.
8. **Evaluation:** log decisions and compare predicted outcomes with realized results.

## Signal schema (conceptual)

- `symbol`, `venue`, `timeframe`, `as_of`
- `decision`: `LONG` | `SHORT` | `NO_TRADE`
- `confidence`: calibrated value in [0, 1], once calibration exists
- `entry`, `invalidation`, `targets`: optional estimates, never guarantees
- `risk_budget`: bounded by portfolio-level rules
- `supporting_specialists`, `opposing_specialists`
- `data_quality`, `model_version`, `reason_codes`

## Validation gates

- Chronological train/validation/test split; no random shuffling of time series.
- Walk-forward evaluation and a final untouched holdout.
- Realistic fees, spread, slippage, funding, and execution delay.
- Report expectancy, drawdown, turnover, exposure, calibration, and benchmark-relative performance.
- Test multiple market regimes and assets; account for multiple-testing/data-snooping risk.
- Paper-trade and monitor drift before any live deployment.

## Safety defaults

- No live orders by default.
- No leverage by default.
- No hard-coded secrets; use environment variables or a secret manager.
- Fail closed on stale data, missing risk limits, or invalid calculations.
- Every signal and risk rejection must be logged for audit.
