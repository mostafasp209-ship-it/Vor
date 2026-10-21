# Research source discovery policy

The goal is relevant, traceable research for each specialist—not a giant unfiltered scrape.

## Discovery layers
1. **Broad scholarly indexes:** OpenAlex, Crossref and Semantic Scholar discover papers, authors, venues, citations and open-access copies. They are discovery/metadata services, not guarantees of full-text access.
2. **Preprint and specialist repositories:** arXiv for quantitative methods/ML; RePEc/IDEAS and NBER for economics and finance.
3. **Institutional research portals:** IMF, BIS, Federal Reserve and ECB for macro, rates, FX and market-structure research.
4. **Topic routing:** each expert should query only the sources mapped to its methods, then follow references/citations and search for contradictory findings.
5. **Evidence quality:** store DOI/URL, title, authors, year, venue, abstract, retrieval timestamp, access/license, source type, and why it is relevant. Mark preprints as preprints. Record retractions/corrections when available.
6. **Full text:** download only when openly licensed or otherwise authorized. Respect site/API terms, rate limits, robots policies, and publisher restrictions. Do not bypass paywalls or claim to have read a paper when only its metadata/abstract was available.
7. **Coverage honesty:** no finite run can truthfully claim to have read every article from every country/site. Start with a documented catalog and repeatable API searches, persist results, deduplicate by DOI/title, and expand the catalog from discovered venues and references.

## Official API references
- OpenAlex API: https://help.openalex.org/api/
- Crossref REST API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Semantic Scholar API: https://api.semanticscholar.org/api-docs/
- arXiv API: https://info.arxiv.org/help/api/index.html
- RePEc: https://repec.org/
- NBER papers: https://www.nber.org/papers
- IMF Working Papers: https://www.imf.org/en/Publications/WP
- BIS research: https://www.bis.org/list/research/index.htm
- Federal Reserve FEDS: https://www.federalreserve.gov/econres/feds/
- ECB Working Papers: https://www.ecb.europa.eu/pub/research/working-papers/html/index.en.html

This catalog is the initial verified shortlist, not an exhaustive country-by-country inventory. Expand it by discipline and jurisdiction as the discovery pipeline is implemented and tested.


## Google web search integration

The code includes an adapter for Google's Programmable Search Engine JSON API, requiring `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`. However, Google's current official documentation says the Custom Search JSON API is closed to new customers and existing customers must transition by January 1, 2027. Thus, this adapter is only practical for eligible existing accounts during the transition; do not assume it is available for a new deployment. It is not an unrestricted crawler of every Google result. The general web-search adapter is the practical broad-search fallback; Vertex AI Search is worth evaluating for a configured set of domains, not as a drop-in full-web Google search replacement.

Official setup references:
- Programmable Search Engine: https://programmablesearchengine.google.com/
- Custom Search JSON API documentation: https://developers.google.com/custom-search/v1/overview
