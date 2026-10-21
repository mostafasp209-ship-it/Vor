# Market data ingestion

The first adapter fetches public OHLCV candles through CCXT. It does not place orders and does not require exchange API keys for public market data.

Install the optional dependency:

```bash
python -m pip install -e '.[market-data,dev]'
```

Example:

```python
from crypto_quant_lab.market_data import CcxtMarketDataClient

client = CcxtMarketDataClient("binance")
try:
    candles = client.fetch_ohlcv(symbol="BTC/USDT", timeframe="1h", limit=200)
    print(f"Loaded {len(candles)} candles")
finally:
    client.close()
```

Timestamps are milliseconds since Unix epoch. Candles are sorted chronologically and duplicate timestamps are rejected. Always verify exchange symbol conventions, API limits, data gaps, and the status of the latest candle before using data in a backtest. The most recent candle may still be forming. No live-trading functionality is provided.
