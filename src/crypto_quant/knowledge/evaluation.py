"""Offline evaluation helpers for the local scholarly retrieval catalog.

Relevance labels must be supplied by a human or a documented evaluation set.
Synthetic fixtures are useful for contract tests, not evidence of real-world quality.
"""
from __future__ import annotations

from typing import Iterable
from .research_store import ResearchCatalog


def evaluate_retrieval(catalog: ResearchCatalog, cases: Iterable[dict], k: int = 5) -> dict:
    """Compute precision@k, recall@k and reciprocal rank for labeled queries.

    Each case has query and relevant_record_ids. IDs are compared exactly with
    each result's record_id. Aggregate scores are macro-averages across cases.
    """
    if not 1 <= k <= 100:
        raise ValueError("k must be between 1 and 100")
    normalized_cases = list(cases)
    if not normalized_cases:
        raise ValueError("at least one evaluation case is required")
    results = []
    for index, case in enumerate(normalized_cases):
        query = str(case.get("query", "")).strip()
        relevant = {str(item) for item in case.get("relevant_record_ids", []) if str(item)}
        if not query:
            raise ValueError(f"case {index} has an empty query")
        if not relevant:
            raise ValueError(f"case {index} needs at least one relevant record ID")
        retrieved = catalog.search(query, limit=k)
        ranked_ids = [str(record.get("record_id", "")) for record in retrieved]
        first_rank = next((rank for rank, rid in enumerate(ranked_ids, start=1) if rid in relevant), None)
        hits = len(set(ranked_ids) & relevant)
        results.append({
            "query": query, "k": k, "retrieved_record_ids": ranked_ids,
            "relevant_record_ids": sorted(relevant), "hits": hits,
            "precision_at_k": hits / k,
            "recall_at_k": hits / len(relevant),
            "reciprocal_rank": 1.0 / first_rank if first_rank is not None else 0.0,
            "first_relevant_rank": first_rank,
        })
    count = len(results)
    return {
        "k": k, "case_count": count,
        "precision_at_k": sum(row["precision_at_k"] for row in results) / count,
        "recall_at_k": sum(row["recall_at_k"] for row in results) / count,
        "mrr_at_k": sum(row["reciprocal_rank"] for row in results) / count,
        "cases": results,
        "evaluation_note": "Metrics are only as trustworthy as the supplied relevance labels.",
    }
