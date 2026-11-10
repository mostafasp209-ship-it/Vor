"""Persistent, adaptive, walk-forward research loop for Vor.

This is an optimizer, not an LLM or an unconstrained agent. It learns operationally
from prior generations by retaining elite candidates, mutating their parameters,
tracking failure modes, and preserving a resumable checkpoint.
"""
from __future__ import annotations
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json, math, random, time
from pathlib import Path
from typing import Any

import numpy as np

from crypto_quant.search_engine import (
    Strategy, _metrics, add_features, build_signal, candidate_grid,
    fetch_futures_ohlcv, simulate,
)

FAMILIES = (
    "trend_pullback","breakout","mean_reversion","directional_momentum","range_expansion",
    "macd_cross","stochastic_reversal","bollinger_reversion","bollinger_breakout",
    "donchian_breakout","vwap_reclaim","ichimoku_trend","supertrend_follow",
    "cci_reversal","mfi_flow","psar_trend","hma_momentum","candle_structure",
)
FAST=(8,13,21,34); SLOW=(55,89,144,200)
RSI_LONG=(35,40,45,50,55); RSI_SHORT=(45,50,55,60,65)
ADX=(0,12,15,20,25,30); VOLUME=(0.0,.7,.9,1.0,1.2,1.5)
STOPS=(.8,1.0,1.2,1.5,1.8,2.0,2.5)
TARGETS=(3.0,3.5,4.0,4.5,5.0)
HOLDS=(12,24,48,72,96,144); LOOKBACKS=(20,50)


def _strategy_key(p: Strategy) -> tuple:
    return tuple(asdict(p).values())


def _mutate(parent: Strategy, rng: random.Random) -> Strategy:
    values=asdict(parent)
    fields=list(values)
    changes=rng.sample(fields,k=rng.choice((1,1,2,2,3)))
    for field in changes:
        if field=="family": values[field]=rng.choice(FAMILIES)
        elif field=="fast": values[field]=rng.choice(FAST)
        elif field=="slow": values[field]=rng.choice(SLOW)
        elif field=="rsi_long": values[field]=rng.choice(RSI_LONG)
        elif field=="rsi_short": values[field]=rng.choice(RSI_SHORT)
        elif field=="adx_min": values[field]=rng.choice(ADX)
        elif field=="volume_min": values[field]=rng.choice(VOLUME)
        elif field=="atr_stop": values[field]=rng.choice(STOPS)
        elif field=="target_r": values[field]=rng.choice(TARGETS)
        elif field=="max_hold": values[field]=rng.choice(HOLDS)
        elif field=="lookback": values[field]=rng.choice(LOOKBACKS)
    if values["fast"]>=values["slow"]:
        values["slow"]=next(x for x in SLOW if x>values["fast"])
    return Strategy(**values)


