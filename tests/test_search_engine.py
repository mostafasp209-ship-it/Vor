import numpy as np
import pandas as pd
import pytest
from crypto_quant.search_engine import Strategy, add_features, build_signal, candidate_grid, search_market, simulate, validate_market_data

def sample_market(n=1800):
    rng=np.random.default_rng(7); close=100*np.exp(np.cumsum(rng.normal(.00015,.003,n)))
    op=np.r_[close[0],close[:-1]]; spread=close*.002
    return pd.DataFrame({"open":op,"high":np.maximum(op,close)+spread,
      "low":np.minimum(op,close)-spread,"close":close,
      "volume":rng.lognormal(5,.25,n)},
      index=pd.date_range("2024-01-01",periods=n,freq="15min",tz="UTC"))

def test_validation_rejects_bad_ohlc():
    d=sample_market(40); d.iloc[0,d.columns.get_loc("high")]=1
    with pytest.raises(ValueError,match="High"): validate_market_data(d)

def test_grid_is_reproducible_and_unique():
    a=candidate_grid(80); assert a==candidate_grid(80); assert len(a)==80; assert len(set(a))==80

def test_signal_values_are_bounded():
    d=add_features(sample_market())
    p=Strategy("trend_pullback",13,55,45,55,20,.8,1.5,3.,48,20)
    assert set(np.unique(build_signal(d,p))).issubset({-1,0,1})

def test_entry_is_next_open_and_stop_precedes_target():
    idx=pd.date_range("2025-01-01",periods=205,freq="h",tz="UTC")
    c=np.full(205,100.)
    d=pd.DataFrame({"open":c,"high":c+.1,"low":c-.1,"close":c,"volume":np.full(205,1000.)},index=idx)
    d.loc[idx[201],["open","high","low","close"]]=[100,105,95,100]
    p=Strategy("breakout",13,55,45,55,0,0.,1.,3.,3,20)
    d["atr"]=1.0
    sig=np.zeros(205,dtype=np.int8); sig[200]=1
    trades=simulate(d,sig,p,start=0,end=205,fee_bps=0,slippage_bps=0)
    assert trades and trades[0]["entry_time"]==idx[201].isoformat()
    assert trades[0]["exit_reason"]=="stop" and trades[0]["net_r"]<0

def test_search_respects_time_splits():
    r=search_market(sample_market(),symbol="TESTUSDT",interval="15m",max_candidates=20,shortlist=5,min_trades=1)
    assert sum(r["splits"].values())==r["candles"]
    assert r["test_shortlist"]<=5
    assert all(isinstance(x["qualifies"],bool) for x in r["results"])


def test_time_exit_charges_entry_and_exit_costs():
    idx=pd.date_range("2025-01-01",periods=205,freq="h",tz="UTC")
    c=np.full(205,100.)
    d=pd.DataFrame({"open":c,"high":c+.01,"low":c-.01,"close":c,
                    "volume":np.full(205,1000.),"atr":np.full(205,1.)},index=idx)
    p=Strategy("breakout",13,55,45,55,0,0.,1.,3.,2,20)
    sig=np.zeros(205,dtype=np.int8); sig[200]=1
    free=simulate(d,sig,p,start=0,end=205,fee_bps=0,slippage_bps=0)
    charged=simulate(d,sig,p,start=0,end=205,fee_bps=5,slippage_bps=2)
    assert free[0]["exit_reason"]=="time"
    assert charged[0]["net_r"]<free[0]["net_r"]


def test_advanced_indicators_are_present():
    d=add_features(sample_market())
    required={"macd","stoch_k","bb_upper","cci","williams_r","mfi","obv",
              "cmf","vwap_24","donchian_high_50","keltner_upper",
              "ichimoku_span_a","supertrend_direction","psar","hma_13"}
    assert required.issubset(d.columns)


def test_expanded_indicators_are_finite_and_causal_columns_exist():
    d=add_features(sample_market(1800))
    required={"tsi","tsi_signal","ultimate_oscillator","dpo_20","kama_10",
              "aroon_up","aroon_down","choppiness_14","squeeze_on",
              "fisher_transform","fisher_signal","chaikin_oscillator",
              "donchian_mid_20","atr_percentile_100","confirmed_swing_high",
              "confirmed_swing_low"}
    assert required.issubset(d.columns)
    assert np.isfinite(d["fisher_transform"].dropna()).all()
    assert d["fisher_transform"].notna().sum()>100


def test_all_strategy_families_build_valid_signals():
    from crypto_quant.search_engine import candidate_grid
    d=add_features(sample_market(1800))
    for p in candidate_grid(500):
        signal=build_signal(d,p)
        assert len(signal)==len(d)
        assert set(np.unique(signal)).issubset({-1,0,1})


def test_evolutionary_search_uses_family_history():
    from crypto_quant.autonomous_search import FAMILIES, _population
    cold={family:{"tested":0,"qualified":0} for family in FAMILIES}
    hot={family:{"tested":1000,"qualified":0} for family in FAMILIES}
    hot["tsi_momentum"]={"tested":100,"qualified":70}
    a=_population([],120,123,cold)
    b=_population([],120,123,hot)
    assert len(a)==len(b)==120
    assert a!=b
    assert all(x.family in FAMILIES for x in b)
