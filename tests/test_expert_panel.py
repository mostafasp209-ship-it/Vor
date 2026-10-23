from pathlib import Path
from crypto_quant.experts.panel import PanelCoordinator
from crypto_quant.experts.registry import get_expert


class FakeIndex:
    pass


class FakeWorkflow:
    def __init__(self, profile, index, memory_path):
        self.profile = profile
        self.memory_path = memory_path

    def research(self, question, market_context=""):
        return {
            "specialist_id": self.profile.agent_id,
            "action": "LONG" if self.profile.agent_id == "trend_momentum" else "NO_TRADE",
            "confidence": 0.5,
            "evidence": ["test evidence"],
            "counter_evidence": [],
            "source_refs": [],
        }


def moderator(system, user):
    return '{"summary":"Mixed evidence","common_ground":[],"disagreements":["different action"],"strongest_evidence":[],"counter_evidence":[],"data_quality_flags":[],"next_tests":["out-of-sample test"],"provisional_action":"NO_TRADE","confidence":0.2}'


def test_panel_preserves_individual_opinions_and_disagreement(tmp_path):
    panel = PanelCoordinator(FakeIndex(), tmp_path, reasoning_provider=moderator, workflow_factory=FakeWorkflow)
    result = panel.discuss("test question", expert_ids=["trend_momentum", "risk_auditor"], max_experts=2)
    assert result["panel_size_completed"] == 2
    assert result["action_counts"]["LONG"] == 1
    assert result["action_counts"]["NO_TRADE"] == 1
    assert result["discussion"]["provisional_action"] == "NO_TRADE"
    assert len(result["individual_opinions"]) == 2


def test_panel_enforces_bounded_cost_and_unknown_specialists(tmp_path):
    panel = PanelCoordinator(FakeIndex(), tmp_path, reasoning_provider=moderator, workflow_factory=FakeWorkflow)
    import pytest
    with pytest.raises(ValueError):
        panel.discuss("test", max_experts=31)
    with pytest.raises(KeyError):
        panel.discuss("test", expert_ids=["not_a_real_expert"], max_experts=2)



def directional_moderator(system, user):
    return '{"summary":"Bullish","common_ground":[],"disagreements":[],"strongest_evidence":[],"counter_evidence":[],"data_quality_flags":[],"next_tests":[],"provisional_action":"LONG","confidence":0.95}'


def test_panel_suppresses_directional_moderator_without_sourced_opinions(tmp_path):
    panel = PanelCoordinator(
        FakeIndex(), tmp_path, reasoning_provider=directional_moderator,
        workflow_factory=FakeWorkflow
    )
    result = panel.discuss(
        "test question", expert_ids=["trend_momentum", "risk_auditor"], max_experts=2
    )
    assert result["discussion"]["provisional_action"] == "NO_TRADE"
    assert result["discussion"]["confidence"] == 0.0
    assert "directional_panel_action_suppressed_no_sourced_directional_opinion" in result["discussion"]["data_quality_flags"]


def test_panel_rejects_duplicate_specialist_ids(tmp_path):
    panel = PanelCoordinator(FakeIndex(), tmp_path, reasoning_provider=moderator, workflow_factory=FakeWorkflow)
    import pytest
    with pytest.raises(ValueError, match="must not contain duplicates"):
        panel.discuss("test", expert_ids=["risk_auditor", "risk_auditor"], max_experts=2)
