"""Optional live search and OpenAI-compatible reasoning adapters.
Credentials are read from environment variables; imports never make network calls.
If OPENAI_API_KEY is absent, reasoning falls back to a local Ollama server without a key.
"""
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .research_loop import SearchResult


class ProviderError(RuntimeError):
    pass


def brave_search(query: str, limit: int = 5) -> list[SearchResult]:
    """Search the web through Brave Search API; requires BRAVE_SEARCH_API_KEY."""
    key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not key:
        raise ProviderError("Set BRAVE_SEARCH_API_KEY to enable live web search.")
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    url = "https://api.search.brave.com/res/v1/web/search?" + urlencode({"q": query, "count": limit})
    req = Request(url, headers={
        "Accept": "application/json", "X-Subscription-Token": key,
        "User-Agent": "Vor-Research/0.1",
    })
    try:
        with urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise ProviderError(f"Search request failed: {type(exc).__name__}") from exc
    return [
        SearchResult(
            title=item.get("title", ""), url=item.get("url", ""),
            snippet=item.get("description", ""),
            source_date=item.get("page_age", "") or "",
        )
        for item in payload.get("web", {}).get("results", [])[:limit]
    ]


def openai_compatible_chat(system_prompt: str, user_prompt: str) -> str:
    """Use OpenAI API when keyed; otherwise use local Ollama with no API key.

    Local mode requires Ollama running at OLLAMA_BASE_URL (default
    http://localhost:11434/v1) and a downloaded model (default qwen2.5:7b).
    """
    key = os.getenv("OPENAI_API_KEY")
    if key:
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        headers = {"Authorization": "Bearer " + key}
        timeout = 60
    else:
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        headers = {}
        timeout = 120

    body = json.dumps({
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }).encode("utf-8")
    headers.update({"Content-Type": "application/json", "Accept": "application/json"})
    req = Request(base + "/chat/completions", data=body, method="POST", headers=headers)
    try:
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
        if not key:
            raise ProviderError(
                "Local Ollama reasoning failed. Install/start Ollama and run "
                f"'ollama pull {model}', or configure OPENAI_API_KEY for a hosted provider. "
                f"Cause: {type(exc).__name__}"
            ) from exc
        raise ProviderError(f"Reasoning API request failed: {type(exc).__name__}") from exc


def scholarly_search(query: str, limit: int = 5) -> list[SearchResult]:
    """Discover scholarly works through OpenAlex; results are metadata, not full-text claims."""
    from ..knowledge.source_catalog import search_openalex
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    try:
        records = search_openalex(query, limit=min(limit, 20), mailto=os.getenv("OPENALEX_MAILTO"))
    except Exception as exc:
        raise ProviderError(f"Scholarly search failed: {type(exc).__name__}") from exc
    output = []
    for item in records:
        url = item.get("landing_page_url") or item.get("doi") or item.get("work_id") or ""
        title = item.get("title") or "Untitled scholarly work"
        details = [
            str(item.get("year") or ""), str(item.get("venue") or ""),
            "citations=" + str(item.get("cited_by_count") or 0),
        ]
        if item.get("is_open_access"):
            details.append("open-access copy reported by index; verify license")
        output.append(SearchResult(
            title=title, url=url, snippet="; ".join(x for x in details if x),
            source_date=str(item.get("year") or ""),
        ))
    return output


def multi_source_search(query: str, limit: int = 5) -> list[SearchResult]:
    """Merge scholarly and web results fairly, deduplicating URLs and preserving diversity.

    Each configured provider gets a chance to contribute before the final limit is
    applied. Missing optional-provider credentials do not disable OpenAlex metadata.
    """
    if not query.strip():
        return []
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    providers = (scholarly_search, brave_search, google_search)
    batches: list[list[SearchResult]] = []
    errors: list[str] = []
    for provider in providers:
        try:
            provider_limit = min(limit, 10) if provider is google_search else limit
            batches.append(list(provider(query, provider_limit)))
        except Exception as exc:
            errors.append(f"{provider.__name__}:{type(exc).__name__}")

    # Round-robin keeps one high-volume source from crowding out every other source.
    results: list[SearchResult] = []
    seen: set[str] = set()
    max_batch = max((len(batch) for batch in batches), default=0)
    for rank in range(max_batch):
        for batch in batches:
            if rank >= len(batch):
                continue
            item = batch[rank]
            normalized_url = item.url.strip().rstrip("/")
            if normalized_url and normalized_url not in seen:
                seen.add(normalized_url)
                results.append(item)
                if len(results) >= limit:
                    return results
    if not results and errors:
        raise ProviderError("All search providers failed: " + ", ".join(errors))
    return results


def google_search(query: str, limit: int = 5) -> list[SearchResult]:
    """Search Google via Programmable Search Engine JSON API (eligible accounts only).

    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID. This is not unrestricted Google crawling.
    """
    key = os.getenv("GOOGLE_API_KEY")
    engine_id = os.getenv("GOOGLE_CSE_ID")
    if not key or not engine_id:
        raise ProviderError("Set GOOGLE_API_KEY and GOOGLE_CSE_ID to enable Google search.")
    if not query.strip():
        return []
    if not 1 <= limit <= 10:
        raise ValueError("Google Custom Search JSON API allows at most 10 results per request")
    params = {"key": key, "cx": engine_id, "q": query, "num": limit}
    url = "https://www.googleapis.com/customsearch/v1?" + urlencode(params)
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "Vor-Research/0.1"})
    try:
        with urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise ProviderError(f"Google search request failed: {type(exc).__name__}") from exc
    return [
        SearchResult(
            title=item.get("title", ""), url=item.get("link", ""),
            snippet=item.get("snippet", ""),
            source_date=item.get("pagemap", {}).get("metatags", [{}])[0].get(
                "article:published_time", ""
            ),
        )
        for item in payload.get("items", [])[:limit]
    ]
