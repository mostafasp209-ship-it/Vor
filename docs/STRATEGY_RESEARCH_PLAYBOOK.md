# Vor Strategy Research Playbook

This file is the research specification used by the automated search. It is a set of
testable hypotheses, not a claim that any named indicator is profitable.

## 1. Feature inventory

- Trend: SMA, EMA, WMA, HMA, MACD, ADX, +DI/-DI, Ichimoku, Supertrend, Parabolic SAR.
- Momentum: RSI, Stochastic, Stoch RSI, CCI, Williams %R, ROC.
- Volatility: ATR, ATR%, realized volatility, Bollinger Bands/width, Keltner Channels,
  candle range/body in ATR units.
- Volume/flow: relative volume, volume z-score, MFI, OBV/slope, CMF, rolling VWAP.
- Structure: prior Donchian highs/lows, rolling range position, engulfing candles,
  pin-bar anatomy.
- Context: trend-strength and volatility descriptors for later regime-conditioned tests.

All calculations must be causal: a feature at candle t may use only data available by
the close of t. A signal at t is executed no earlier than the open of t+1.

## 2. Strategy hypotheses

1. Trend pullback: trade a momentum reset only when the higher trend remains intact.
2. Breakout: trade close-confirmed breaks of prior rolling highs/lows.
3. Mean reversion: fade statistically extended moves only when a trend filter does not
   indicate a strong directional regime.
4. Directional momentum: require trend alignment, directional movement and positive
   short-horizon return.
5. Range expansion: require a large body/range relative to ATR and directional alignment.
6. MACD cross: test momentum transition with a trend constraint.
7. Stochastic reversal: test oscillator turns in a trend-aligned pullback.
8. Bollinger reversion: test re-entry from outer bands with a context filter.
9. Bollinger breakout: test band expansion and close outside the envelope.
10. Donchian breakout: test close beyond prior N-bar extrema.
11. VWAP reclaim: test a reclaim/loss of rolling VWAP with volume-flow confirmation.
12. Ichimoku trend: require price/cloud and Tenkan/Kijun alignment.
13. Supertrend follow: test direction flips with a slower trend confirmation.
14. CCI reversal: test recovery through extreme thresholds in trend context.
15. MFI flow: test money-flow regime changes with CMF confirmation.
16. Parabolic SAR: test stop-and-reverse direction changes with trend alignment.
17. HMA momentum: test slope and price alignment with a momentum confirmation.
18. Candle structure: test engulfing/pin-bar anatomy only at a trend/VWAP location.
19. TSI momentum: test double-smoothed momentum crosses with trend confirmation.
20. Aroon trend: test changes in the age of rolling highs/lows.
21. KAMA regime: test adaptive moving-average slope and price alignment.
22. Squeeze breakout: test volatility compression followed by band expansion.
23. Choppiness trend: test exits from sideways regimes with directional confirmation.
24. Ultimate oscillator: test multi-horizon buying-pressure transitions.
25. Fisher reversal: test bounded Fisher-transform turns near extremes.
26. Donchian midline: test rolling range-midpoint reclaim/loss with trend alignment.

The search must test Long and Short symmetrically, and report them separately before
any combined portfolio conclusion. A qualifying result must contain at least 10 winners
and 10 losers; a nominally infinite payoff ratio from zero losing trades is not accepted. Do not assume one direction or asset behaves like
another.

## 3. Mathematical acceptance

Net trade return is normalized by initial price risk (R). Report at minimum:
trade count, net win rate, average winning R, average losing R, realized payoff ratio,
expectancy R/trade, total R, profit factor and maximum drawdown R.

The realized payoff ratio is mean(net R of winners) divided by the absolute mean(net R
of losers). A configured target of 3R is not evidence that realized payoff is 3:1.
Fees and slippage must be charged on entry and every exit, including time exits.

The user's discovery target is a hard gate:
- net win rate >= 70%;
- realized average win/loss >= 3.0;
- positive expectancy;
- sufficient trade count;
- stability across chronological folds and multiple markets.

Never lower the thresholds automatically to manufacture a winner. If no candidate
passes, report SEARCHING/NO QUALIFIED CANDIDATE and preserve the failure evidence.

## 4. How the optimizer adapts

Each generation:
- samples new candidates across the rule families;
- retains the highest-scoring diverse candidates;
- mutates their parameters to explore nearby hypotheses;
- keeps exploring fresh candidates to avoid collapsing into one family;
- records failed gates by family and the best candidates/metrics per generation;
- checkpoints the generation, elite population and failure counters for resumption.

A candidate's score rewards the weakest fold's expectancy, trade count and profit factor,
while penalizing drawdown. Families with better historical qualification rates receive
more exploitation weight; under-tested families receive an exploration bonus. Candidate
progress is checkpointed so an interrupted generation can resume without re-counting
completed trials. Baseline winners must also retain positive expectancy under 1.5x fees
and 2x slippage. This is a search heuristic, not a probability of future profit.

## 5. Research controls and known gaps

- No future candle values, no same-candle close fills, no random shuffling of time.
- Stop-first assumption when stop and target are both touched in one OHLC candle.
- Current execution model is approximate; funding, variable spread, order-book impact,
  liquidation, partial fills and exchange-specific trigger behavior remain to be added.
- OHLC candles cannot reveal the true intrabar price path.
- Repeatedly trying many configurations creates selection bias. Preserve the full trial
  count and rejected-candidate evidence; never present the best backtest alone.
- Historical walk-forward passes are not independent future validation. A winning
  candidate must be frozen and paper-traded on unseen candles before live consideration.
- No live order placement is permitted from this research workflow.

## 6. Research references

- Bailey, Borwein, López de Prado and Zhu, *The Probability of Backtest Overfitting*,
  Journal of Computational Finance (2017): https://escholarship.org/uc/item/4w1110bb
- Arian, Norouzi Mobarakeh and Seco, *Backtest overfitting in the machine learning era*
  (2024): https://doi.org/10.1016/j.knosys.2024.112477

The research process should optimize for reproducible evidence and robustness, not for
a visually impressive historical equity curve.
