"""CLI for Vor's futures strategy discovery engine."""
import argparse, json
from crypto_quant.search_engine import run_search

def main():
    p=argparse.ArgumentParser(description="Search and validate futures strategies in Vor")
    p.add_argument("--symbols",default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    p.add_argument("--intervals",default="15m,1h")
    p.add_argument("--days",type=int,default=365)
    p.add_argument("--candidates",type=int,default=300)
    p.add_argument("--shortlist",type=int,default=25)
    p.add_argument("--min-trades",type=int,default=30)
    p.add_argument("--fee-bps",type=float,default=5.)
    p.add_argument("--slippage-bps",type=float,default=2.)
    p.add_argument("--output",default="artifacts/strategy_search")
    a=p.parse_args()
    reports=run_search([x.strip().upper() for x in a.symbols.split(",") if x.strip()],
      [x.strip() for x in a.intervals.split(",") if x.strip()],days=a.days,
      max_candidates=a.candidates,shortlist=a.shortlist,min_trades=a.min_trades,
      fee_bps=a.fee_bps,slippage_bps=a.slippage_bps,output_dir=a.output)
    for r in reports:
        print(f"\n{r['symbol']} {r['interval']}: {r['qualified_count']} passed all gates")
        for x in r["results"][:5]:
            print(json.dumps({"passed":x["qualifies"],"strategy":x["strategy"],
              "validation":x["validation"],"test":x["test"]},sort_keys=True))

if __name__=="__main__": main()
