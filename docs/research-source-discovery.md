# Research source discovery policy

The goal is relevant, traceable research for each specialist—not a giant unfiltered scrape.

## Discovery layers
1. **Broad scholarly indexes:** OpenAlex, Crossref and Semantic Scholar discover papers, authors, venues, citations and open-access copies. They are discovery/metadata services, not guarantees of full-text access.
2. **Preprint and specialist repositories:** arXiv for quantitative methods/ML; RePEc/IDEAS and NBER for economics and finance.
3. **Institutional research portals:** IMF, BIS, Federal Reserve and ECB for macro, rates, FX and market-structure research.
4. **Topic routing:** each expert should query only the sources mapped to its methods, then follow references/citations and search for contradictory findings.
5. **Evidence quality:** store DOI/URL, title, authors, year, venue, abstract, retrieval timestamp, access/license, source type, and why it is relevant. Mark preprints as preprints. Record retractions/corrections when available.
6. **Full text:** download only when openly licensed or otherwise authorized. Respect site/API terms, rate limits, robots policies, and publisher restrictions. Do not bypass paywalls or claim to have read a paper when only its metadata/abstract was available.
7. **Coverage honesty:** no finite run can truthfully claim to have read every article from every country/site. Start with a documented catalog and repeatable API searches, persist results, deduplicate by DOI/title, and expand the catalog from discovered venues and references.

## Official API references
- OpenAlex API: https://help.openalex.org/api/
- Crossref REST API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Semantic Scholar API: https://api.semanticscholar.org/api-docs/
- arXiv API: https://info.arxiv.org/help/api/index.html
- RePEc: https://repec.org/
- NBER papers: https://www.nber.org/papers
- IMF Working Papers: https://www.imf.org/en/Publications/WP
- BIS research: https://www.bis.org/list/research/index.htm
- Federal Reserve FEDS: https://www.federalreserve.gov/econres/feds/
- ECB Working Papers: https://www.ecb.europa.eu/pub/research/working-papers/html/index.en.html

This catalog is the initial verified shortlist, not an exhaustive country-by-country inventory. Expand it by discipline and jurisdiction as the discovery pipeline is implemented and tested.


## Google web search integration

The code includes an adapter for Google's Programmable Search Engine JSON API, requiring `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`. However, Google's current official documentation says the Custom Search JSON API is closed to new customers and existing customers must transition by January 1, 2027. Thus, this adapter is only practical for eligible existing accounts during the transition; do not assume it is available for a new deployment. It is not an unrestricted crawler of every Google result. The general web-search adapter is the practical broad-search fallback; Vertex AI Search is worth evaluating for a configured set of domains, not as a drop-in full-web Google search replacement.

Official setup references:
- Programmable Search Engine: https://programmablesearchengine.google.com/
- Custom Search JSON API documentation: https://developers.google.com/custom-search/v1/overview


## Evidence labels emitted by the OpenAlex adapter

Each returned work has a stable `record_id` (DOI when supplied, otherwise the OpenAlex work ID), authors, year, venue, landing page, and any advertised PDF URL. The adapter reconstructs the abstract only when OpenAlex actually supplies its abstract index.

- `evidence_level=metadata`: discovery metadata only; no abstract was supplied.
- `evidence_level=abstract`: the abstract is available, but the full paper has not been ingested.
- `full_text_ingested=false`: deliberately remains false for discovery results. A PDF URL or OpenAlex open-access flag alone is not proof that Vor downloaded, read, or is licensed to store the full text.
- `license=null`: the adapter does not infer a license from availability. A future ingestion step must independently verify and persist the applicable license/terms.

Tests mock the API response to verify DOI fallback, abstract reconstruction, and that metadata/abstract records are never mislabeled as full text. These tests do not require a network connection or API key.


## Persistent local research catalog

The new `ResearchCatalog` stores discovered records in a local SQLite database, deduplicates DOI variants (for example `https://doi.org/10.1234/ABC` and `10.1234/abc`), supports simple keyword search, and reports counts by evidence level. It is standard-library-only; no paid API or database service is required.

Example from Python after installing the project:

```python
from crypto_quant.knowledge import ResearchCatalog, discover_openalex_into_catalog

catalog = ResearchCatalog("data/research_catalog.sqlite3")
run = discover_openalex_into_catalog(
    catalog,
    query="cryptocurrency market liquidity volatility",
    limit=10,
)
print(run["counts"])
print(catalog.stats())
for paper in catalog.search("liquidity volatility", limit=5):
    print(paper["title"], paper.get("doi"), paper["evidence_level"])
```

The discovery helper stores the UTC retrieval timestamp. Repeated searches refresh matching records rather than multiplying DOI duplicates. Stronger evidence is not downgraded by a later metadata-only refresh. The catalog rejects full-text claims unless the record explicitly marks full text as ingested and includes a license/authorization field; callers must only provide that field after independently verifying it. This is a local metadata/abstract catalog, not a claim that a corpus of full papers has already been collected.


## Retrieval quality evaluation

The offline evaluator computes macro-averaged precision@k, recall@k and mean reciprocal rank (MRR@k) for queries with explicit relevance labels. It is intended to make retrieval regressions visible before expanding the agent population.

A minimal example:

```python
from crypto_quant.knowledge import ResearchCatalog, evaluate_retrieval

catalog = ResearchCatalog("data/research_catalog.sqlite3")
report = evaluate_retrieval(catalog, [
    {
        "query": "crypto market liquidity",
        # Replace these example IDs with records judged relevant by a reviewer.
        "relevant_record_ids": ["10.1234/example-doi"],
    },
], k=5)
print(report["precision_at_k"], report["recall_at_k"], report["mrr_at_k"])
```

The evaluator does not invent relevance judgments or fetch papers. Build a benchmark by having a reviewer label relevant record IDs for representative queries (for example, momentum, market-making, liquidity, volatility, exchange microstructure and portfolio risk), document the labeling rules, and keep the same held-out cases when comparing changes. The synthetic records in automated tests only verify metric contracts; they are **not** evidence that real-world search relevance is good. Keyword search is still a simple baseline, not semantic retrieval.
