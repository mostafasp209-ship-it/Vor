import pytest
from crypto_quant.knowledge.research_store import ResearchCatalog
from crypto_quant.knowledge.evaluation import evaluate_retrieval


def _catalog(tmp_path):
    catalog = ResearchCatalog(tmp_path / "evaluation.sqlite3")
    catalog.upsert([
        {"record_id": "paper-a", "title": "Crypto market liquidity", "year": 2024,
         "abstract": "Market liquidity and spreads", "evidence_level": "abstract"},
        {"record_id": "paper-b", "title": "Crypto market volatility", "year": 2023,
         "abstract": "Volatility and risk", "evidence_level": "abstract"},
        {"record_id": "paper-c", "title": "Crypto market structure", "year": 2022,
         "abstract": "Market design", "evidence_level": "abstract"},
    ])
    return catalog


def test_metrics_calculate_precision_recall_and_mrr(tmp_path):
    report = evaluate_retrieval(_catalog(tmp_path), [
        {"query": "crypto market", "relevant_record_ids": ["paper-a", "paper-b"]},
    ], k=2)
    row = report["cases"][0]
    assert row["hits"] == 2
    assert row["precision_at_k"] == 1.0
    assert row["recall_at_k"] == 1.0
    assert row["reciprocal_rank"] == 1.0
    assert report["mrr_at_k"] == 1.0


def test_missing_relevant_record_scores_zero_for_recall_and_mrr(tmp_path):
    report = evaluate_retrieval(_catalog(tmp_path), [
        {"query": "crypto market", "relevant_record_ids": ["not-in-catalog"]},
    ], k=2)
    assert report["cases"][0]["recall_at_k"] == 0.0
    assert report["cases"][0]["reciprocal_rank"] == 0.0


def test_macro_average_across_cases(tmp_path):
    report = evaluate_retrieval(_catalog(tmp_path), [
        {"query": "crypto liquidity", "relevant_record_ids": ["paper-a"]},
        {"query": "crypto structure", "relevant_record_ids": ["missing"]},
    ], k=2)
    assert report["case_count"] == 2
    assert report["recall_at_k"] == 0.5
    assert report["mrr_at_k"] == 0.5


@pytest.mark.parametrize("k", [0, 101])
def test_invalid_k_rejected(tmp_path, k):
    with pytest.raises(ValueError, match="k must"):
        evaluate_retrieval(_catalog(tmp_path), [
            {"query": "crypto", "relevant_record_ids": ["paper-a"]},
        ], k=k)


@pytest.mark.parametrize("cases, message", [
    ([], "at least one"),
    ([{"query": "  ", "relevant_record_ids": ["paper-a"]}], "empty query"),
    ([{"query": "crypto", "relevant_record_ids": []}], "relevant record ID"),
])
def test_invalid_cases_rejected(tmp_path, cases, message):
    with pytest.raises(ValueError, match=message):
        evaluate_retrieval(_catalog(tmp_path), cases)
