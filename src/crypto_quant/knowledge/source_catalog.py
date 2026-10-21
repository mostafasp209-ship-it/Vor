"""Curated, topic-routed research sources for expert agents.

Prefer official APIs, open repositories, and licensed access. This catalog is a
starting point, not a claim that every country's every article has been crawled.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ResearchSource:
    source_id: str
    name: str
    url: str
    access: str
    best_for: tuple[str, ...]
    notes: str = ""

SOURCES = (
 ResearchSource("openalex","OpenAlex","https://api.openalex.org/works","open metadata API",("quant","finance","econometrics","crypto","market_microstructure","technical_analysis"),"Broad scholarly discovery, topics, citations, open-access locations; use paging and rate limits."),
 ResearchSource("crossref","Crossref","https://api.crossref.org/works","open metadata API",("quant","finance","econometrics","crypto","technical_analysis"),"DOI and publication metadata; abstracts/full text may remain copyrighted."),
 ResearchSource("semantic_scholar","Semantic Scholar","https://api.semanticscholar.org/graph/v1/paper/search","API; rate limits/key may apply",("quant","finance","econometrics","crypto","machine_learning"),"Paper discovery, citation graph and open-access PDF links where available."),
 ResearchSource("arxiv","arXiv","https://export.arxiv.org/api/query","open preprint API",("quant","econometrics","machine_learning","crypto"),"Especially quantitative finance, statistics, optimization, and ML; preprints are not necessarily peer reviewed."),
 ResearchSource("repec","RePEc / IDEAS","https://ideas.repec.org/","public search website",("finance","econometrics","macro","market_microstructure"),"Economics and finance working papers; access methods vary by provider."),
 ResearchSource("nber","NBER Working Papers","https://www.nber.org/papers","public search website",("finance","macro","econometrics"),"Economic and financial research; full text access can vary."),
 ResearchSource("imf","IMF eLibrary / Working Papers","https://www.imf.org/en/Publications/WP","public search website",("macro","fx","finance","econometrics"),"International macroeconomics, currencies, financial stability."),
 ResearchSource("bis","Bank for International Settlements","https://www.bis.org/list/research/index.htm","public research portal",("macro","fx","finance","market_microstructure"),"Central banking, payments, market structure, financial stability."),
 ResearchSource("federal_reserve","Federal Reserve FEDS","https://www.federalreserve.gov/econres/feds/","public research portal",("macro","rates","finance","econometrics"),"US monetary policy, rates, banking, asset pricing."),
 ResearchSource("ecb","European Central Bank Working Papers","https://www.ecb.europa.eu/pub/research/working-papers/html/index.en.html","public research portal",("macro","fx","rates","finance"),"Euro area macroeconomics, monetary policy, markets."),
 ResearchSource("boe","Bank of England Staff Working Papers","https://www.bankofengland.co.uk/working-paper","public research portal",("macro","fx","rates","finance"),"UK monetary policy, banking, markets."),
 ResearchSource("boj","Bank of Japan research papers","https://www.boj.or.jp/en/research/","public research portal",("macro","fx","rates","finance"),"Japan monetary policy and financial system research."),
 ResearchSource("bank_canada","Bank of Canada working papers","https://www.bankofcanada.ca/research/working-papers/","public research portal",("macro","fx","rates","finance"),"Canadian macroeconomics, monetary policy, and markets."),
 ResearchSource("rba","Reserve Bank of Australia research","https://www.rba.gov.au/publications/rdp/","public research portal",("macro","fx","rates","finance"),"Australian macroeconomics and financial markets."),
 ResearchSource("rbi","Reserve Bank of India working papers","https://www.rbi.org.in/","public research portal",("macro","fx","rates","finance"),"Indian monetary, banking, and financial research; verify current working-paper paths."),
 ResearchSource("bcb","Banco Central do Brasil research","https://www.bcb.gov.br/en/publications","public research portal",("macro","fx","rates","finance"),"Brazilian macroeconomics, monetary policy, and financial stability."),
 ResearchSource("sar b","South African Reserve Bank research","https://www.resbank.co.za/en/home/publications/publication-detail-pages/working-papers","public research portal",("macro","fx","rates","finance"),"South African monetary and financial research."),
 ResearchSource("bis_working","BIS working papers","https://www.bis.org/list/research/index.htm","public research portal",("macro","fx","rates","finance","market_microstructure"),"International research including cross-border banking and market structure."),
 ResearchSource("ssrn","SSRN","https://www.ssrn.com/","public search website; access varies",("finance","quant","technical_analysis","crypto"),"Finance and social-science preprints; screen for peer review and version quality."),
)

# Explicit routes keep each expert's source set relevant rather than sending every
# agent every result. Add specialist sources as reviewed and verified.
TOPIC_ROUTES = {
 "quant": ("openalex","crossref","semantic_scholar","arxiv"),
 "finance": ("openalex","crossref","semantic_scholar","repec","nber","ssrn"),
 "econometrics": ("openalex","crossref","semantic_scholar","arxiv","repec"),
 "macro": ("openalex","repec","nber","imf","bis","federal_reserve","ecb","boe","boj","bank_canada","rba","rbi","bcb","sar b"),
 "fx": ("openalex","crossref","imf","bis","ecb","boe","boj","bank_canada","rba","rbi","bcb","sar b"),
 "rates": ("openalex","crossref","federal_reserve","ecb","bis","boe","boj","bank_canada","rba","rbi","bcb","sar b"),
 "market_microstructure": ("openalex","crossref","semantic_scholar","bis"),
 "crypto": ("openalex","crossref","semantic_scholar","arxiv","ssrn"),
 "technical_analysis": ("openalex","crossref","semantic_scholar","ssrn"),
 "machine_learning": ("openalex","semantic_scholar","arxiv"),
}

def sources_for_topics(topics: tuple[str, ...] | list[str]) -> tuple[ResearchSource, ...]:
    """Return unique catalogued sources matching specialist topic tags."""
    by_id = {source.source_id: source for source in SOURCES if source.url and source.access != "disabled"}
    chosen: list[ResearchSource] = []
    seen: set[str] = set()
    for topic in topics:
        for source_id in TOPIC_ROUTES.get(topic, TOPIC_ROUTES["quant"]):
            if source_id in by_id and source_id not in seen:
                chosen.append(by_id[source_id])
                seen.add(source_id)
    return tuple(chosen)


def search_openalex(query: str, limit: int = 10, mailto: str | None = None) -> list[dict]:
    """Search OpenAlex works metadata; abstracts/open PDFs are not guaranteed.

    Uses only the Python standard library. Keep limits modest and follow API terms.
    """
    import json
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    if not query.strip():
        return []
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    params = {"search": query, "per-page": limit, "select": "id,doi,title,publication_year,type,cited_by_count,authorships,open_access,primary_location"}
    if mailto:
        params["mailto"] = mailto
    request = Request("https://api.openalex.org/works?" + urlencode(params), headers={"User-Agent": "VorResearch/0.1 (research metadata client)"})
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = []
    for work in payload.get("results", []):
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        oa = work.get("open_access") or {}
        results.append({
            "source_id": "openalex", "work_id": work.get("id"), "doi": work.get("doi"),
            "title": work.get("title"), "year": work.get("publication_year"),
            "type": work.get("type"), "cited_by_count": work.get("cited_by_count"),
            "venue": source.get("display_name"), "landing_page_url": location.get("landing_page_url"),
            "pdf_url": location.get("pdf_url"), "is_open_access": oa.get("is_oa", False),
            "authors": [a.get("author", {}).get("display_name") for a in work.get("authorships", [])],
            "retrieval_note": "Metadata discovery only; verify full-text access and license before ingestion.",
        })
    return results
