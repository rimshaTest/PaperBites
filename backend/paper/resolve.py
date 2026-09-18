# paper/resolve.py
"""Resolve a single paper from a user-supplied citation string, DOI, or paper URL/link.

Backs the "Saved" tab's add-by-citation-or-link flow: a user pastes a citation or a link to a
paper that the automatic category fetches (paper/latest.py) never happened to surface, and this
looks it up directly via the same free APIs (OpenAlex, Semantic Scholar), then runs it through
the same enrichment pipeline (Crossref abstract fallback, language detection/translation, Gemini
summary) so a manually-added paper looks identical to an auto-fetched one once saved.

Deliberately reuses paper/latest.py's private helpers rather than duplicating them - same
normalization, same enrichment, same "card" shape end to end.
"""
import logging
import re
import urllib.parse
from typing import Dict, List, Optional

import aiohttp

from config import Config
from paper.latest import (
    _HTTP_TIMEOUT,
    _get_json_with_retry,
    _openalex_best_venue,
    reconstruct_openalex_abstract,
    _semantic_scholar_authors,
    _semantic_scholar_publication_type,
    _fill_missing_abstracts,
    _apply_language_and_translation,
    _apply_summaries,
    _attach_images,
)

config_instance = Config()
logger = logging.getLogger("paperbites.resolve")

_DOI_RE = re.compile(r'10\.\d{4,9}/[^\s"\'<>)\]]+', re.IGNORECASE)

_SEMANTIC_SCHOLAR_FIELDS = (
    "title,authors.authorId,authors.name,abstract,citationCount,publicationDate,"
    "externalIds,url,openAccessPdf,venue,isOpenAccess,publicationTypes"
)


def _extract_doi(text: str) -> Optional[str]:
    """Pull a DOI out of arbitrary text - works for a raw DOI, a doi.org link, or a citation
    string that happens to include one."""
    match = _DOI_RE.search(text)
    if not match:
        return None
    return match.group(0).rstrip(").,;")


def _normalize_openalex(item: Dict) -> Dict:
    venue = _openalex_best_venue(item)
    authors = []
    for a in item.get("authorships", []):
        author = a.get("author") or {}
        name = author.get("display_name")
        if not name:
            continue
        author_url = author.get("id") or ""
        author_id = author_url.rsplit("/", 1)[-1] if author_url else None
        authors.append({"id": f"openalex:{author_id}" if author_id else None, "name": name})

    return {
        "source": "openalex",
        "source_id": (item.get("id") or "").rsplit("/", 1)[-1],
        "title": item.get("title") or item.get("display_name") or "Untitled",
        "authors": authors,
        "abstract": reconstruct_openalex_abstract(item.get("abstract_inverted_index")),
        "citation_count": item.get("cited_by_count") or 0,
        "published_date": item.get("publication_date"),
        "categories": ["Saved"],
        "journal": venue["name"],
        "publication_type": venue["type"] if venue["type"] != "other" else None,
        "is_open_access": bool((item.get("open_access") or {}).get("is_oa")),
        "doi": (item.get("doi") or "").replace("https://doi.org/", "") or None,
        "url": (item.get("open_access") or {}).get("oa_url") or item.get("id"),
    }


def _normalize_semantic_scholar(item: Dict) -> Dict:
    publication_type = _semantic_scholar_publication_type(item)
    return {
        "source": "semantic_scholar",
        "source_id": item.get("paperId", ""),
        "title": item.get("title") or "Untitled",
        "authors": _semantic_scholar_authors(item),
        "abstract": item.get("abstract") or "",
        "citation_count": item.get("citationCount") or 0,
        "published_date": item.get("publicationDate"),
        "categories": ["Saved"],
        "journal": item.get("venue") or None,
        "publication_type": publication_type if publication_type != "other" else None,
        "is_open_access": bool(item.get("isOpenAccess")),
        "doi": (item.get("externalIds") or {}).get("DOI"),
        "url": item.get("url") or (item.get("openAccessPdf") or {}).get("url"),
    }


async def _fetch_openalex_by_doi(session: aiohttp.ClientSession, doi: str) -> Optional[Dict]:
    email = config_instance.get("api.email")
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    if email:
        url += f"?mailto={urllib.parse.quote(email)}"

    item = await _get_json_with_retry(session, url, "OpenAlex")
    if not item or not item.get("id"):
        return None
    return _normalize_openalex(item)


async def _fetch_semantic_scholar_by_doi(session: aiohttp.ClientSession, doi: str) -> Optional[Dict]:
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields={_SEMANTIC_SCHOLAR_FIELDS}"
    item = await _get_json_with_retry(session, url, "Semantic Scholar", headers={"Accept": "application/json"})
    if not item:
        return None
    return _normalize_semantic_scholar(item)


async def _search_semantic_scholar_by_title(session: aiohttp.ClientSession, query: str) -> Optional[Dict]:
    """Match a freeform citation/title string to a paper via Semantic Scholar's title-match API
    (built for exactly this - matching a citation string to its canonical paper record)."""
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search/match"
        f"?query={urllib.parse.quote(query)}&fields={_SEMANTIC_SCHOLAR_FIELDS}"
    )
    data = await _get_json_with_retry(session, url, "Semantic Scholar", headers={"Accept": "application/json"})
    matches = (data or {}).get("data") or []
    if not matches:
        return None
    return _normalize_semantic_scholar(matches[0])


async def resolve_paper(query: str) -> Optional[Dict]:
    """Resolve a citation string, DOI, or paper URL to a normalized, enriched paper dict.

    Tries, in order: a DOI found anywhere in the input (covers raw DOIs, doi.org links, and many
    citations that include one) via OpenAlex then Semantic Scholar; falls back to Semantic
    Scholar's title-match search for freeform text with no DOI. Returns None if nothing matches
    or the match has no usable content (no authors, or no abstract from any source).
    """
    query = (query or "").strip()
    if not query:
        return None

    doi = _extract_doi(query)

    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as session:
        paper = None
        if doi:
            paper = await _fetch_openalex_by_doi(session, doi) or await _fetch_semantic_scholar_by_doi(session, doi)

        if not paper:
            paper = await _search_semantic_scholar_by_title(session, query)

    if not paper or not paper.get("authors"):
        return None

    papers: List[Dict] = [paper]
    papers = await _fill_missing_abstracts(papers)
    await _apply_language_and_translation(papers)
    await _apply_summaries(papers)

    papers = [p for p in papers if p.get("description")]
    if not papers:
        return None

    await _attach_images(papers, "Saved")
    return papers[0]
