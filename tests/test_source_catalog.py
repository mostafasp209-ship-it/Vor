from crypto_quant.experts.registry import default_experts, get_expert
from crypto_quant.knowledge.source_catalog import SOURCES, sources_for_topics, search_openalex


def test_specialists_have_distinct_methods_and_routed_sources():
    experts = default_experts()
    assert len(experts) >= 25
    assert len({e.agent_id for e in experts}) == len(experts)
    assert len({e.method_checklist for e in experts}) >= 20
    assert sources_for_topics(get_expert("macro_rates").source_topics)
    assert any(s.source_id == "imf" for s in sources_for_topics(("macro",)))


def test_source_catalog_has_no_empty_or_disabled_entries():
    assert SOURCES
    assert all(s.url.startswith("https://") and s.name for s in SOURCES)


def test_openalex_search_validates_input_without_network():
    import pytest
    with pytest.raises(ValueError):
        search_openalex("test", limit=0)
    assert search_openalex("  ") == []
