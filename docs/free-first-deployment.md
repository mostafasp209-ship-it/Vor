# Free-first deployment and scaling plan

This project is research-only. It does not place orders and makes no profitability guarantee.

## Zero-paid-API baseline

1. Install Python 3.11+ and the project dependencies: `pip install -e ".[dev,market-data]"`.
2. Install Ollama from https://ollama.com/download and start its local service.
3. Download one model appropriate to the machine, for example `ollama pull qwen2.5:7b`. If memory is limited, choose a smaller model and expect lower reasoning quality.
4. Leave `OPENAI_API_KEY`, `BRAVE_SEARCH_API_KEY`, and Google credentials unset. The reasoning adapter then targets the local Ollama OpenAI-compatible endpoint. OpenAlex metadata discovery is attempted without a paid search key.
5. Run a bounded panel:

   ```bash
   python -m crypto_quant.experts.cli --panel --max-experts 4 \
     --question "Compare trend-following and mean-reversion evidence for BTC" \
     --market-context "Use daily candles; account for fees, spread, slippage, and funding"
   ```

Local inference is not cloud-hosted: it consumes the user's CPU/GPU, RAM, disk and electricity. GitHub-hosted runners do not have access to a developer's local Ollama process. A no-key local setup must be run on the machine where Ollama is installed, or on a properly configured self-hosted runner.

## Search behavior and evidence limitations

- OpenAlex provides scholarly discovery metadata; a record or abstract is not the same as verified full-text reading.
- Brave and Google adapters are optional. They are skipped when credentials are unavailable. Google Custom Search JSON API is a legacy option for eligible accounts only and must not be assumed available to new customers.
- Search results are deduplicated by URL and interleaved across providers so a single source is less likely to consume the entire result budget.
- The result cap is intentional: it bounds latency and resource usage. Increase it only with rate limits, caching and evaluation.
- Store full text only when licensing or other authorization permits. Preserve canonical URL/DOI, retrieval date, authors, year, source type, and license/provenance where available.

## How to scale toward 5,000 knowledge specialists

The current registry contains a limited set of authored methodology profiles, not 5,000 independently validated experts. Do not claim otherwise. Scaling should mean 5,000 *distinct, testable knowledge specializations*, not 5,000 copies of the same prompt.

For each specialization, require:
- a clearly bounded subject and a curated source map;
- a methodology checklist, known failure modes, and falsifiable claims;
- independent retrieval filters and a namespaced memory store;
- source citations and explicit evidence/counter-evidence separation;
- a benchmark set with expected reasoning properties and regression tests;
- provenance/versioning for every learned memory update;
- a documented abstention rule when sources or market data are insufficient.

Generate catalog entries from reviewed templates only after a human-readable distinction is defined; reject duplicate or near-duplicate specialties. Use shared infrastructure for retrieval and inference rather than keeping 5,000 models running. Schedule a bounded subset per question, cache identical searches, enforce provider quotas, and run independent risk/backtest audits.

## Required validation before any live signal use

1. Test source timestamps, missing values, duplicate candles and exchange differences.
2. Prevent look-ahead, survivorship and data leakage; use chronological walk-forward splits and a final untouched holdout.
3. Include fees, spread, slippage, funding, borrow costs, latency and realistic fill assumptions.
4. Compare against simple baselines and randomized/null strategies.
5. Report drawdown, tail loss, turnover, sample size, uncertainty and performance by regime, not only win rate.
6. Keep outputs as research-only until independently reviewed. A panel consensus is not proof of edge.

## CI

GitHub Actions runs the project's pytest suite on pushes and pull requests. A green test run verifies the tested code paths only; it does not prove live provider credentials, Ollama hardware compatibility, complete source coverage or profitability.
