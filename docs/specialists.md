# The 50 specialist domains

Each specialist owns one narrow analytical responsibility and returns a standardized, timestamped result. A specialist may abstain; it must not invent unavailable data. The list is a proposed architecture, not a claim that 50 independent models already exist.

1. Market data quality and missing-value detection
2. Multi-timeframe trend structure
3. Price action and swing structure
4. Support and resistance zones
5. Breakout and false-breakout analysis
6. Momentum indicators
7. Mean-reversion conditions
8. Volatility regime classification
9. Volume and volume-profile analysis
10. Order-book imbalance
11. Spread and liquidity conditions
12. Trade-flow and aggressor imbalance
13. Funding-rate analysis
14. Futures basis and term structure
15. Open-interest changes
16. Liquidation-flow analysis
17. Options implied volatility and skew
18. Options positioning and expiry effects
19. On-chain activity
20. Exchange inflows and outflows
21. Stablecoin supply and flows
22. Network fees and congestion
23. Token unlocks and supply events
24. Project fundamentals and protocol usage
25. Governance and protocol risk events
26. News event classification
27. Social sentiment with bot/noise filtering
28. Search-interest and attention changes
29. Macro rates and liquidity context
30. Dollar and major-asset cross-market relationships
31. BTC/ETH leadership and market breadth
32. Cross-asset correlation shifts
33. Statistical trend and time-series features
34. Cointegration and relative-value candidates
35. Market-regime detection
36. Anomaly and manipulation detection
37. Asset-specific liquidity risk
38. Exchange and counterparty risk
39. Volatility-based position sizing
40. Stop and invalidation-level evaluation
41. Reward-to-risk and target feasibility
42. Portfolio exposure and concentration
43. Correlated-position and drawdown control
44. Transaction-cost and slippage estimation
45. Funding and carry-cost estimation
46. Signal calibration and probability quality
47. Historical analog and pattern validation
48. Backtest integrity and leakage detection
49. Strategy monitoring and drift detection
50. Ensemble coordination, disagreement, and abstention

## Output contract

Every specialist should return:
- specialist ID and version
- observation timestamp and data cutoff
- asset, venue, and timeframe
- direction: `LONG`, `SHORT`, or `NEUTRAL`
- calibrated probability or score, with method documented
- evidence/features used and data-quality flags
- validity horizon and invalidation conditions
- explicit abstention reason when applicable

The ensemble should account for correlated specialists so that five variations of the same indicator do not count as five independent votes. Missing or stale inputs should reduce confidence or force `NO_TRADE`.
