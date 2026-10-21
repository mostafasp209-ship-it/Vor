"""Conservative baseline ensemble; research only, not an execution engine."""

from collections.abc import Sequence

from .signals import Decision, Direction, EnsembleDecision, SpecialistOpinion


def combine_opinions(
    opinions: Sequence[SpecialistOpinion],
    *,
    min_specialists: int = 3,
    min_edge: float = 0.15,
) -> EnsembleDecision:
    """Combine opinions with a transparent weighted vote and an abstain path.

    This starter intentionally does not claim statistical independence or calibrated
    probabilities. Production use needs correlation controls and out-of-sample calibration.
    """
    if min_specialists < 1:
        raise ValueError("min_specialists must be at least 1")
    if not 0.0 <= min_edge <= 1.0:
        raise ValueError("min_edge must be between 0 and 1")
    if not opinions:
        return EnsembleDecision("UNKNOWN", "UNKNOWN", Decision.NO_TRADE, 0.0, 0.0, 0.0, 0,
                                "No specialist opinions provided")

    symbols = {o.symbol for o in opinions}
    timeframes = {o.timeframe for o in opinions}
    if len(symbols) != 1 or len(timeframes) != 1:
        raise ValueError("all opinions must refer to the same symbol and timeframe")

    valid = [o for o in opinions if o.data_quality_ok and o.weight > 0]
    long_support = sum(o.score * o.weight for o in valid if o.direction is Direction.LONG)
    short_support = sum(o.score * o.weight for o in valid if o.direction is Direction.SHORT)
    total = sum(o.weight for o in valid)
    long_norm = long_support / total if total else 0.0
    short_norm = short_support / total if total else 0.0
    edge = abs(long_norm - short_norm)

    decision = Decision.NO_TRADE
    reason = "Insufficient valid specialist evidence or insufficient directional edge"
    confidence = max(long_norm, short_norm)
    if len(valid) >= min_specialists and edge >= min_edge:
        if long_norm > short_norm:
            decision, reason = Decision.LONG, "Weighted long support exceeds short support"
        elif short_norm > long_norm:
            decision, reason = Decision.SHORT, "Weighted short support exceeds long support"

    return EnsembleDecision(next(iter(symbols)), next(iter(timeframes)), decision,
                            confidence, long_norm, short_norm, len(valid), reason)
