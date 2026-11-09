"""Start or resume Vor's persistent autonomous strategy research loop."""
import argparse, json
from crypto_quant.autonomous_search import run_autonomous

def main():
    p=argparse.ArgumentParser(description="Adaptive, resumable walk-forward futures strategy search")
    p.add_argument("--symbols",default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    p.add_argument("--intervals",default="15m,1h")
    p.add_argument("--days",type=int,default=365)
    p.add_argument("--candidates-per-generation",type=int,default=250)
    p.add_argument("--min-trades",type=int,default=80)
    p.add_argument("--min-win-rate",type=float,default=70.)
    p.add_argument("--min-realized-rr",type=float,default=3.)
    p.add_argument("--max-hours",type=float,default=5.2)
    p.add_argument("--output",default=".research_state")
    a=p.parse_args()
    result=run_autonomous([x.strip().upper() for x in a.symbols.split(",") if x.strip()],
      [x.strip() for x in a.intervals.split(",") if x.strip()],days=a.days,
      candidates_per_generation=a.candidates_per_generation,min_trades=a.min_trades,
      min_win_rate=a.min_win_rate,min_realized_rr=a.min_realized_rr,max_hours=a.max_hours,
      output_dir=a.output)
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
