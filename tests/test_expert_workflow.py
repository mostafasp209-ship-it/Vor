from pathlib import Path
from crypto_quant.experts.registry import get_expert
from crypto_quant.experts.workflow import ExpertWorkflow
from crypto_quant.knowledge import KnowledgeIndex
from crypto_quant.experts.research_loop import SearchResult

def test_workflow_combines_retrieval_search_and_reasoning_without_network(tmp_path: Path):
    source = tmp_path / "research.md"
    source.write_text("# Momentum\nTime series momentum trend research evidence.", encoding="utf-8")
    index = KnowledgeIndex(tmp_path / "index.sqlite3")
    index.ingest_file(source)
    def search(query, limit):
        return [SearchResult("Study", "https://example.org/study", "A sample snippet")]
    def reason(system, user):
        assert "local_sources" in user and "search_note" in user
        return '{"action":"NO_TRADE","summary":"Need more evidence","evidence":[],"counter_evidence":[],"assumptions":[],"invalidation":[],"confidence":0.1,"source_refs":[],"limitations":["sample"]}'
    workflow = ExpertWorkflow(get_expert("trend_momentum"), index, tmp_path / "memory.jsonl", search, reason)
    result = workflow.research("momentum trend", "BTC daily")
    assert result["research_only"] is True
    assert result["retrieved_web_sources"] == ["https://example.org/study"]
    assert result["action"] == "NO_TRADE"

def test_workflow_invalid_model_json_abstains(tmp_path: Path):
    index = KnowledgeIndex(tmp_path / "index.sqlite3")
    workflow = ExpertWorkflow(get_expert("risk_auditor"), index, tmp_path / "memory.jsonl",
        lambda query, limit: [], lambda system, user: "not json")
    result = workflow.research("assess evidence")
    assert result["action"] == "NO_TRADE"
    assert result["confidence"] == 0.0
