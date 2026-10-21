"""Command-line entry points for research-only expert and panel runs."""
import argparse
import json
from pathlib import Path
from .registry import default_experts, get_expert
from .workflow import ExpertWorkflow
from .panel import PanelCoordinator
from ..knowledge import KnowledgeIndex

def main() -> int:
    parser = argparse.ArgumentParser(description="Run sourced trading research; never places orders.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--market-context", default="")
    parser.add_argument("--index", default="data/knowledge.sqlite3")
    parser.add_argument("--memory", default="data/memory")
    parser.add_argument("--panel", action="store_true", help="Run a multi-specialist discussion and synthesis.")
    parser.add_argument("--experts", default="", help="Comma-separated specialist IDs for panel mode.")
    parser.add_argument("--max-experts", type=int, default=6, help="Bound API usage; panel mode accepts 1..30.")
    parser.add_argument("--expert", choices=[p.agent_id for p in default_experts()], default="trend_momentum")
    args = parser.parse_args()
    index = KnowledgeIndex(args.index)
    if args.panel:
        ids = [item.strip() for item in args.experts.split(",") if item.strip()] or None
        result = PanelCoordinator(index, args.memory).discuss(
            args.question, args.market_context, expert_ids=ids, max_experts=args.max_experts
        )
    else:
        profile = get_expert(args.expert)
        memory = Path(args.memory) / (profile.agent_id + ".jsonl")
        result = ExpertWorkflow(profile, index, memory).research(args.question, args.market_context)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