def _population(elites: list[dict[str,Any]], count: int, seed: int) -> list[Strategy]:
    rng=random.Random(seed)
    fresh=candidate_grid(max_candidates=count,seed=seed)
    pool=list(fresh[:max(1,count//3)])
    elite_objects=[Strategy(**x["strategy"]) for x in elites[:30]]
    if elite_objects:
        while len(pool)<count:
            parent=rng.choice(elite_objects)
            pool.append(_mutate(parent,rng))
    seen=set(); unique=[]
    for p in pool:
        key=_strategy_key(p)
        if key not in seen:
            seen.add(key); unique.append(p)
    while len(unique)<count:
        p=candidate_grid(max_candidates=1,seed=seed+len(unique)+rng.randrange(1_000_000))[0]
        if _strategy_key(p) not in seen:
            seen.add(_strategy_key(p)); unique.append(p)
    return unique[:count]


def _folds(n: int, fold_count: int=4) -> list[tuple[int,int]]:
    # Four non-overlapping forward windows. Initial bars are indicator warm-up.
    left=int(n*.30); right=int(n*.90); width=(right-left)//fold_count
    result=[]
    for i in range(fold_count):
        start=left+i*width
        end=right if i==fold_count-1 else left+(i+1)*width
        result.append((start,end))
    return result


def _wilson_lower(wins: int, n: int, z: float=1.96) -> float:
    if n<=0: return 0.0
    p=wins/n; den=1+z*z/n
    center=p+z*z/(2*n)
    margin=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)
    return max(0.0,(center-margin)/den)*100


def _evaluate(p: Strategy, datasets: list[dict[str,Any]], *, fee_bps: float,
              slippage_bps: float) -> dict[str,Any]:
    all_trades=[]; market_stats=[]; fold_stats=[]
    for item in datasets:
        d=item["data"]; signal=build_signal(d,p)
        market_trades=[]
        local_folds=[]
        for start,end in item["folds"]:
            trades=simulate(d,signal,p,start=start,end=end,
                            fee_bps=fee_bps,slippage_bps=slippage_bps)
            market_trades.extend(trades); all_trades.extend(trades)
            local_folds.extend(trades)
            fold_stats.append({"market":item["key"],**_metrics(trades)})
        market_stats.append({"market":item["key"],**_metrics(market_trades)})
    overall=_metrics(all_trades)
    positive_markets=sum(x["expectancy_r"]>0 for x in market_stats)
    positive_folds=sum(x["expectancy_r"]>0 for x in fold_stats)
    total_folds=len(fold_stats)
    wins=sum(1 for x in all_trades if x["net_r"]>0)
    overall["wilson_win_rate_lower_95"]=round(_wilson_lower(wins,len(all_trades)),2)
    score=(min((x["expectancy_r"] for x in fold_stats),default=-1.0)
           *math.log1p(overall["trades"])
           +.05*overall["profit_factor"]
           -.02*overall["max_drawdown_r"])
    return {"overall":overall,"markets":market_stats,"folds":fold_stats,
            "positive_markets":positive_markets,"market_count":len(market_stats),
            "positive_folds":positive_folds,"fold_count":total_folds,"score":score}


def _failure_reasons(result: dict[str,Any], *, min_trades: int,
                     min_trades_per_market: int, min_win_rate: float, min_rr: float,
                     min_positive_market_fraction: float) -> list[str]:
    m=result["overall"]; reasons=[]
    if m["trades"]<min_trades: reasons.append("insufficient_trade_frequency")
    if any(x["trades"]<min_trades_per_market for x in result["markets"]):
        reasons.append("insufficient_market_coverage")
    if m["win_rate"]<min_win_rate: reasons.append("win_rate_below_target")
    if m["realized_rr"]<min_rr: reasons.append("realized_rr_below_target")
    if m["expectancy_r"]<=0: reasons.append("non_positive_expectancy")
    if m["wilson_win_rate_lower_95"]<50: reasons.append("weak_win_rate_confidence")
    if result["positive_folds"]<math.ceil(result["fold_count"]*.75):
        reasons.append("walk_forward_instability")
    if result["positive_markets"]/max(1,result["market_count"])<min_positive_market_fraction:
        reasons.append("cross_market_instability")
    return reasons


def run_autonomous(symbols: list[str], intervals: list[str], days: int=365,
                   candidates_per_generation: int=250, min_trades: int=200,
                   min_trades_per_market: int=10, min_win_rate: float=70., min_realized_rr: float=3.,
                   min_positive_market_fraction: float=.75, fee_bps: float=5.,
                   slippage_bps: float=2., max_hours: float=5.2,
                   output_dir: str=".research_state", seed: int=20261110) -> dict[str,Any]:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    state_path=out/"checkpoint.json"; ledger_path=out/"experiment_ledger.jsonl"
    if state_path.exists():
        state=json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state={"status":"SEARCHING","generation":0,"seed":seed,"elites":[],
               "best":None,"evaluated":0,"failure_counts":{},"family_stats":{},
               "started_at_utc":datetime.now(timezone.utc).isoformat()}
    if state.get("status")=="FOUND":
        return state

    datasets=[]
    for symbol in symbols:
        for interval in intervals:
            key=f"{symbol.upper()}_{interval}"
            print(f"Loading {key} {days}d Binance USD-M candles",flush=True)
            raw=fetch_futures_ohlcv(symbol,interval,days)
            featured=add_features(raw)
            datasets.append({"key":key,"data":featured,"folds":_folds(len(featured))})
    if not datasets: raise ValueError("No datasets supplied")
    started=time.monotonic(); generation_results=[]
    while time.monotonic()-started < max_hours*3600:
        gen=int(state["generation"])+1; gen_seed=int(state["seed"])+gen*7919
        population=_population(state.get("elites",[]),candidates_per_generation,gen_seed)
        evaluated=[]
        for idx,p in enumerate(population,1):
            result=_evaluate(p,datasets,fee_bps=fee_bps,slippage_bps=slippage_bps)
            reasons=_failure_reasons(result,min_trades=min_trades,
              min_trades_per_market=min_trades_per_market,min_win_rate=min_win_rate,
              min_rr=min_realized_rr,min_positive_market_fraction=min_positive_market_fraction)
            row={"strategy":asdict(p),**result,"qualified":not reasons,"failure_reasons":reasons}
            evaluated.append(row); state["evaluated"]=int(state.get("evaluated",0))+1
            family_stat=state.setdefault("family_stats",{}).setdefault(p.family,
              {"tested":0,"qualified":0,"best_score":None,"failure_counts":{}})
            family_stat["tested"]+=1
            if not reasons: family_stat["qualified"]+=1
            if family_stat["best_score"] is None or result["score"]>family_stat["best_score"]:
                family_stat["best_score"]=result["score"]
            for reason in reasons:
                state["failure_counts"][reason]=int(state["failure_counts"].get(reason,0))+1
                family_stat["failure_counts"][reason]=int(family_stat["failure_counts"].get(reason,0))+1
            if not reasons:
                state.update({"status":"FOUND","winner":row,"generation":gen,
                  "found_at_utc":datetime.now(timezone.utc).isoformat()})
                break
            if idx%50==0:
                print(f"generation {gen}: {idx}/{len(population)} candidates",flush=True)
            if time.monotonic()-started >= max_hours*3600:
                break
        evaluated.sort(key=lambda x:(x["qualified"],x["score"],x["overall"]["expectancy_r"]),reverse=True)
        combined=(state.get("elites",[])+evaluated)
        combined.sort(key=lambda x:(x.get("qualified",False),x["score"],x["overall"]["expectancy_r"]),reverse=True)
        dedup=[]; seen=set()
        for row in combined:
            key=tuple(row["strategy"].values())
            if key not in seen:
                seen.add(key); dedup.append(row)
            if len(dedup)>=40: break
        state["elites"]=dedup
        state["generation"]=gen; state["seed"]=gen_seed
        best=dedup[0] if dedup else None
        if best: state["best"]=best
        gen_summary={"generation":gen,"candidates":len(evaluated),
          "qualified":sum(x["qualified"] for x in evaluated),
          "best_score":best["score"] if best else None,
          "best_metrics":best["overall"] if best else None,
          "top_candidates":[{"strategy":x["strategy"],"score":x["score"],
             "metrics":x["overall"],"failure_reasons":x["failure_reasons"]}
             for x in evaluated[:5]],
          "elapsed_seconds":round(time.monotonic()-started,1)}
        generation_results.append(gen_summary)
        with ledger_path.open("a",encoding="utf-8") as fp:
            fp.write(json.dumps(gen_summary,allow_nan=False)+"\n")
        state["last_generation"]=gen_summary
        state["updated_at_utc"]=datetime.now(timezone.utc).isoformat()
        state_path.write_text(json.dumps(state,indent=2,allow_nan=False),encoding="utf-8")
        print(json.dumps(gen_summary,ensure_ascii=False),flush=True)
        if state.get("status")=="FOUND": break
    state["status"]="FOUND" if state.get("winner") else "SEARCHING"
    state["last_run_seconds"]=round(time.monotonic()-started,1)
    state["updated_at_utc"]=datetime.now(timezone.utc).isoformat()
    state_path.write_text(json.dumps(state,indent=2,allow_nan=False),encoding="utf-8")
    summary={"status":state["status"],"generation":state["generation"],
      "total_candidates_evaluated":state["evaluated"],"failure_counts":state["failure_counts"],
      "last_generation":state.get("last_generation"),"best":state.get("winner") or state.get("best"),
      "message":("All configured historical walk-forward gates passed. Paper-forward validation is still required."
        if state["status"]=="FOUND" else
        "No candidate has passed every gate yet. Checkpoint saved; the next scheduled run can resume.")}
    (out/"latest_report.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8")
    return summary
