"""Transparent synthesis helpers; consensus is not evidence of a trading edge."""
from .schema import ExpertOpinion

def summarize_opinions(opinions: list[ExpertOpinion]) -> dict:
    counts = {"LONG": 0, "SHORT": 0, "NO_TRADE": 0}
    for opinion in opinions:
        counts[opinion.action] += 1
    directional = counts["LONG"] + counts["SHORT"]
    consensus = "NO_TRADE"
    if directional and counts["LONG"] > counts["SHORT"]:
        consensus = "LONG"
    elif directional and counts["SHORT"] > counts["LONG"]:
        consensus = "SHORT"
    return {
        "consensus": consensus,
        "opinion_count": len(opinions),
        "action_counts": counts,
        "agreement_fraction": (max(counts["LONG"], counts["SHORT"]) / directional) if directional else 0.0,
        "caveat": "Vote counts are not a calibrated probability or evidence of profitability; review citations, conflicts, costs, and out-of-sample results.",
    }
