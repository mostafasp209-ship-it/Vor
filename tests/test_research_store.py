from __future__ import annotations

import pytest

from crypto_quant.knowledge.research_store import ResearchCatalog


def test_catalog_deduplicates_doi_variants_and_searches(tmp_path):
    catalog = ResearchCatalog(tmp_path / "research.sqlite3")
    first = {
        "source_id": "openalex",
        "record_id": "https://openalex.org/W1",
        "doi": "https://doi.org/10.1234/ABC",
        "title": "Crypto market liquidity",
        "year": 2024,
        "abstract": "Liquidity changes during volatility.",
        "evidence_level": "abstract",
        "full_text_ingested": False,
    }
    second = {
        **first,
        "source_id": "crossref",
        "record_id": "https://doi.org/10.1234/abc",
        "doi": "10.1234/abc",
        "title": "Crypto market liquidity",
        "abstract": None,
        "evidence_level": "metadata",
    }

    assert catalog.upsert([first]) == {"inserted": 1, "updated": 0, "skipped": 0}
    assert catalog.upsert([second]) == {"inserted": 0, "updated": 1, "skipped": 0}
    assert catalog.stats()["total"] == 1
    assert catalog.stats()["abstract"] == 1
    assert catalog.search("crypto liquidity")[0]["evidence_level"] == "abstract"


def test_catalog_rejects_unlicensed_or_mislabelled_full_text(tmp_path):
    catalog = ResearchCatalog(tmp_path / "research.sqlite3")
    record = {
        "source_id": "openalex",
        "record_id": "W2",
        "title": "A full text claim",
        "evidence_level": "full_text",
        "full_text_ingested": True,
    }
    with pytest.raises(ValueError, match="license/authorization"):
        catalog.upsert([record])

    record["license"] = "CC-BY-4.0"
    record["full_text_ingested"] = False
    with pytest.raises(ValueError, match="full_text_ingested"):
        catalog.upsert([record])


def test_catalog_does_not_downgrade_full_text_when_metadata_refreshes(tmp_path):
    catalog = ResearchCatalog(tmp_path / "research.sqlite3")
    full_text = {
        "source_id": "local_repository",
        "record_id": "W3",
        "title": "Open finance paper",
        "year": 2022,
        "evidence_level": "full_text",
        "full_text_ingested": True,
        "license": "CC-BY-4.0",
        "text": "The verified stored paper text.",
    }
    metadata = {
        "source_id": "openalex",
        "record_id": "W3",
        "title": "Open finance paper",
        "year": 2022,
        "evidence_level": "metadata",
        "full_text_ingested": False,
    }
    catalog.upsert([full_text])
    catalog.upsert([metadata])
    stored = catalog.search("finance paper")[0]
    assert stored["evidence_level"] == "full_text"
    assert stored["full_text_ingested"] is True
    assert stored["text"] == "The verified stored paper text."


def test_catalog_validates_search_limit_and_empty_query(tmp_path):
    catalog = ResearchCatalog(tmp_path / "research.sqlite3")
    assert catalog.search("  ") == []
    with pytest.raises(ValueError):
        catalog.search("paper", limit=0)
