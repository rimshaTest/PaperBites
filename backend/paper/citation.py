# paper/citation.py
"""Add-a-paper-by-citation pipeline (docs/TECHNICAL_SPEC.md's "Add-Paper Ingestion Pipeline").

Two steps, matching the spec's confirm-dialog flow:
1. search_citation() accepts either a raw pasted citation (MLA, APA, or any other style) or a
   direct link to the paper's page (e.g. an open-access journal's article URL). A citation is
   sent straight to Crossref's `query.bibliographic` fuzzy search - Crossref's own fuzzy matching
   already tolerates format differences (punctuation, field order, "et al.", etc.) well enough
   that parsing the citation style first (e.g. via a library like anystyle) would be redundant
   complexity for the same result, which the spec calls an acceptable shortcut. A URL is instead
   scraped for its `citation_*` <meta> tags (the Highwire/Google-Scholar-style metadata standard
   most academic publishers embed - PLOS, eLife, Nature, arXiv, ACS, etc.) to find a DOI (or, if
   no DOI is present anywhere, its title/authors are used as a bibliographic search fallback).
   Either path returns candidate matches with a confirmed open-access link/status resolved via
   Unpaywall.
2. add_paper_from_citation() takes the one candidate the user confirmed and runs it through the
   same enrichment pipeline paper/latest.py's discovery feed uses (abstract fallback, language
   detection/translation, card image) - except the summary and category are produced together by
   one Gemini call (paper.summarize.summarize_and_classify_paper) rather than the user picking a
   category by hand: the discovery feed already knows a paper's category from the search query
   that found it, but a citation-added paper doesn't, so the same read that produces the summary
   also classifies it. It's also embedded for semantic search (paper/embeddings.py) exactly once
   here, same as the discovery feed does at its own ingestion point.

When neither path finds a match, the frontend offers to queue the input for manual admin review
(paper_reviews.py) instead - the spec's fallback for when automated matching can't resolve it.
"""
import asyncio
import logging
import re
import urllib.parse
from html.parser import HTMLParser
from typing import Dict, List, Optional

import aiohttp

from config import Config
from paper.latest import (
    CATEGORIES,
    _HTTP_TIMEOUT,
    _apply_language_and_translation,
    _attach_images,
    _crossref_published_date,
    _fill_missing_abstracts,
    _get_json_with_retry,
    fetch_crossref_abstract,
    fetch_unpaywall_oa_location,
)
from paper.embeddings import embed_document
from paper.summarize import summarize_and_classify_paper

config_instance = Config()
logger = logging.getLogger("paperbites.citation")

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
# Browser-like UA - some publisher sites block/serve stripped-down pages to obvious bot UAs.
_SCRAPE_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PaperBitesBot/1.0; +https://paperbites.app)"}


def _looks_like_url(raw_input: str) -> bool:
    return bool(_URL_RE.match(raw_input))


class _CitationMetaTagParser(HTMLParser):
    """Pulls `<meta name="citation_*" content="...">` tags out of a page's HTML, regardless of
    attribute order (some sites emit `content` before `name`) - the de facto standard most
    academic publisher sites embed for exactly this kind of automated metadata extraction, so
    scraping it is far more reliable than parsing rendered page text.
    """

    def __init__(self):
        super().__init__()
        self.values: Dict[str, List[str]] = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "meta":
            return
        attr_dict = {k.lower(): v for k, v in attrs if k}
        name = (attr_dict.get("name") or "").lower()
        content = attr_dict.get("content")
        if name.startswith("citation_") and content:
            self.values.setdefault(name, []).append(content)


async def _fetch_citation_meta_tags(session: aiohttp.ClientSession, url: str) -> Dict[str, List[str]]:
    try:
        async with session.get(url, headers=_SCRAPE_HEADERS) as response:
            if response.status != 200:
                return {}
            html_text = await response.text(errors="ignore")
    except Exception as e:
        logger.debug(f"Error fetching page for citation meta tags '{url}': {e}")
        return {}

    parser = _CitationMetaTagParser()
    try:
        parser.feed(html_text)
    except Exception as e:
        logger.debug(f"Error parsing HTML for citation meta tags '{url}': {e}")
    return parser.values


def _extract_doi(value: str) -> Optional[str]:
    """Pull a bare DOI out of a string that might be a bare DOI, a "doi:10.xxx" prefix, or a
    full doi.org URL."""
    match = _DOI_RE.search(value)
    return match.group(0) if match else None


async def _candidate_from_crossref_item(session: aiohttp.ClientSession, item: Dict) -> Optional[Dict]:
    """Build a candidate dict from one Crossref API item and resolve its open-access status."""
    titles = item.get("title") or []
    if not titles:
        return None

    authors = []
    for a in item.get("author", []):
        name = " ".join(part for part in [a.get("given"), a.get("family")] if part)
        if name:
            authors.append(name)

    journals = item.get("container-title") or []
    doi = item.get("DOI")

    candidate = {
        "doi": doi,
        "title": titles[0],
        "authors": authors,
        "journal": journals[0] if journals else None,
        "published_date": _crossref_published_date(item),
        "url": item.get("URL"),
        "is_open_access": None,
    }

    if doi:
        location = await fetch_unpaywall_oa_location(session, doi)
        if location:
            candidate["url"] = location["url"] or candidate["url"]
            candidate["is_open_access"] = True
        else:
            candidate["is_open_access"] = False
    else:
        candidate["is_open_access"] = False

    return candidate


