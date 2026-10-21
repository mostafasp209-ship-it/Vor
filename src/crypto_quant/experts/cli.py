"""Command-line entry point for one research-only specialist run."""
import argparse
import json
from pathlib import Path
from .registry import default_experts, get_expert
from .workflow import ExpertWorkflow
from ..knowledge import KnowledgeIndex

def main() -> int:
    parser = argparse.ArgumentParser(description="Run one sourced trading research specialist; never places orders.")
    parser.add_argument("--expert", choices=[p.agent_id for p in default_experts()], default="trend_momentum")
    parser.add_argument("--question", required=True)
    parser.add_argument("--market-context", default="")
    parser.add_argument("--index", default="data/knowledge.sqlite3")
    parser.add_argument("--memory", default="data/memory")
    args = parser.parse_args()
    profile = get_expert(args.expert)
    memory = Path(args.memory) / (profile.agent_id + ".jsonl")
    result = ExpertWorkflow(profile, KnowledgeIndex(args.index), memory).research(args.question, args.market_context)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
