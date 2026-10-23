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



def test_openalex_records_keep_identifiers_and_distinguish_abstract_from_full_text(monkeypatch):
    import json
    from urllib.request import urlopen

    payload = {
        "results": [{
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.5555/example",
            "title": "A study of market liquidity",
            "publication_year": 2024,
            "type": "article",
            "cited_by_count": 3,
            "authorships": [{"author": {"display_name": "A. Researcher"}}],
            "open_access": {"is_oa": True},
            "primary_location": {
                "landing_page_url": "https://example.org/paper",
                "pdf_url": "https://example.org/paper.pdf",
                "source": {"display_name": "Example Journal"},
            },
            "abstract_inverted_index": {"Liquidity": [0], "affects": [1], "markets": [2]},
        }]
    }

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())
    records = search_openalex("market liquidity", limit=1)
    assert len(records) == 1
    record = records[0]
    assert record["record_id"] == "https://doi.org/10.5555/example"
    assert record["authors"] == ["A. Researcher"]
    assert record["abstract"] == "Liquidity affects markets"
    assert record["evidence_level"] == "abstract"
    assert record["full_text_ingested"] is False
    assert record["license"] is None


def test_openalex_metadata_without_abstract_is_not_promoted_to_evidence(monkeypatch):
    import json

    payload = {"results": [{
        "id": "https://openalex.org/W456",
        "title": "Metadata-only record",
        "authorships": [],
        "primary_location": None,
        "open_access": {"is_oa": False},
    }]}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())
    record = search_openalex("metadata only", limit=1)[0]
    assert record["record_id"] == "https://openalex.org/W456"
    assert record["evidence_level"] == "metadata"
    assert record["abstract"] is None
    assert record["full_text_ingested"] is False
