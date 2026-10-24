# Real-world retrieval evaluation protocol

This protocol turns the retrieval metric helper into a reproducible evaluation rather than treating synthetic unit tests as proof of search quality.

## Scope

Start with five topics:
- momentum and trend-following
- liquidity and market microstructure
- volatility and risk
- crypto-market structure
- backtesting bias and transaction costs

## Procedure

1. Populate the local SQLite catalog using the documented OpenAlex discovery flow. Store the provider's stable ID, DOI when present, title, authors, year, abstract, source URL, retrieval timestamp, and evidence level.
2. Freeze a catalog snapshot for each evaluation run. Record the snapshot date and query parameters so results can be reproduced.
3. For each topic, write at least 5 natural-language queries. Search broadly enough to include papers that may disagree with the presumed hypothesis.
4. Have a human reviewer inspect candidate papers and label relevant catalog `record_id` values. Do not infer relevance from keyword overlap alone. Record reviewer, date, and a short rationale for each judgment.
5. Store cases in JSON using the schema expected by `evaluate_retrieval`:
   ```json
   {
     "query": "transaction costs and momentum strategy performance",
     "relevant_record_ids": ["<exact-record_id-from-frozen-catalog>"]
   }
   ```
   Replace placeholders with real IDs before scoring; placeholder cases are not executable evaluation data.
6. Run the evaluation at k=5 and k=10. Report macro Precision@k, Recall@k and MRR, number of queries, number of judged relevant records, and topic-level scores. Include failed/empty retrievals rather than silently dropping them.
7. Compare changes against the same frozen query set and relevance judgments. Do not tune and report on the same small set without disclosing that it is a development set.
8. Inspect misses and false positives manually. Include contradictory or null findings, not only papers supporting a strategy.
9. Keep a separate untouched holdout set for final reporting. Unit tests validate metric arithmetic; only judged real papers can estimate retrieval quality.

## Evidence and licensing rules

- Metadata and abstracts are not full text. Keep evidence levels explicit.
- Download or ingest full text only when openly licensed or otherwise authorized; respect API terms, rate limits, and publisher restrictions.
- Record retractions/corrections when available.
- Retrieval scores measure retrieval against the reviewed labels, not truth, trading performance, or profitability.

## Minimum release gate

Do not describe retrieval as validated until the catalog snapshot, query set, relevance judgments, and run report are saved and independently reproducible. Do not enable live trading based on retrieval scores alone.
