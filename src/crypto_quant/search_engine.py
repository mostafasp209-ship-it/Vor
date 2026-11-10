"""Trade-level futures strategy discovery engine for Vor."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import product
import json, math, time, io, zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd
from crypto_quant.feature_library import add_advanced_features

BASE = "https://fapi.binance.com"
INTERVALS = {"1m":60000,"3m":180000,"5m":300000,"15m":900000,"30m":1800000,
 "1h":3600000,"2h":7200000,"4h":14400000,"6h":21600000,"8h":28800000,
 "12h":43200000,"1d":86400000}

@dataclass(frozen=True)
class Strategy:
    family:str; fast:int; slow:int; rsi_long:int; rsi_short:int; adx_min:int
    volume_min:float; atr_stop:float; target_r:float; max_hold:int; lookback:int

def _get(path, params):
    req=Request(f"{BASE}{path}?{urlencode(params)}",headers={"User-Agent":"Vor-Strategy-Research/1.0"})
    with urlopen(req,timeout=30) as response: return json.loads(response.read().decode())

def validate_market_data(frame):
    cols=["open","high","low","close","volume"]
    if set(cols)-set(frame.columns): raise ValueError(f"Missing OHLCV fields: {sorted(set(cols)-set(frame.columns))}")
    d=frame[cols].copy().sort_index()
    if d.empty or d.index.has_duplicates: raise ValueError("Market data is empty or has duplicate timestamps")
    d[cols]=d[cols].apply(pd.to_numeric,errors="coerce")
    if d[cols].isna().any().any(): raise ValueError("Market data contains missing values")
    if (d[["open","high","low","close"]]<=0).any().any() or (d.volume<0).any(): raise ValueError("Invalid price or volume")
    if (d.high<d[["open","low","close"]].max(axis=1)).any(): raise ValueError("High is inconsistent with OHLC")
    if (d.low>d[["open","high","close"]].min(axis=1)).any(): raise ValueError("Low is inconsistent with OHLC")
    return d

def _read_binance_archive(url):
    """Read one official Binance USD-M futures kline ZIP; return None when absent."""
    request=Request(url,headers={"User-Agent":"Vor-Strategy-Research/1.0"})
    try:
        with urlopen(request,timeout=60) as response:
            payload=response.read()
    except Exception as exc:
        from urllib.error import HTTPError
        if isinstance(exc,HTTPError) and exc.code==404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names=[name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"Archive has no CSV: {url}")
        raw=archive.read(csv_names[0])
    names=["open_time","open","high","low","close","volume","close_time",
           "quote_volume","trade_count","taker_buy_base","taker_buy_quote","ignore"]
    data=pd.read_csv(io.BytesIO(raw))
    normalized=[str(x).strip().lower() for x in data.columns]
    if "open_time" not in normalized:
        data=pd.read_csv(io.BytesIO(raw),header=None,names=names)
    else:
        data.columns=normalized
    required=names[:6]
    missing=set(required)-set(data.columns)
    if missing:
        raise RuntimeError(f"Archive missing columns {sorted(missing)}: {url}")
    data["open_time"]=pd.to_numeric(data["open_time"],errors="coerce")
    for col in ("open","high","low","close","volume"):
        data[col]=pd.to_numeric(data[col],errors="coerce")
    data=data.dropna(subset=["open_time","open","high","low","close","volume"])
    data["open_time"]=pd.to_datetime(data["open_time"],unit="ms",utc=True)
    return data.set_index("open_time")[["open","high","low","close","volume"]]


def fetch_futures_ohlcv(symbol,interval="15m",days=365,pause_seconds=.05):
    """Fetch USD-M candles from Binance's official daily/monthly public archive.

    Static archive downloads are used instead of the live REST endpoint because
    hosted CI runners may be geo-blocked by the exchange API.
    """
    if interval not in INTERVALS: raise ValueError(f"Unsupported interval: {interval}")
    if days<30: raise ValueError("days must be at least 30")
    symbol=symbol.upper()
    now=pd.Timestamp.now(tz="UTC")
    start=now-pd.Timedelta(days=days)
    complete_end=now.normalize()  # Daily archive is only expected through yesterday.
    if complete_end<=start:
        raise ValueError("No completed UTC day inside requested history")
    first_period=start.to_period("M")
    last_period=(complete_end-pd.Timedelta(nanoseconds=1)).to_period("M")
    chunks=[]
    period=first_period
    while period<=last_period:
        month_start=period.start_time.tz_localize("UTC")
        month_end=(period+1).start_time.tz_localize("UTC")
        is_current_archive_month=(period==last_period)
        if not is_current_archive_month:
            filename=f"{symbol}-{interval}-{period.year}-{period.month:02d}.zip"
            url=(f"https://data.binance.vision/data/futures/um/monthly/klines/"
                 f"{symbol}/{interval}/{filename}")
            chunk=_read_binance_archive(url)
            if chunk is not None:
                chunks.append(chunk)
            else:
                # Newly completed months can take time to appear in monthly storage.
                day=max(month_start,start.normalize())
                while day<month_end and day<complete_end:
                    date=day.strftime("%Y-%m-%d")
                    daily=f"{symbol}-{interval}-{date}.zip"
                    daily_url=(f"https://data.binance.vision/data/futures/um/daily/klines/"
                               f"{symbol}/{interval}/{daily}")
                    chunk=_read_binance_archive(daily_url)
                    if chunk is not None: chunks.append(chunk)
                    day+=pd.Timedelta(days=1)
                    time.sleep(max(0.0,pause_seconds))
        else:
            day=max(month_start,start.normalize())
            while day<month_end and day<complete_end:
                date=day.strftime("%Y-%m-%d")
                daily=f"{symbol}-{interval}-{date}.zip"
                daily_url=(f"https://data.binance.vision/data/futures/um/daily/klines/"
                           f"{symbol}/{interval}/{daily}")
                chunk=_read_binance_archive(daily_url)
                if chunk is not None: chunks.append(chunk)
                day+=pd.Timedelta(days=1)
                time.sleep(max(0.0,pause_seconds))
        period+=1
        time.sleep(max(0.0,pause_seconds))
    if not chunks:
        raise RuntimeError(f"No Binance USD-M archive candles returned for {symbol} {interval}")
    data=pd.concat(chunks).sort_index()
    data=data[~data.index.duplicated(keep="last")]
    data=data.loc[(data.index>=start)&(data.index<complete_end)]
    return validate_market_data(data)

def add_features(frame):
    d=validate_market_data(frame); c,h,l,v=d.close,d.high,d.low,d.volume
    for n in (8,13,21,34,55,89,144,200): d[f"ema_{n}"]=c.ewm(span=n,adjust=False).mean()
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rs=gain/loss.replace(0,np.nan); d["rsi"]=100-100/(1+rs)
    prev=c.shift(1); tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    d["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
    up,down=h.diff(),-l.diff()
    pdm=up.where((up>down)&(up>0),0.); mdm=down.where((down>up)&(down>0),0.)
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/d.atr
    mdi=100*mdm.ewm(alpha=1/14,adjust=False).mean()/d.atr
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    d["adx"]=dx.ewm(alpha=1/14,adjust=False).mean(); d["plus_di"]=pdi; d["minus_di"]=mdi
    d["volume_ratio"]=v/v.rolling(20).mean().shift(1)
    for n in (20,50):
        d[f"prior_high_{n}"]=h.shift(1).rolling(n).max()
        d[f"prior_low_{n}"]=l.shift(1).rolling(n).min()
    d["return_4"]=c.pct_change(4); d["range_atr"]=(h-l)/d.atr
    d=d.replace([np.inf,-np.inf],np.nan)
    return add_advanced_features(d)

def build_signal(d,p):
    c=d.close; fast=d[f"ema_{p.fast}"]; slow=d[f"ema_{p.slow}"]
    up,down=fast>slow,fast<slow; liquid=d.volume_ratio>=p.volume_min; strong=d.adx>=p.adx_min
    if p.family=="trend_pullback":
        long=up&(c>slow)&(d.rsi>p.rsi_long)&(d.rsi.shift(1)<=p.rsi_long)&strong&liquid
        short=down&(c<slow)&(d.rsi<p.rsi_short)&(d.rsi.shift(1)>=p.rsi_short)&strong&liquid
    elif p.family=="breakout":
        long=(c>d[f"prior_high_{p.lookback}"])&up&strong&liquid
        short=(c<d[f"prior_low_{p.lookback}"])&down&strong&liquid
    elif p.family=="mean_reversion":
        long=(d.rsi.shift(1)<30)&(d.rsi>=30)&(c>d.ema_55)&liquid
        short=(d.rsi.shift(1)>70)&(d.rsi<=70)&(c<d.ema_55)&liquid
    elif p.family=="directional_momentum":
        long=up&(d.return_4>0)&strong&(d.plus_di>d.minus_di)&liquid
        short=down&(d.return_4<0)&strong&(d.minus_di>d.plus_di)&liquid
    elif p.family=="range_expansion":
        body=(d.close-d.open).abs()
        long=(d.close>d.open)&(body/d.atr>.8)&(d.range_atr>1.2)&up&liquid
        short=(d.close<d.open)&(body/d.atr>.8)&(d.range_atr>1.2)&down&liquid
    elif p.family=="macd_cross":
        long=(d.macd>d.macd_signal)&(d.macd.shift(1)<=d.macd_signal.shift(1))&up&strong
        short=(d.macd<d.macd_signal)&(d.macd.shift(1)>=d.macd_signal.shift(1))&down&strong
    elif p.family=="stochastic_reversal":
        long=(d.stoch_k>d.stoch_d)&(d.stoch_k.shift(1)<=d.stoch_d.shift(1))&(d.stoch_k<35)&(d.rsi>p.rsi_long)&up
        short=(d.stoch_k<d.stoch_d)&(d.stoch_k.shift(1)>=d.stoch_d.shift(1))&(d.stoch_k>65)&(d.rsi<p.rsi_short)&down
    elif p.family=="bollinger_reversion":
        long=(d.bb_pct<.15)&(d.bb_pct.shift(1)>=.15)&(d.rsi<40)&(d.close>d.ema_55)
        short=(d.bb_pct>.85)&(d.bb_pct.shift(1)<=.85)&(d.rsi>60)&(d.close<d.ema_55)
    elif p.family=="bollinger_breakout":
        long=(d.close>d.bb_upper)&(d.bb_width>d.bb_width.rolling(20).median())&up&liquid
        short=(d.close<d.bb_lower)&(d.bb_width>d.bb_width.rolling(20).median())&down&liquid
    elif p.family=="donchian_breakout":
        long=(d.close>d[f"donchian_high_{p.lookback}"])&up&liquid
        short=(d.close<d[f"donchian_low_{p.lookback}"])&down&liquid
    elif p.family=="vwap_reclaim":
        long=(d.close>d.vwap_24)&(d.close.shift(1)<=d.vwap_24.shift(1))&up&(d.obv_slope>0)
        short=(d.close<d.vwap_24)&(d.close.shift(1)>=d.vwap_24.shift(1))&down&(d.obv_slope<0)
    elif p.family=="ichimoku_trend":
        cloud_top=d[["ichimoku_span_a","ichimoku_span_b"]].max(axis=1)
        cloud_bottom=d[["ichimoku_span_a","ichimoku_span_b"]].min(axis=1)
        long=(d.close>cloud_top)&(d.ichimoku_tenkan>d.ichimoku_kijun)&(d.close>d.ichimoku_kijun)&liquid
        short=(d.close<cloud_bottom)&(d.ichimoku_tenkan<d.ichimoku_kijun)&(d.close<d.ichimoku_kijun)&liquid
    elif p.family=="supertrend_follow":
        long=(d.supertrend_direction>0)&(d.supertrend_direction.shift(1)<0)&(d.close>d.ema_55)
        short=(d.supertrend_direction<0)&(d.supertrend_direction.shift(1)>0)&(d.close<d.ema_55)
    elif p.family=="cci_reversal":
        long=(d.cci.shift(1)<-100)&(d.cci>=-100)&(d.close>d.ema_55)
        short=(d.cci.shift(1)>100)&(d.cci<=100)&(d.close<d.ema_55)
    elif p.family=="mfi_flow":
        long=(d.mfi>50)&(d.mfi.shift(1)<=50)&(d.cmf>0)&up
        short=(d.mfi<50)&(d.mfi.shift(1)>=50)&(d.cmf<0)&down
    elif p.family=="psar_trend":
        long=(d.close>d.psar)&(d.close.shift(1)<=d.psar.shift(1))&up
        short=(d.close<d.psar)&(d.close.shift(1)>=d.psar.shift(1))&down
    elif p.family=="hma_momentum":
        hma=d[f"hma_{p.fast}"]
        long=(hma>hma.shift(1))&(d.close>hma)&(d.roc_10>0)&(d.adx>=p.adx_min)
        short=(hma<hma.shift(1))&(d.close<hma)&(d.roc_10<0)&(d.adx>=p.adx_min)
    elif p.family=="candle_structure":
        long=((d.bullish_engulfing>0)|(d.bullish_pinbar>0))&up&(d.close>d.vwap_24)&liquid
        short=((d.bearish_engulfing>0)|(d.bearish_pinbar>0))&down&(d.close<d.vwap_24)&liquid
    else: raise ValueError(f"Unknown family: {p.family}")
    out=np.zeros(len(d),dtype=np.int8); out[np.asarray(long.fillna(False))]=1
    out[np.asarray(short.fillna(False))]=-1
    return out

def _metrics(trades):
    r=np.asarray([x["net_r"] for x in trades],dtype=float); wins=r[r>0]; losses=r[r<0]
    gp=float(wins.sum()); gl=float(-losses.sum()); eq=np.cumsum(r)
    peak=np.maximum.accumulate(np.r_[0.,eq]); dd=peak[1:]-eq if len(eq) else np.array([])
    return {"trades":int(len(r)),"win_rate":round(float((r>0).mean()*100),2) if len(r) else 0.,
      "avg_win_r":round(float(wins.mean()),3) if len(wins) else 0.,
      "avg_loss_r":round(float(-losses.mean()),3) if len(losses) else 0.,
      "realized_rr":round(float(wins.mean()/-losses.mean()),3) if len(wins) and len(losses) else 0.,
      "expectancy_r":round(float(r.mean()),4) if len(r) else 0.,
      "total_r":round(float(r.sum()),2),
      "profit_factor":round(gp/gl,3) if gl else (99. if gp else 0.),
      "max_drawdown_r":round(float(dd.max()),2) if len(dd) else 0.}

def simulate(d,signal,p,*,start,end,fee_bps,slippage_bps):
    """Next-open execution; skip flat bars efficiently; charge both sides on every exit."""
    trades=[]; cost=(fee_bps+slippage_bps)/10000
    first=max(start,200)
    candidates=np.flatnonzero(np.asarray(signal[first:max(first,end-1)])!=0)+first
    cursor=0
    while cursor<len(candidates):
        i=int(candidates[cursor]); side=int(signal[i])
        atr=float(d.atr.iloc[i]) if pd.notna(d.atr.iloc[i]) else np.nan
        if not np.isfinite(atr) or atr<=0:
            cursor+=1; continue
        ei=i+1; raw=float(d.open.iloc[ei]); entry=raw*(1+cost*side); risk=atr*p.atr_stop
        if risk/entry<.0003 or risk/entry>.04:
            cursor+=1; continue
        stop=entry-side*risk; target=entry+side*p.target_r*risk
        last=min(end-1,ei+p.max_hold-1); exit_price=float(d.close.iloc[last]); reason="time"; xi=last
        for j in range(ei,last+1):
            op,hi,lo=float(d.open.iloc[j]),float(d.high.iloc[j]),float(d.low.iloc[j])
            stop_hit=lo<=stop if side>0 else hi>=stop
            target_hit=hi>=target if side>0 else lo<=target
            if stop_hit:
                raw_exit=min(op,stop) if side>0 else max(op,stop)
                exit_price=raw_exit*(1-cost*side); reason="stop"; xi=j; break
            if target_hit:
                raw_exit=max(op,target) if side>0 else min(op,target)
                exit_price=raw_exit*(1-cost*side); reason="target"; xi=j; break
        if reason=="time":
            exit_price=exit_price*(1-cost*side)
        net_r=side*(exit_price-entry)/risk
        trades.append({"signal_time":d.index[i].isoformat(),"entry_time":d.index[ei].isoformat(),
          "exit_time":d.index[xi].isoformat(),"side":"LONG" if side>0 else "SHORT",
          "entry":entry,"exit":exit_price,"stop":stop,"target":target,
          "exit_reason":reason,"net_r":float(net_r)})
        cursor=int(np.searchsorted(candidates,xi+1,side="left"))
    return trades

def candidate_grid(max_candidates=300,seed=20261110):
    """Sample unique candidates without materializing a multi-million-row Cartesian product."""
    families=("trend_pullback","breakout","mean_reversion","directional_momentum","range_expansion",
      "macd_cross","stochastic_reversal","bollinger_reversion","bollinger_breakout",
      "donchian_breakout","vwap_reclaim","ichimoku_trend","supertrend_follow",
      "cci_reversal","mfi_flow","psar_trend","hma_momentum","candle_structure")
    fast_values=(8,13,21,34); slow_values=(55,89,144,200)
    rsi_long_values=(40,45,50); rsi_short_values=(50,55,60)
    adx_values=(0,15,20,25); volume_values=(0.0,.7,1.0,1.2)
    stop_values=(1.0,1.5,2.0); target_values=(3.0,3.5,4.0,4.5)
    hold_values=(24,48,96); lookback_values=(20,50)
    rng=np.random.default_rng(seed); results=[]; seen=set()
    max_attempts=max_candidates*30
    for _ in range(max_attempts):
        fast=int(rng.choice(fast_values)); slow=int(rng.choice([x for x in slow_values if x>fast]))
        p=Strategy(str(rng.choice(families)),fast,slow,
          int(rng.choice(rsi_long_values)),int(rng.choice(rsi_short_values)),
          int(rng.choice(adx_values)),float(rng.choice(volume_values)),
          float(rng.choice(stop_values)),float(rng.choice(target_values)),
          int(rng.choice(hold_values)),int(rng.choice(lookback_values)))
        key=tuple(asdict(p).values())
        if key not in seen:
            seen.add(key); results.append(p)
            if len(results)>=max_candidates: break
    if len(results)<max_candidates:
        raise RuntimeError(f"Only generated {len(results)} unique candidates; requested {max_candidates}")
    return results

def _score(train,val):
    if not train["trades"] or not val["trades"]: return -1e9
    return min(train["expectancy_r"],val["expectancy_r"])*math.log1p(min(train["trades"],val["trades"]))

def search_market(frame,*,symbol,interval,max_candidates=300,shortlist=25,min_trades=30,
                  min_win_rate=70.,min_realized_rr=3.,fee_bps=5.,slippage_bps=2.):
    if not 0<min_win_rate<=100 or min_realized_rr<=0 or min_trades<1: raise ValueError("Invalid acceptance thresholds")
    d=add_features(frame); n=len(d); train_end=int(n*.56); val_end=int(n*.70)
    if train_end<250 or val_end-train_end<100 or n-val_end<100:
        raise ValueError("Insufficient data for 56/14/30 chronological splits")
    ranked=[]
    for p in candidate_grid(max_candidates):
        sig=build_signal(d,p)
        tr=_metrics(simulate(d,sig,p,start=0,end=train_end,fee_bps=fee_bps,slippage_bps=slippage_bps))
        va=_metrics(simulate(d,sig,p,start=train_end,end=val_end,fee_bps=fee_bps,slippage_bps=slippage_bps))
        ranked.append({"strategy":asdict(p),"train":tr,"validation":va,"score":_score(tr,va)})
    ranked.sort(key=lambda x:x["score"],reverse=True); finalists=ranked[:min(shortlist,len(ranked))]
    results=[]
    for item in finalists:
        p=Strategy(**item["strategy"]); sig=build_signal(d,p)
        test=_metrics(simulate(d,sig,p,start=val_end,end=n,fee_bps=fee_bps,slippage_bps=slippage_bps))
        val=item["validation"]
        passed=all((val["trades"]>=min_trades,test["trades"]>=min_trades,
          val["win_rate"]>=min_win_rate,test["win_rate"]>=min_win_rate,
          val["realized_rr"]>=min_realized_rr,test["realized_rr"]>=min_realized_rr,
          val["expectancy_r"]>0,test["expectancy_r"]>0))
        results.append({**item,"test":test,"qualifies":bool(passed)})
    results.sort(key=lambda x:(x["qualifies"],x["score"],x["test"]["expectancy_r"]),reverse=True)
    return {"symbol":symbol,"interval":interval,"candles":n,
      "splits":{"train":train_end,"validation":val_end-train_end,"test":n-val_end},
      "search_candidates":len(ranked),"test_shortlist":len(finalists),
      "thresholds":{"min_trades_each_validation_test":min_trades,"win_rate_pct":min_win_rate,"realized_rr":min_realized_rr},
      "qualified_count":sum(x["qualifies"] for x in results),"results":results,
      "warning":"Research only: funding, dynamic spread, market impact, liquidation and partial fills are not modeled."}

def run_search(symbols,intervals,days=365,max_candidates=300,shortlist=25,min_trades=30,
               fee_bps=5.,slippage_bps=2.,output_dir="artifacts/strategy_search"):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); reports=[]
    for interval in intervals:
        for symbol in symbols:
            print(f"Fetching {symbol} {interval} ({days} days)",flush=True)
            frame=fetch_futures_ohlcv(symbol,interval,days)
            report=search_market(frame,symbol=symbol,interval=interval,max_candidates=max_candidates,
              shortlist=shortlist,min_trades=min_trades,fee_bps=fee_bps,slippage_bps=slippage_bps)
            reports.append(report)
            (out/f"{symbol}_{interval}_report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
            print(f"{symbol} {interval}: {report['qualified_count']} passed / {report['test_shortlist']} tested",flush=True)
    summary={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"days":days,"reports":reports}
    (out/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8")
    return reports
