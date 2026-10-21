# Agentic Trading Expert Population: Architecture Proposal

## Goal

Replace the current interpretation of "5,000 agents" as 5,000 parameterized ML candidates with a population of persistent, research-capable trading specialists. Each specialist should have a defined school of thought, an evidence-backed knowledge profile, tools for research, explicit uncertainty, and a track record that can be evaluated independently.

This document is an architecture target, not a claim that the system already has 5,000 expert agents or that any style is profitable.

## Core design principle

**An agent is an expert role plus sourced knowledge, reasoning procedure, tools, memory, and an evaluation record—not merely a model with different parameters.**

Do not duplicate a 15,000-book corpus 5,000 times. Store shared, legally acquired source material once, then give each specialist a scoped retrieval view, curated reading list, notes, and private working memory. A specialist may search for more evidence and propose additions; newly found material is not trusted until it passes provenance, quality, rights, and relevance checks.

## Logical architecture

1. **Source registry and ingestion**
   - Register books, papers, exchange documentation, reputable educational articles, transcripts, and datasets.
   - Store title, author/publisher, URL or stable identifier, publication date, language, license/rights status, retrieval date, content hash, and quality notes.
   - Prefer public-domain, open-license, licensed, or user-provided sources. Do not bypass paywalls, DRM, or copyright restrictions. A target of 15,000 books is a collection goal, not permission to scrape or redistribute all books.
   - Parse documents, preserve page/section references, deduplicate, and flag OCR or extraction quality problems.

2. **Knowledge index**
   - Shared document store plus lexical and vector retrieval.
   - Chunks retain source metadata and exact citations.
   - Search supports topic, author, style, instrument, timeframe, and evidence type.
   - Retrieval returns source excerpts and references; agents must distinguish quoted facts, interpretations, and hypotheses.

3. **Expert registry**
   - Each specialist has: stable ID, domain/style, scope, required inputs, method/checklist, preferred sources, known failure modes, prohibited claims, tools, memory namespace, version, and evaluation history.
   - Start with a small set of meaningfully distinct specialists (for example, RTM, Al Brooks-style price action, trend/momentum, volatility/regime analysis, market microstructure, risk, and skeptical reviewer). Scale to 5,000 only when roles are genuinely distinct and evaluation shows a reason to add them.
   - Avoid falsely implying affiliation with, endorsement by, or exact reproduction of a named educator. Describe the methodology and cite legitimate sources.

4. **Research agent loop**
   - Identify the question and missing evidence.
   - Search the approved corpus and, where enabled, the web.
   - Read and cite relevant material; compare conflicting sources.
   - Produce a structured hypothesis, evidence, counter-evidence, invalidation conditions, uncertainty, and proposed test.
   - Save a research note with provenance. New knowledge is staged for review/evaluation before becoming trusted specialist knowledge.
   - Set tool, time, token, and spending limits; cache results and prevent endless recursive research.

5. **Specialist opinion contract**
   - Fields: agent_id, specialty, market_context, action (LONG/SHORT/NO_TRADE), time_horizon, evidence, source_refs, assumptions, counter_evidence, invalidation, confidence_calibration, missing_data, and proposed_test.
   - An agent must return NO_TRADE when necessary inputs are missing or evidence is insufficient. Confidence is not treated as probability until calibrated on held-out data.

6. **Debate and synthesis**
   - A coordinator routes a question to relevant specialists rather than invoking all 5,000 for every candle.
   - A skeptic/auditor checks citations, look-ahead leakage, unsupported claims, and contradictory assumptions.
   - The synthesizer reports agreement and disagreement, not just an average score.
   - A separate risk gate can veto an otherwise bullish/bearish view. Research output does not execute live orders.

7. **Persistent memory and learning**
   - Separate source knowledge, specialist notes, task memory, and performance memory.
   - Record versioned hypotheses and their outcomes. Never silently rewrite historical notes after seeing outcomes.
   - Learning means retrieval improvements, reviewed knowledge updates, and evaluated procedure changes—not unverified self-modification.
   - Keep an immutable audit trail for source, prompt/config version, retrieved evidence, decision, and evaluation result.

8. **Evaluation**
   - Unit-test retrieval, citations, structured outputs, and specialist-specific reasoning checklists.
   - Evaluate forecasts and decisions with chronological walk-forward tests, untouched holdout periods, realistic fees/slippage, and baselines.
   - Prevent data leakage and selection bias. Track performance by market regime, timeframe, and instrument.
   - Measure calibration, coverage/abstention, drawdown, turnover, net returns, and robustness—not only Sharpe or win rate.
   - Compare a specialist against a simple baseline and against the same agent without retrieval. Remove or revise specialists that add no reproducible value.
   - No agent or source is assumed profitable because it is famous, confident, or well cited.

## Suggested repository modules

- src/crypto_quant/knowledge/sources.py — source metadata and rights/provenance
- src/crypto_quant/knowledge/ingest.py — parsing, deduplication, chunking
- src/crypto_quant/knowledge/retrieval.py — keyword/vector retrieval interface
- src/crypto_quant/experts/schema.py — expert profile and opinion contracts
- src/crypto_quant/experts/registry.py — specialist definitions and routing
- src/crypto_quant/experts/research_loop.py — bounded search/read/summarize loop
- src/crypto_quant/experts/synthesis.py — debate, audit, and synthesis
- src/crypto_quant/evaluation/walk_forward.py — chronological specialist evaluation
- tests/knowledge/ and tests/experts/ — provenance, citations, abstention, routing, and leakage tests

Keep the current 5,000-configuration ML experiment as a baseline/benchmark under a distinct name. Do not label those candidates as expert agents.

## Implementation phases

1. Build the source registry, rights/provenance metadata, and a small test corpus.
2. Implement one end-to-end specialist with citations and a strict opinion schema.
3. Add a bounded research/search loop and review queue for new knowledge.
4. Add 5–10 contrasting specialists and a skeptic; test whether their opinions are reproducible and useful.
5. Add walk-forward evaluation and ablation tests before increasing the population.
6. Expand the source collection and expert registry incrementally, up to 5,000 only when operational cost and evaluation justify it.

## Open decisions before production

- Which LLM/provider or locally hosted model will power reasoning?
- Which search sources and credentials are available?
- Where will the corpus and vector index be stored, and what is the budget?
- Which instruments, timeframes, and languages are in scope?
- What licenses apply to the initial book/document collection?

Until these are resolved, avoid claiming the agents have read 15,000 books, learned like human traders, or possess verified trading skill.
