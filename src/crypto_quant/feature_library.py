"""Causal technical-feature library used by Vor's research engine.

All features are computed from the current and past OHLCV bars only. Signal
generation happens after bar close; execution must be on a later bar.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def add_advanced_features(frame: pd.DataFrame) -> pd.DataFrame:
    d=frame.copy()
    o,h,l,c,v=(d[x].astype(float) for x in ("open","high","low","close","volume"))
    for n in (10,20,50,100,200):
        d[f"sma_{n}"]=c.rolling(n).mean()
    def wma(s,n):
        weights=np.arange(1,n+1,dtype=float)
        return s.rolling(n).apply(lambda x: float(np.dot(x,weights)/weights.sum()),raw=True)
    for n in (9,16,21,34):
        d[f"wma_{n}"]=wma(c,n)
    for n in (16,21,34):
        half=max(2,n//2); root=max(2,int(np.sqrt(n)))
        d[f"hma_{n}"]=wma(2*wma(c,half)-wma(c,n),root)

    ema12=c.ewm(span=12,adjust=False).mean()
    ema26=c.ewm(span=26,adjust=False).mean()
    d["macd"]=ema12-ema26
    d["macd_signal"]=d.macd.ewm(span=9,adjust=False).mean()
    d["macd_hist"]=d.macd-d.macd_signal

    low14=l.rolling(14).min(); high14=h.rolling(14).max()
    d["stoch_k"]=100*(c-low14)/(high14-low14).replace(0,np.nan)
    d["stoch_d"]=d.stoch_k.rolling(3).mean()
    d["stoch_rsi"]=100*(d.rsi-d.rsi.rolling(14).min())/(d.rsi.rolling(14).max()-d.rsi.rolling(14).min()).replace(0,np.nan)

    mid=c.rolling(20).mean(); sd=c.rolling(20).std(ddof=0)
    d["bb_mid"]=mid; d["bb_upper"]=mid+2*sd; d["bb_lower"]=mid-2*sd
    d["bb_width"]=(4*sd/mid.replace(0,np.nan))
    d["bb_pct"]=(c-d.bb_lower)/(d.bb_upper-d.bb_lower).replace(0,np.nan)

    tp=(h+l+c)/3
    tp_sma=tp.rolling(20).mean()
    mad=tp.rolling(20).apply(lambda x: float(np.mean(np.abs(x-np.mean(x)))),raw=True)
    d["cci"]=(tp-tp_sma)/(0.015*mad).replace(0,np.nan)
    d["williams_r"]=-100*(high14-c)/(high14-low14).replace(0,np.nan)
    d["roc_10"]=c.pct_change(10)*100
    d["roc_20"]=c.pct_change(20)*100

    direction=np.sign(c.diff()).fillna(0)
    raw_money=tp*v
    pos=raw_money.where(tp.diff()>0,0.0).rolling(14).sum()
    neg=raw_money.where(tp.diff()<0,0.0).rolling(14).sum()
    ratio=pos/neg.replace(0,np.nan)
    d["mfi"]=100-100/(1+ratio)
    d["obv"]=(direction*v).cumsum()
    d["obv_slope"]=d.obv.pct_change(10).replace([np.inf,-np.inf],np.nan)
    mf_mult=((c-l)-(h-c))/(h-l).replace(0,np.nan)
    d["cmf"]=(mf_mult*v).rolling(20).sum()/v.rolling(20).sum().replace(0,np.nan)

    # Rolling VWAP avoids session/timezone assumptions and remains causal.
    d["vwap_24"]=(tp*v).rolling(24).sum()/v.rolling(24).sum().replace(0,np.nan)
    d["vwap_96"]=(tp*v).rolling(96).sum()/v.rolling(96).sum().replace(0,np.nan)
    for n in (10,20,40,55):
        d[f"donchian_high_{n}"]=h.shift(1).rolling(n).max()
        d[f"donchian_low_{n}"]=l.shift(1).rolling(n).min()

    # Keltner channel; ATR is supplied by the base feature builder.
    d["keltner_mid"]=c.ewm(span=20,adjust=False).mean()
    d["keltner_upper"]=d.keltner_mid+2*d.atr
    d["keltner_lower"]=d.keltner_mid-2*d.atr

    # Ichimoku lines. Leading spans are shifted forward, so current cloud
    # values are read from the values actually known at this timestamp.
    tenkan=(h.rolling(9).max()+l.rolling(9).min())/2
    kijun=(h.rolling(26).max()+l.rolling(26).min())/2
    span_a=((tenkan+kijun)/2).shift(26)
    span_b=((h.rolling(52).max()+l.rolling(52).min())/2).shift(26)
    d["ichimoku_tenkan"]=tenkan; d["ichimoku_kijun"]=kijun
    d["ichimoku_span_a"]=span_a; d["ichimoku_span_b"]=span_b

    # Supertrend: final bands and direction are updated sequentially.
    atr=d.atr.to_numpy(); high=h.to_numpy(); low=l.to_numpy(); close=c.to_numpy()
    basic_mid=(high+low)/2
    upper=basic_mid+3*atr; lower=basic_mid-3*atr
    final_u=np.full(len(d),np.nan); final_l=np.full(len(d),np.nan)
    trend=np.ones(len(d),dtype=np.int8)
    for i in range(len(d)):
        if not np.isfinite(atr[i]): continue
        if i==0 or not np.isfinite(final_u[i-1]):
            final_u[i]=upper[i]; final_l[i]=lower[i]; continue
        final_u[i]=upper[i] if upper[i]<final_u[i-1] or close[i-1]>final_u[i-1] else final_u[i-1]
        final_l[i]=lower[i] if lower[i]>final_l[i-1] or close[i-1]<final_l[i-1] else final_l[i-1]
        trend[i]=trend[i-1]
        if trend[i-1]<0 and close[i]>final_u[i-1]: trend[i]=1
        elif trend[i-1]>0 and close[i]<final_l[i-1]: trend[i]=-1
    d["supertrend_direction"]=trend
    d["supertrend_line"]=np.where(trend>0,final_l,final_u)

    # Parabolic SAR with standard acceleration limits.
    psar=np.full(len(d),np.nan); bull=True; af=.02; af_max=.2; ep=np.nan
    for i in range(1,len(d)):
        if i==1:
            bull=close[i]>=close[i-1]; psar[i]=low[i-1] if bull else high[i-1]
            ep=high[i] if bull else low[i]; continue
        prev=psar[i-1]
        if not np.isfinite(prev): continue
        candidate=prev+af*(ep-prev)
        if bull:
            candidate=min(candidate,low[i-1],low[i-2])
            if low[i]<candidate:
                bull=False; candidate=ep; ep=low[i]; af=.02
            elif high[i]>ep: ep=high[i]; af=min(af+.02,af_max)
        else:
            candidate=max(candidate,high[i-1],high[i-2])
            if high[i]>candidate:
                bull=True; candidate=ep; ep=high[i]; af=.02
            elif low[i]<ep: ep=low[i]; af=min(af+.02,af_max)
        psar[i]=candidate
    d["psar"]=psar

    # Candle anatomy and simple, transparent pattern flags.
    body=(c-o).abs(); span=(h-l).replace(0,np.nan)
    upper_wick=h-np.maximum(o,c); lower_wick=np.minimum(o,c)-l
    d["body_atr"]=body/d.atr.replace(0,np.nan)
    d["upper_wick_ratio"]=upper_wick/span
    d["lower_wick_ratio"]=lower_wick/span
    prev_o=o.shift(1); prev_c=c.shift(1)
    d["bullish_engulfing"]=((c>o)&(prev_c<prev_o)&(o<=prev_c)&(c>=prev_o)).astype(int)
    d["bearish_engulfing"]=((c<o)&(prev_c>prev_o)&(o>=prev_c)&(c<=prev_o)).astype(int)
    d["bullish_pinbar"]=((lower_wick/span>.60)&(body/span<.30)).astype(int)
    d["bearish_pinbar"]=((upper_wick/span>.60)&(body/span<.30)).astype(int)

    # Volatility and regime descriptors for regime-aware filters.
    d["realized_vol_20"]=c.pct_change().rolling(20).std()
    d["atr_pct"]=d.atr/c
    d["volume_zscore"]=(v-v.rolling(50).mean())/v.rolling(50).std().replace(0,np.nan)
    d["trend_strength"]=(d.ema_21-d.ema_55).abs()/d.atr.replace(0,np.nan)
    d["range_position_50"]=(c-d.donchian_low_50)/(d.donchian_high_50-d.donchian_low_50).replace(0,np.nan)
    return d.replace([np.inf,-np.inf],np.nan)
