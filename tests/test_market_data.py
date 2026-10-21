import pytest

from crypto_quant_lab.market_data import Candle, validate_candles


def candle(ts: int, close: float = 10.0) -> Candle:
    return Candle(ts, 9.0, max(11.0, close), min(8.0, close), close, 100.0)


def test_candles_are_sorted_chronologically() -> None:
    result = validate_candles([candle(200), candle(100)])
    assert [item.timestamp_ms for item in result] == [100, 200]


def test_duplicate_timestamps_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_candles([candle(100), candle(100)])


def test_invalid_ohlcv_is_rejected() -> None:
    with pytest.raises(ValueError, match="high"):
        Candle(100, 12, 11, 9, 10, 5)
