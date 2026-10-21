# Expert-agent prototype: quickstart

This is the first runnable software foundation for the expert-agent architecture. It creates distinct research roles, a structured opinion schema, a bounded search-provider interface, persistent JSONL research notes, and a transparent synthesis helper. It does not claim that these profiles are human experts, that any books have already been ingested, or that a live search provider is configured by default.

## Current starter roles

- RTM-style price-action research
- Al Brooks-style bar-by-bar price-action research
- Trend and momentum
- Volatility and market regimes
- Market structure and microstructure
- Independent risk/evidence auditor

These names describe methodological areas, not affiliation or endorsement by named educators.

## Try it

Install the package and development dependencies, then run pytest. Example research flow:

    from pathlib import Path
    from crypto_quant.experts import ResearchAgent, get_expert

    agent = ResearchAgent(get_expert("trend_momentum"), Path("data/memory/trend_momentum.jsonl"))
    note = agent.research("What evidence supports time-series momentum in liquid markets?")
    print(note)

Without a search_provider, the agent explicitly records that no web search occurred. To enable Google, another search engine, or other sites, implement a provider adapter that returns SearchResult values and uses approved credentials and the providers' terms. The prototype intentionally does not scrape search pages, bypass access controls, or fabricate sources.

## What is not done yet

- No 15,000-book corpus has been collected or indexed.
- No API/LLM reasoning backend is wired in.
- No live web provider is configured by default.
- No 5,000 distinct expert profiles exist yet.
- No trading orders are executed.
- These research roles have not demonstrated profitability.

## Next implementation steps

1. Add source registry, license/provenance checks, document ingestion, deduplication, and cited retrieval.
2. Wire a configured search provider and LLM adapter behind explicit interfaces.
3. Add reviewed persistent knowledge updates, bounded budgets, caching, and source-quality scoring.
4. Test each specialist with blinded historical examples, citations, counter-evidence, and abstention.
5. Add chronological walk-forward evaluation and only then scale the population.
