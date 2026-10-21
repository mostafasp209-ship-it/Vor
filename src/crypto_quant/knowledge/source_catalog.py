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
 ResearchSource("ssrn","SSRN","https://www.ssrn.com/","public search website; access varies",("finance","quant","technical_analysis","crypto"),"Finance and social-science preprints; screen for peer review and version quality."),
 ResearchSource("cochrane_not_applicable","", "", "disabled", (), "Placeholder intentionally unused."),
)

# Explicit routes keep each expert's source set relevant rather than sending every
# agent every result. Add specialist sources as reviewed and verified.
TOPIC_ROUTES = {
 "quant": ("openalex","crossref","semantic_scholar","arxiv"),
 "finance": ("openalex","crossref","semantic_scholar","repec","nber","ssrn"),
 "econometrics": ("openalex","crossref","semantic_scholar","arxiv","repec"),
 "macro": ("openalex","repec","nber","imf","bis","federal_reserve","ecb"),
 "fx": ("openalex","crossref","imf","bis","ecb"),
 "rates": ("openalex","crossref","federal_reserve","ecb","bis"),
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
