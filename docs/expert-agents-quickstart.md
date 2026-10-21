# Expert-agent prototype: quickstart

The repository has starter implementations for distinct research roles, structured opinions, persistent JSONL memory, optional API adapters, a local SQLite full-text index for permitted Markdown/text sources, and a command-line entry point. This is not yet a finished 5,000-agent service.

## Local knowledge base

Only ingest documents you have the right to store. The initial index supports .txt and .md, stores source path and SHA-256 content hash, chunks sources, and performs SQLite FTS retrieval. PDF/EPUB extraction, source-license workflows, large-corpus deduplication, and automated book acquisition are not implemented yet.

    from crypto_quant.knowledge import KnowledgeIndex
    index = KnowledgeIndex("data/knowledge.sqlite3")
    print(index.ingest_directory("data/library"))
    print(index.search("trend following momentum", limit=5))

See source-library-policy.md for source rights and provenance requirements.

## Enable API reasoning and live web search

Set these environment variables in the deployment environment; never commit API keys:

- OPENAI_API_KEY enables OpenAI-compatible chat completion.
- OPENAI_MODEL optionally selects the model; the default is gpt-4.1-mini.
- OPENAI_BASE_URL optionally sets an OpenAI-compatible API base URL.
- BRAVE_SEARCH_API_KEY enables Brave Search web queries.
- GOOGLE_API_KEY and GOOGLE_CSE_ID enable Google Programmable Search Engine queries (configure the engine scope in Google first).
- OPENALEX_MAILTO is optional contact metadata for scholarly API requests.

Install the package, set both keys, ingest licensed sources into the local index, then run:

    python -m crypto_quant.experts.cli --expert trend_momentum --question "What evidence supports time-series momentum?" --market-context "BTC/USD daily candles"

    # Run a bounded multi-specialist research discussion (default 6 experts)
    python -m crypto_quant.experts.cli --panel --max-experts 6 --question "Compare momentum and mean reversion for BTC" --market-context "Daily data; include fees and slippage"

    # Or explicitly choose the panel
    python -m crypto_quant.experts.cli --panel --experts trend_momentum,mean_reversion,market_microstructure,risk_auditor --max-experts 4 --question "Compare strategy evidence"

Adapters are optional and make no requests unless explicitly called. API access requires valid credentials, an active account, and applicable provider terms. Search snippets alone are not authoritative evidence; review and cite source pages.

## Scope and remaining work

- The registry currently contains distinct research archetypes, not 5,000 independent deployed experts. The panel can select a bounded subset and preserve disagreement; the default is six experts to control latency and API cost.
- Google integration uses the official Programmable Search Engine JSON API and requires GOOGLE_API_KEY plus GOOGLE_CSE_ID. It searches the configured engine scope, not every page indexed by Google. Check Google's current eligibility, quota and billing rules before deployment.
- No 15,000-source corpus has been collected or indexed; source discovery returns metadata/snippets unless authorized full text is separately ingested.
- Live providers are not verified until valid credentials and a successful integration test are supplied.
- No automated review-and-acceptance pipeline for learned knowledge exists yet.
- No trading orders are executed; this is research-only.
- No profitability claim has been established.

The panel's discussion output compares common ground, disagreements, counter-evidence, data-quality flags and proposed next tests. Relevance selection is a lightweight keyword-based starting point and needs evaluation; it is not a semantic relevance guarantee.

## Scaling plan

1. Establish a legal/open/licensed source registry, provenance, ingestion, deduplication and cited retrieval.
2. Wire a bounded search + reasoning loop requiring source references, counter-evidence, and abstention.
3. Review persistent knowledge updates; add caching, token budgets, rate limits, and secret handling.
4. Test specialists on blinded historical examples and independent risk review.
5. Use chronological walk-forward evaluation, realistic costs and untouched holdout before scaling.
