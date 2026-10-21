"""Registry for a 5,000-slot specialist ensemble.

These are configurable evaluation slots grouped by expertise, not 5,000 real humans,
independent models, or a claim of consensus. Most slots are placeholders until a tested
strategy implementation is attached.
"""
from __future__ import annotations

DOMAINS = (
    "trend_following", "mean_reversion", "breakout", "price_action", "candlesticks",
    "support_resistance", "market_structure", "momentum", "volume_profile", "volume_flow",
    "volatility", "market_regime", "multi_timeframe", "moving_averages", "rsi_stochastics",
    "macd_momentum", "bollinger_bands", "vwap", "order_book", "liquidity",
    "funding_rates", "open_interest", "basis_spread", "liquidations", "perpetual_futures",
    "spot_flows", "on_chain_activity", "exchange_flows", "stablecoin_flows", "tokenomics",
    "protocol_fundamentals", "macro_economics", "correlations", "cross_asset", "sentiment",
    "news_events", "social_metrics", "calendar_effects", "seasonality", "statistical_arbitrage",
    "cross_exchange_arbitrage", "pairs_trading", "market_making_research", "execution_costs",
    "portfolio_allocation", "risk_management", "drawdown_control", "regime_validation",
    "walk_forward_validation", "data_quality",
)


def specialist_slots(per_domain: int = 100) -> list[dict[str, object]]:
    """Return metadata for 50 x 100 = 5,000 virtual research slots."""
    if per_domain < 1:
        raise ValueError("per_domain must be >= 1")
    return [
        {"id": f"{domain}-{index:03d}", "domain": domain, "status": "placeholder", "weight": 0.0}
        for domain in DOMAINS
        for index in range(1, per_domain + 1)
    ]
