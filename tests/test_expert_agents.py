import json
from pathlib import Path

import pytest

from crypto_quant.experts import ExpertOpinion, ResearchAgent, SearchResult, default_experts, get_expert
from crypto_quant.experts.synthesis import summarize_opinions

def test_registry_has_distinct_starter_specialists():
    experts = default_experts()
    assert len(experts) >= 5
    assert len({e.agent_id for e in experts}) == len(experts)
    assert get_expert("risk_auditor").specialty

def test_research_agent_persists_cited_search_results(tmp_path: Path):
    def search(query: str, limit: int):
        return [SearchResult("Public research", "https://example.org/paper", f"Matched query: {query}")]
    agent = ResearchAgent(default_experts()[0], tmp_path / "memory.jsonl", search, max_results=2)
    note = agent.research("how to test a trading hypothesis")
    assert note.source_refs == ("https://example.org/paper",)
    assert len(agent.read_memory()) == 1
    stored = json.loads((tmp_path / "memory.jsonl").read_text())
    assert stored["agent_id"] == default_experts()[0].agent_id

def test_no_provider_is_explicit_and_does_not_claim_to_search(tmp_path: Path):
    note = ResearchAgent(default_experts()[0], tmp_path / "memory.jsonl").research("test")
    assert not note.source_refs
    assert any("No search provider configured" in item for item in note.limitations)

def test_opinion_validates_confidence():
    with pytest.raises(ValueError):
        ExpertOpinion("x", "test", "BTC", confidence=1.1)

def test_synthesis_does_not_call_vote_a_probability():
    opinions = [ExpertOpinion("a", "trend", "BTC", action="LONG", confidence=.7),
                ExpertOpinion("b", "risk", "BTC", action="NO_TRADE")]
    result = summarize_opinions(opinions)
    assert result["consensus"] == "LONG"
    assert "not a calibrated probability" in result["caveat"]
