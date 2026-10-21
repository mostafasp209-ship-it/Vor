"""Bounded, provider-agnostic research loop with persistent, sourced notes.

Network search is injected as a callable. No search engine or LLM credentials are
assumed; configure a permitted provider in the deployment environment.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Iterable

from .registry import ExpertProfile


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source_date: str = ""


@dataclass(frozen=True)
class ResearchNote:
    agent_id: str
    question: str
    findings: tuple[str, ...]
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    created_at: str


SearchProvider = Callable[[str, int], Iterable[SearchResult]]


class ResearchAgent:
    """Runs bounded searches and stores auditable research notes, not autonomous trades."""

    def __init__(self, profile: ExpertProfile, memory_path: str | Path,
                 search_provider: SearchProvider | None = None, max_results: int = 5):
        if max_results < 1 or max_results > 20:
            raise ValueError("max_results must be between 1 and 20")
        self.profile = profile
        self.memory_path = Path(memory_path)
        self.search_provider = search_provider
        self.max_results = max_results

    def research(self, question: str) -> ResearchNote:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")
        # Every query carries the specialist's domain, rather than searching only
        # the generic question. The number of queries and total results stay bounded.
        queries = [
            f"{question} {self.profile.specialty} {topic}"
            for topic in self.profile.search_topics[:3]
        ]
        results: list[SearchResult] = []
        limitations: list[str] = []
        if self.search_provider is None:
            limitations.append("No search provider configured; no live web search was performed.")
        else:
            seen_urls: set[str] = set()
            for query in queries:
                try:
                    for item in self.search_provider(query, self.max_results):
                        url = item.url.strip()
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append(item)
                        if len(results) >= self.max_results:
                            break
                except Exception as exc:
                    limitations.append(f"Search provider error for query {query!r}: {type(exc).__name__}")
                if len(results) >= self.max_results:
                    break
        findings = tuple(
            f"{r.title}" + (f" [{r.source_date}]" if r.source_date else "") + f": {r.snippet}"
            for r in results
        )
        refs = tuple(r.url.strip() for r in results if r.url.strip())
        if not results:
            limitations.append(
                "No verifiable source results available; do not treat this note as confirmed market knowledge."
            )
        note = ResearchNote(
            self.profile.agent_id, question, findings, refs, tuple(limitations),
            datetime.now(timezone.utc).isoformat()
        )
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(note), ensure_ascii=False) + "\n")
        return note

    def read_memory(self) -> list[dict]:
        if not self.memory_path.exists():
            return []
        notes = []
        with self.memory_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    notes.append(json.loads(line))
        return notes
