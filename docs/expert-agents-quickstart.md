# Expert-agent prototype: quickstart

The repository has starter implementations for distinct research roles, structured opinions, persistent JSONL memory, optional API adapters, a local SQLite full-text index for permitted Markdown/text sources, and a command-line entry point. This is not yet a finished 5,000-agent service.

## Free local reasoning (no paid API key)

The panel's reasoning adapter now prefers the hosted OpenAI API only when `OPENAI_API_KEY` is set. If it is absent, the adapter uses a local Ollama server with no API key.

1. Install Ollama from https://ollama.com/download.
2. Start Ollama, then download a model that fits your hardware, for example:

   ```bash
   ollama pull qwen2.5:7b
   ```

3. Leave `OPENAI_API_KEY` unset. Optionally set `OLLAMA_MODEL` and `OLLAMA_BASE_URL` (default model `qwen2.5:7b`, default endpoint `http://localhost:11434/v1`).
4. Run the CLI examples below on the same machine as Ollama.

Local inference does not need a paid API key, but model downloads use disk space and inference uses your own RAM/CPU/GPU and electricity. A 7B model may be slow or fail on hardware with insufficient memory. A GitHub-hosted workflow runner will not automatically have your personal Ollama server; do not expect local reasoning to work in GitHub Actions unless a self-hosted runner is explicitly configured.

## Local knowledge base

Only ingest documents you have the right to store. The initial index supports .txt and .md, stores source path and SHA-256 content hash, chunks sources, and performs SQLite FTS retrieval. PDF/EPUB extraction, source-license workflows, large-corpus deduplication, and automated book acquisition are not implemented yet.

    from crypto_quant.knowledge import KnowledgeIndex
    index = KnowledgeIndex("data/knowledge.sqlite3")
    print(index.ingest_directory("data/library"))
    print(index.search("trend following momentum", limit=5))

See source-library-policy.md for source rights and provenance requirements.

## Optional web and scholarly search

- OpenAlex scholarly metadata search is available without a paid key; set `OPENALEX_MAILTO` only if you want to provide contact metadata.
- Brave web search requires `BRAVE_SEARCH_API_KEY` and provider access/quotas; do not assume it is free without checking the account terms.
- Google Programmable Search JSON API requires `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`, and is only suitable for eligible existing accounts. It is not unrestricted Google crawling; Google's documentation says it is closed to new customers and existing customers must transition by January 1, 2027. For a new deployment, don't rely on this legacy adapter.

## Enable hosted reasoning (optional, may cost money)

Set `OPENAI_API_KEY` in the deployment environment to enable OpenAI-hosted reasoning. `OPENAI_MODEL` optionally selects the model; `OPENAI_BASE_URL` optionally changes the compatible endpoint. If this key is set, hosted reasoning takes precedence over local Ollama.

Never commit API keys to Git. Use environment variables or repository secrets.

## Run a specialist or bounded panel

Install the package and its development extras:

    pip install -e ".[dev]"

Run one specialist:

    python -m crypto_quant.experts.cli --expert trend_momentum --question "What evidence supports time-series momentum?" --market-context "BTC/USD daily candles"

Run a bounded multi-specialist discussion (default 6 experts):

    python -m crypto_quant.experts.cli --panel --max-experts 6 --question "Compare momentum and mean reversion for BTC" --market-context "Daily data; include fees and slippage"

Or explicitly choose the panel:

    python -m crypto_quant.experts.cli --panel --experts trend_momentum,mean_reversion,market_microstructure,risk_auditor --max-experts 4 --question "Compare strategy evidence"

Adapters are optional and make no requests unless explicitly called. Search queries include each specialist's methodology and configured topic terms; the research note preserves publication/source dates when the provider supplies them.

The workflow retrieves local knowledge using both the question and the specialist's own specialty/search topics. It keeps model-claimed citations for audit, but only exposes URLs actually returned by the search provider as verified `source_refs`. If neither local knowledge nor web sources were retrieved, a directional LONG/SHORT output is suppressed to `NO_TRADE`. This is an evidence-quality guardrail, not proof that any remaining opinion is correct. Search metadata/snippets are still not the same as reading a paper's full text.

## Scope and remaining work

- The registry currently contains 30 distinct research archetypes, not 5,000 independent deployed experts. The panel can select a bounded subset and preserve disagreement; the default is six experts to control latency and cost.
- No 15,000-source corpus has been collected or indexed; source discovery returns metadata/snippets unless authorized full text is separately ingested.
- Live provider connections must be tested in the target environment.
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
