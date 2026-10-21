import json

import pytest

from crypto_quant.experts import providers
from crypto_quant.experts.research_loop import SearchResult


def result(title, url):
    return SearchResult(title=title, url=url, snippet=f"snippet for {title}")


def test_multi_source_search_round_robins_and_deduplicates(monkeypatch):
    monkeypatch.setattr(providers, "scholarly_search", lambda q, n: [
        result("paper A", "https://example.org/a"),
        result("paper B", "https://example.org/b"),
    ])
    monkeypatch.setattr(providers, "brave_search", lambda q, n: [
        result("web A", "https://example.org/web-a"),
        result("duplicate A", "https://example.org/a/"),
    ])
    monkeypatch.setattr(providers, "google_search", lambda q, n: [
        result("google A", "https://example.org/google-a"),
    ])

    found = providers.multi_source_search("crypto momentum", limit=4)

    assert [item.title for item in found] == ["paper A", "web A", "google A", "paper B"]
    assert len({item.url.rstrip("/") for item in found}) == len(found)


def test_multi_source_search_keeps_public_scholar_results_if_optional_providers_fail(monkeypatch):
    monkeypatch.setattr(providers, "scholarly_search", lambda q, n: [result("paper", "https://doi.org/1")])

    def unavailable(q, n):
        raise providers.ProviderError("missing optional key")

    monkeypatch.setattr(providers, "brave_search", unavailable)
    monkeypatch.setattr(providers, "google_search", unavailable)

    found = providers.multi_source_search("market microstructure", limit=5)
    assert len(found) == 1
    assert found[0].title == "paper"


def test_local_ollama_fallback_without_hosted_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    seen = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "local answer"}}]
            }).encode()

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["body"] = json.loads(request.data.decode())
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(providers, "urlopen", fake_urlopen)

    answer = providers.openai_compatible_chat("system", "question")

    assert answer == "local answer"
    assert seen["url"] == "http://localhost:11434/v1/chat/completions"
    assert seen["body"]["model"] == "test-model"
    assert seen["timeout"] == 120


def test_multi_source_search_rejects_invalid_limit():
    with pytest.raises(ValueError):
        providers.multi_source_search("test", limit=0)
