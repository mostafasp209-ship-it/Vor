"""Initial, deliberately small registry of distinct trading research roles."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ExpertProfile:
    agent_id: str
    name: str
    specialty: str
    method_checklist: tuple[str, ...]
    failure_modes: tuple[str, ...]
    search_topics: tuple[str, ...]

_PROFILES = (
    ExpertProfile("price_action_rt", "RTM-style price-action researcher", "price action and supply/demand methodology",
      ("Describe structure and relevant zones", "State evidence and counter-evidence", "Define invalidation before any conclusion"),
      ("Retrospective pattern fitting", "Treating zones as objectively certain"), ("RTM price action", "supply demand trading evidence", "price action backtesting")),
    ExpertProfile("price_action_brooks", "Al Brooks-style price-action researcher", "bar-by-bar price action methodology",
      ("Classify trend or trading range", "Describe signal bar and context", "Check follow-through and failed breakouts"),
      ("Reading too much into one bar", "Ignoring transaction costs"), ("Al Brooks price action", "bar by bar trading", "price action trend trading research")),
    ExpertProfile("trend_momentum", "Trend and momentum researcher", "trend persistence and momentum",
      ("Identify trend and timeframe", "Check momentum persistence", "Test lag and whipsaw sensitivity"),
      ("Late entries", "Regime shifts and whipsaws"), ("trend following research", "time series momentum", "trend regime backtesting")),
    ExpertProfile("volatility_regime", "Volatility and regime researcher", "volatility and market regimes",
      ("Estimate volatility regime", "Compare current context with historical regimes", "Specify regime-change risk"),
      ("Unstable regime labels", "Look-ahead leakage"), ("volatility regime detection", "financial time series regimes")),
    ExpertProfile("market_structure", "Market structure and microstructure researcher", "liquidity, spreads, and market microstructure",
      ("Separate observable data from interpretation", "Consider spread, depth, and liquidity", "Identify execution assumptions"),
      ("Inferring hidden liquidity from candles alone", "Ignoring slippage"), ("market microstructure", "limit order book liquidity", "crypto market slippage research")),
    ExpertProfile("risk_auditor", "Independent risk and evidence auditor", "risk controls and skeptical review",
      ("Seek falsifying evidence", "Check costs and drawdown", "Reject unsupported certainty"),
      ("False precision", "Survivorship and selection bias"), ("backtest overfitting", "trading risk management", "walk forward validation")),
)

def default_experts() -> tuple[ExpertProfile, ...]:
    """Return distinct starter roles; these are profiles, not claims of human expertise."""
    return _PROFILES

def get_expert(agent_id: str) -> ExpertProfile:
    for profile in _PROFILES:
        if profile.agent_id == agent_id:
            return profile
    raise KeyError(f"Unknown expert profile: {agent_id}")