async def _lookup_doi(session: aiohttp.ClientSession, doi: str) -> Optional[Dict]:
    """Look up a DOI directly against Crossref (exact match, not fuzzy search) - used when a
    pasted URL's own metadata (or the URL itself) already names a DOI, which is more reliable
    than falling back to a bibliographic fuzzy search.
    """
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    data = await _get_json_with_retry(session, url, "Crossref")
    item = (data or {}).get("message")
    if not item:
        return None
    return await _candidate_from_crossref_item(session, item)


async def _search_crossref_bibliographic(
    session: aiohttp.ClientSession, raw_citation: str, max_results: int
) -> List[Dict]:
    email = config_instance.get("api.email")
    url = (
        "https://api.crossref.org/works"
        f"?query.bibliographic={urllib.parse.quote(raw_citation)}"
        f"&rows={max_results}"
    )
    if email:
        url += f"&mailto={urllib.parse.quote(email)}"

    data = await _get_json_with_retry(session, url, "Crossref")
    if not data:
        return []

    items = (data.get("message") or {}).get("items", [])[:max_results]
    candidates = await asyncio.gather(*(_candidate_from_crossref_item(session, item) for item in items))
    return [c for c in candidates if c]


async def _resolve_url(session: aiohttp.ClientSession, url: str, max_results: int) -> List[Dict]:
    """Resolve a pasted paper-page URL to candidate matches: prefer a DOI (from the page's own
    `citation_doi` meta tag, or embedded directly in the URL itself - common for open-access
    journals like PLOS) looked up exactly against Crossref; fall back to a bibliographic search
    using the page's `citation_title`/`citation_author` meta tags if no DOI can be found anywhere.
    """
    meta = await _fetch_citation_meta_tags(session, url)

    doi = None
    if meta.get("citation_doi"):
        doi = _extract_doi(meta["citation_doi"][0]) or meta["citation_doi"][0].strip()
    if not doi:
        doi = _extract_doi(url)

    if doi:
        candidate = await _lookup_doi(session, doi)
        if candidate:
            return [candidate]

    title = (meta.get("citation_title") or [None])[0]
    if not title:
        logger.debug(f"No DOI or citation_title meta tag found for URL '{url}'")
        return []

    authors = meta.get("citation_author") or []
    fallback_citation = ", ".join(authors[:3] + [title]) if authors else title
    return await _search_crossref_bibliographic(session, fallback_citation, max_results)


async def search_citation(raw_input: str, max_results: int = 5) -> List[Dict]:
    """Resolve a raw pasted citation OR a direct link to a paper's page into candidate matches,
    each with a confirmed open-access link/status resolved via Unpaywall - so the confirm dialog
    can show whether a match is actually readable before the user picks it.
    """
    raw_input = (raw_input or "").strip()
    if not raw_input:
        return []

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        if _looks_like_url(raw_input):
            return await _resolve_url(session, raw_input, max_results)
        return await _search_crossref_bibliographic(session, raw_input, max_results)


async def add_paper_from_citation(candidate: Dict) -> Dict:
    """Build a full paper record from a confirmed citation-search candidate and run it through
    the discovery feed's own enrichment pipeline, so it's stored and served identically to any
    other paper - except its category comes from the same Gemini read that produces its summary,
    not from the user. Raises ValueError on bad input (missing DOI, or a paper that ends up with
    no usable description/category from any source).
    """
    doi = (candidate or {}).get("doi")
    if not doi:
        raise ValueError("A DOI is required to add a paper by citation")

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        # fetch_crossref_abstract already strips JATS tags and runs clean_abstract().
        abstract = await fetch_crossref_abstract(session, doi) or ""

    paper = {
        "source": "crossref",
        "source_id": doi,
        "title": candidate.get("title") or "Untitled",
        "authors": [{"id": None, "name": name} for name in candidate.get("authors") or []],
        "abstract": abstract,
        "citation_count": 0,
        "published_date": candidate.get("published_date"),
        "categories": [],
        "journal": candidate.get("journal"),
        "publication_type": "journal",
        "is_open_access": candidate.get("is_open_access"),
        "doi": doi,
        "url": candidate.get("url"),
    }

    combined = [paper]
    combined = await _fill_missing_abstracts(combined)
    await _apply_language_and_translation(combined)

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        result = await summarize_and_classify_paper(session, paper, CATEGORIES)

    if result:
        paper["description"] = result["summary"]
        paper["categories"] = [result["category"]]
    else:
        # No Gemini key, or every model failed - fall back to the raw abstract like the
        # discovery feed does, and leave the paper uncategorized rather than guessing.
        paper["description"] = paper.get("abstract") or ""
        logger.warning(f"Could not classify category for '{paper['title']}' - saving uncategorized")

    if not paper.get("description"):
        raise ValueError("Could not generate a description for this paper (no abstract or full text available)")

    vector = await embed_document(paper["description"])
    if vector:
        paper["embedding"] = vector

    await _attach_images(combined, paper["categories"][0] if paper["categories"] else paper["title"])

    return paper
