from datetime import datetime, timezone

from crypto_quant_lab.ensemble import combine_opinions
from crypto_quant_lab.signals import Decision, Direction, SpecialistOpinion


def opinion(name: str, direction: Direction, score: float = 0.9) -> SpecialistOpinion:
    return SpecialistOpinion(name, datetime.now(timezone.utc), "BTC-USD", "1h", direction, score)


def test_insufficient_opinions_abstains() -> None:
    result = combine_opinions([opinion("trend", Direction.LONG)], min_specialists=3)
    assert result.decision is Decision.NO_TRADE


def test_clear_long_vote() -> None:
    result = combine_opinions([
        opinion("trend", Direction.LONG),
        opinion("momentum", Direction.LONG),
        opinion("funding", Direction.SHORT, 0.1),
    ], min_specialists=3, min_edge=0.15)
    assert result.decision is Decision.LONG


def test_mixed_symbols_are_rejected() -> None:
    a = opinion("trend", Direction.LONG)
    b = SpecialistOpinion("other", a.observed_at, "ETH-USD", "1h", Direction.LONG, 0.9)
    try:
        combine_opinions([a, b])
    except ValueError as exc:
        assert "same symbol" in str(exc)
    else:
        raise AssertionError("expected mismatched symbols to fail")
