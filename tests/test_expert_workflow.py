from pathlib import Path
import json

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
        payload = json.loads(user)
        assert payload["local_sources"]
        assert "search_note" in payload
        assert "specialty" in payload
        return (
            '{"action":"NO_TRADE","summary":"Need more evidence","evidence":[],'
            '"counter_evidence":[],"assumptions":[],"invalidation":[],"confidence":0.1,'
            '"source_refs":["https://example.org/study","https://fabricated.invalid/paper"],'
            '"limitations":["sample"]}'
        )

    workflow = ExpertWorkflow(get_expert("trend_momentum"), index, tmp_path / "memory.jsonl", search, reason)
    result = workflow.research("momentum trend", "BTC daily")
    assert result["research_only"] is True
    assert result["retrieved_web_sources"] == ["https://example.org/study"]
    assert result["source_refs"] == ["https://example.org/study"]
    assert result["unverified_model_source_refs"] == ["https://fabricated.invalid/paper"]
    assert result["action"] == "NO_TRADE"


def test_workflow_invalid_model_json_abstains(tmp_path: Path):
    index = KnowledgeIndex(tmp_path / "index.sqlite3")
    workflow = ExpertWorkflow(
        get_expert("risk_auditor"), index, tmp_path / "memory.jsonl",
        lambda query, limit: [], lambda system, user: "not json"
    )
    result = workflow.research("assess evidence")
    assert result["action"] == "NO_TRADE"
    assert result["confidence"] == 0.0
    assert result["unverified_model_source_refs"] == []
    assert any("No matching local knowledge" in item for item in result["limitations"])


def test_empty_question_is_rejected_before_search(tmp_path: Path):
    index = KnowledgeIndex(tmp_path / "index.sqlite3")
    workflow = ExpertWorkflow(
        get_expert("risk_auditor"), index, tmp_path / "memory.jsonl",
        lambda query, limit: [], lambda system, user: "{}"
    )
    import pytest
    with pytest.raises(ValueError, match="question must not be empty"):
        workflow.research("  ")
